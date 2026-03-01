from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import (
    INFORMATION_CATEGORIES,
    PROCESS_CATEGORIES,
    DICLevel,
    DataClassification,
    EssentialAssetCategory,
    EssentialAssetStatus,
    EssentialAssetType,
)
from context.models.base import ScopedModel


class EssentialAsset(ScopedModel):
    REFERENCE_PREFIX = "EA"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(
        _("Type"), max_length=20, choices=EssentialAssetType.choices
    )
    category = models.CharField(
        _("Category"), max_length=30, choices=EssentialAssetCategory.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_essential_assets",
        verbose_name=_("Owner"),
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custodian_essential_assets",
        verbose_name=_("Custodian"),
    )
    confidentiality_level = models.IntegerField(
        _("Confidentiality"), choices=DICLevel.choices, default=DICLevel.MEDIUM
    )
    integrity_level = models.IntegerField(
        _("Integrity"), choices=DICLevel.choices, default=DICLevel.MEDIUM
    )
    availability_level = models.IntegerField(
        _("Availability"), choices=DICLevel.choices, default=DICLevel.MEDIUM
    )
    confidentiality_justification = models.TextField(
        _("Confidentiality justification"), blank=True, default=""
    )
    integrity_justification = models.TextField(
        _("Integrity justification"), blank=True, default=""
    )
    availability_justification = models.TextField(
        _("Availability justification"), blank=True, default=""
    )
    max_tolerable_downtime = models.CharField(
        _("MTD / Max tolerable downtime"), max_length=100, blank=True, default=""
    )
    recovery_time_objective = models.CharField(
        _("RTO"), max_length=100, blank=True, default=""
    )
    recovery_point_objective = models.CharField(
        _("RPO"), max_length=100, blank=True, default=""
    )
    data_classification = models.CharField(
        _("Classification"),
        max_length=20,
        choices=DataClassification.choices,
        blank=True,
        default="",
    )
    personal_data = models.BooleanField(
        _("Personal data"), default=False
    )
    personal_data_categories = models.JSONField(
        _("GDPR categories"), null=True, blank=True
    )
    regulatory_constraints = models.TextField(
        _("Regulatory constraints"), blank=True, default=""
    )
    related_activities = models.ManyToManyField(
        "context.Activity",
        blank=True,
        related_name="essential_assets",
        verbose_name=_("Business activities"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=EssentialAssetStatus.choices,
        default=EssentialAssetStatus.IDENTIFIED,
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Essential asset")
        verbose_name_plural = _("Essential assets")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def clean(self):
        super().clean()
        # RS-01: type/category coherence
        if self.type == EssentialAssetType.BUSINESS_PROCESS and self.category not in PROCESS_CATEGORIES:
            raise ValidationError(
                {"category": _("A business process can only have a process category.")}
            )
        if self.type == EssentialAssetType.INFORMATION and self.category not in INFORMATION_CATEGORIES:
            raise ValidationError(
                {"category": _("An information asset can only have an information category.")}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # RV-04: recalculate inherited DIC on all linked support assets
        self._recalculate_support_assets_dic()

    def _recalculate_support_assets_dic(self):
        from .support_asset import SupportAsset
        for dep in self.dependencies_as_essential.select_related("support_asset"):
            dep.support_asset.recalculate_inherited_dic()

    @property
    def max_dic_level(self):
        return max(
            self.confidentiality_level,
            self.integrity_level,
            self.availability_level,
        )
