from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
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
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField(
        "Type", max_length=20, choices=SupportAssetType.choices
    )
    category = models.CharField(
        "Catégorie", max_length=30, choices=SupportAssetCategory.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_support_assets",
        verbose_name="Propriétaire",
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custodian_support_assets",
        verbose_name="Dépositaire",
    )
    location = models.CharField("Localisation", max_length=255, blank=True, default="")
    manufacturer = models.CharField(
        "Fabricant / éditeur", max_length=255, blank=True, default=""
    )
    model_name = models.CharField(
        "Modèle / version", max_length=255, blank=True, default=""
    )
    serial_number = models.CharField(
        "Numéro de série", max_length=255, blank=True, default=""
    )
    software_version = models.CharField("Version logicielle", max_length=100, blank=True, default="")
    ip_address = models.CharField("Adresse IP", max_length=45, blank=True, default="")
    hostname = models.CharField("Nom d'hôte", max_length=255, blank=True, default="")
    operating_system = models.CharField(
        "Système d'exploitation", max_length=255, blank=True, default=""
    )
    acquisition_date = models.DateField("Date d'acquisition", null=True, blank=True)
    end_of_life_date = models.DateField("Date de fin de vie", null=True, blank=True)
    warranty_expiry_date = models.DateField(
        "Expiration garantie", null=True, blank=True
    )
    # FK vers Supplier omis — module non encore implémenté
    # supplier = models.ForeignKey("suppliers.Supplier", ...)
    contract_reference = models.CharField(
        "Référence contrat", max_length=255, blank=True, default=""
    )
    inherited_confidentiality = models.IntegerField(
        "Confidentialité héritée",
        choices=DICLevel.choices,
        default=DICLevel.NEGLIGIBLE,
    )
    inherited_integrity = models.IntegerField(
        "Intégrité héritée",
        choices=DICLevel.choices,
        default=DICLevel.NEGLIGIBLE,
    )
    inherited_availability = models.IntegerField(
        "Disponibilité héritée",
        choices=DICLevel.choices,
        default=DICLevel.NEGLIGIBLE,
    )
    exposure_level = models.CharField(
        "Niveau d'exposition",
        max_length=20,
        choices=ExposureLevel.choices,
        blank=True,
        default="",
    )
    environment = models.CharField(
        "Environnement",
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
        verbose_name="Bien support parent",
    )
    # M2M vers Measure omis — module non encore implémenté
    # related_measures = models.ManyToManyField("measures.Measure", ...)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=SupportAssetStatus.choices,
        default=SupportAssetStatus.ACTIVE,
    )
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Bien support"
        verbose_name_plural = "Biens supports"

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        # RS-02: type/category coherence
        valid_cats = SUPPORT_ASSET_CATEGORY_MAP.get(self.type, [])
        if valid_cats and self.category not in valid_cats:
            raise ValidationError(
                {"category": f"Catégorie invalide pour le type « {self.get_type_display()} »."}
            )
        # RS-06: same scope as parent
        if self.parent_asset_id and self.parent_asset.scope_id != self.scope_id:
            raise ValidationError(
                {"parent_asset": "Le bien support enfant doit appartenir au même périmètre que son parent."}
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
