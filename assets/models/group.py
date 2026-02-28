from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import AssetGroupStatus, SupportAssetType
from context.models.base import ScopedModel


class AssetGroup(ScopedModel):
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(
        _("Type"), max_length=20, choices=SupportAssetType.choices
    )
    members = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="groups",
        verbose_name=_("Members"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_asset_groups",
        verbose_name=_("Owner"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=AssetGroupStatus.choices,
        default=AssetGroupStatus.ACTIVE,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Asset group")
        verbose_name_plural = _("Asset groups")

    def __str__(self):
        return self.name
