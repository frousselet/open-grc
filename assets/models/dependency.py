import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from assets.constants import (
    DependencyType,
    RedundancyLevel,
    SupportAssetStatus,
)
from context.constants import Criticality


class AssetDependency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    essential_asset = models.ForeignKey(
        "assets.EssentialAsset",
        on_delete=models.CASCADE,
        related_name="dependencies_as_essential",
        verbose_name="Bien essentiel",
    )
    support_asset = models.ForeignKey(
        "assets.SupportAsset",
        on_delete=models.CASCADE,
        related_name="dependencies_as_support",
        verbose_name="Bien support",
    )
    dependency_type = models.CharField(
        "Type de dépendance", max_length=20, choices=DependencyType.choices
    )
    criticality = models.CharField(
        "Criticité", max_length=20, choices=Criticality.choices
    )
    description = models.TextField("Description", blank=True, default="")
    is_single_point_of_failure = models.BooleanField(
        "Point unique de défaillance (SPOF)", default=False
    )
    redundancy_level = models.CharField(
        "Niveau de redondance",
        max_length=20,
        choices=RedundancyLevel.choices,
        blank=True,
        default="",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_dependencies",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    is_approved = models.BooleanField("Approuvé", default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_dependencies",
        verbose_name="Approuvé par",
    )
    approved_at = models.DateTimeField("Date d'approbation", null=True, blank=True)
    version = models.PositiveIntegerField("Version", default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Relation de dépendance"
        verbose_name_plural = "Relations de dépendance"
        constraints = [
            models.UniqueConstraint(
                fields=["essential_asset", "support_asset"],
                name="unique_asset_dependency",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.essential_asset.reference} → {self.support_asset.reference}"

    def clean(self):
        super().clean()
        # RS-04: decommissioned/disposed support assets cannot have new deps
        if self.support_asset_id:
            sa_status = self.support_asset.status
            if sa_status in (SupportAssetStatus.DECOMMISSIONED, SupportAssetStatus.DISPOSED):
                if not self.pk or not AssetDependency.objects.filter(pk=self.pk).exists():
                    raise ValidationError(
                        {"support_asset": "Impossible de créer une dépendance vers un bien support décommissionné ou éliminé."}
                    )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # Recalculate inherited DIC on the support asset
        self.support_asset.recalculate_inherited_dic()

    def delete(self, *args, **kwargs):
        support_asset = self.support_asset
        super().delete(*args, **kwargs)
        support_asset.recalculate_inherited_dic()
