from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
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
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField(
        "Type", max_length=20, choices=EssentialAssetType.choices
    )
    category = models.CharField(
        "Catégorie", max_length=30, choices=EssentialAssetCategory.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_essential_assets",
        verbose_name="Propriétaire",
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custodian_essential_assets",
        verbose_name="Dépositaire",
    )
    confidentiality_level = models.IntegerField(
        "Confidentialité", choices=DICLevel.choices, default=DICLevel.MEDIUM
    )
    integrity_level = models.IntegerField(
        "Intégrité", choices=DICLevel.choices, default=DICLevel.MEDIUM
    )
    availability_level = models.IntegerField(
        "Disponibilité", choices=DICLevel.choices, default=DICLevel.MEDIUM
    )
    confidentiality_justification = models.TextField(
        "Justification confidentialité", blank=True, default=""
    )
    integrity_justification = models.TextField(
        "Justification intégrité", blank=True, default=""
    )
    availability_justification = models.TextField(
        "Justification disponibilité", blank=True, default=""
    )
    max_tolerable_downtime = models.CharField(
        "DMIT / MTD", max_length=100, blank=True, default=""
    )
    recovery_time_objective = models.CharField(
        "RTO", max_length=100, blank=True, default=""
    )
    recovery_point_objective = models.CharField(
        "RPO", max_length=100, blank=True, default=""
    )
    data_classification = models.CharField(
        "Classification",
        max_length=20,
        choices=DataClassification.choices,
        blank=True,
        default="",
    )
    personal_data = models.BooleanField(
        "Données personnelles", default=False
    )
    personal_data_categories = models.JSONField(
        "Catégories RGPD", null=True, blank=True
    )
    regulatory_constraints = models.TextField(
        "Contraintes réglementaires", blank=True, default=""
    )
    related_activities = models.ManyToManyField(
        "context.Activity",
        blank=True,
        related_name="essential_assets",
        verbose_name="Activités métier",
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=EssentialAssetStatus.choices,
        default=EssentialAssetStatus.IDENTIFIED,
    )
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Bien essentiel"
        verbose_name_plural = "Biens essentiels"

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        # RS-01: type/category coherence
        if self.type == EssentialAssetType.BUSINESS_PROCESS and self.category not in PROCESS_CATEGORIES:
            raise ValidationError(
                {"category": "Un processus métier ne peut avoir qu'une catégorie de processus."}
            )
        if self.type == EssentialAssetType.INFORMATION and self.category not in INFORMATION_CATEGORIES:
            raise ValidationError(
                {"category": "Une information ne peut avoir qu'une catégorie d'information."}
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
