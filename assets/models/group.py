from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from assets.constants import AssetGroupStatus, SupportAssetType
from context.models.base import ScopedModel


class AssetGroup(ScopedModel):
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField(
        "Type", max_length=20, choices=SupportAssetType.choices
    )
    members = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="groups",
        verbose_name="Membres",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_asset_groups",
        verbose_name="Responsable",
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=AssetGroupStatus.choices,
        default=AssetGroupStatus.ACTIVE,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Groupe d'actifs"
        verbose_name_plural = "Groupes d'actifs"

    def __str__(self):
        return self.name
