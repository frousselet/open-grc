from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import (
    SUPPORT_ASSET_CATEGORY_MAP,
    DICLevel,
    Environment,
    ExposureLevel,
    SupportAssetCategory,
    SupportAssetStatus,
    SupportAssetType,
)
from context.models.base import ScopedModel


class SupportAsset(ScopedModel):
    REFERENCE_PREFIX = "SA"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(
        _("Type"), max_length=20, choices=SupportAssetType.choices
    )
    category = models.CharField(
        _("Category"), max_length=30, choices=SupportAssetCategory.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_support_assets",
        verbose_name=_("Owner"),
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custodian_support_assets",
        verbose_name=_("Custodian"),
    )
    location = models.CharField(_("Location"), max_length=255, blank=True, default="")
    manufacturer = models.CharField(
        _("Manufacturer / vendor"), max_length=255, blank=True, default=""
    )
    model_name = models.CharField(
        _("Model / version"), max_length=255, blank=True, default=""
    )
    serial_number = models.CharField(
        _("Serial number"), max_length=255, blank=True, default=""
    )
    software_version = models.CharField(_("Software version"), max_length=100, blank=True, default="")
    ip_address = models.CharField(_("IP address"), max_length=45, blank=True, default="")
    hostname = models.CharField(_("Hostname"), max_length=255, blank=True, default="")
    operating_system = models.CharField(
        _("Operating system"), max_length=255, blank=True, default=""
    )
    acquisition_date = models.DateField(_("Acquisition date"), null=True, blank=True)
    end_of_life_date = models.DateField(_("End of life date"), null=True, blank=True)
    warranty_expiry_date = models.DateField(
        _("Warranty expiry"), null=True, blank=True
    )
    # FK to Supplier omitted — module not yet implemented
    # supplier = models.ForeignKey("suppliers.Supplier", ...)
    contract_reference = models.CharField(
        _("Contract reference"), max_length=255, blank=True, default=""
    )
    inherited_confidentiality = models.IntegerField(
        _("Inherited confidentiality"),
        choices=DICLevel.choices,
        default=DICLevel.NEGLIGIBLE,
    )
    inherited_integrity = models.IntegerField(
        _("Inherited integrity"),
        choices=DICLevel.choices,
        default=DICLevel.NEGLIGIBLE,
    )
    inherited_availability = models.IntegerField(
        _("Inherited availability"),
        choices=DICLevel.choices,
        default=DICLevel.NEGLIGIBLE,
    )
    exposure_level = models.CharField(
        _("Exposure level"),
        max_length=20,
        choices=ExposureLevel.choices,
        blank=True,
        default="",
    )
    environment = models.CharField(
        _("Environment"),
        max_length=20,
        choices=Environment.choices,
        blank=True,
        default="",
    )
    parent_asset = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent support asset"),
    )
    # M2M to Measure omitted — module not yet implemented
    # related_measures = models.ManyToManyField("measures.Measure", ...)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=SupportAssetStatus.choices,
        default=SupportAssetStatus.ACTIVE,
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Support asset")
        verbose_name_plural = _("Support assets")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def clean(self):
        super().clean()
        # RS-02: type/category coherence
        valid_cats = SUPPORT_ASSET_CATEGORY_MAP.get(self.type, [])
        if valid_cats and self.category not in valid_cats:
            raise ValidationError(
                {"category": _("Invalid category for type '%(type)s'.") % {"type": self.get_type_display()}}
            )
        # RS-06: same scope as parent
        if self.parent_asset_id and self.parent_asset.scope_id != self.scope_id:
            raise ValidationError(
                {"parent_asset": _("The child support asset must belong to the same scope as its parent.")}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def recalculate_inherited_dic(self):
        """RV-03: inherited DIC = MAX of all linked essential assets."""
        agg = self.dependencies_as_support.aggregate(
            max_c=Max("essential_asset__confidentiality_level"),
            max_i=Max("essential_asset__integrity_level"),
            max_a=Max("essential_asset__availability_level"),
        )
        self.inherited_confidentiality = agg["max_c"] or DICLevel.NEGLIGIBLE
        self.inherited_integrity = agg["max_i"] or DICLevel.NEGLIGIBLE
        self.inherited_availability = agg["max_a"] or DICLevel.NEGLIGIBLE
        # Save without triggering clean/history overhead
        SupportAsset.objects.filter(pk=self.pk).update(
            inherited_confidentiality=self.inherited_confidentiality,
            inherited_integrity=self.inherited_integrity,
            inherited_availability=self.inherited_availability,
        )

    @property
    def is_end_of_life(self):
        """RS-03: end of life alert."""
        from django.utils import timezone
        if self.end_of_life_date and self.status == SupportAssetStatus.ACTIVE:
            return self.end_of_life_date <= timezone.now().date()
        return False

    @property
    def is_orphan(self):
        """RS-09: no essential asset linked."""
        return not self.dependencies_as_support.exists()
