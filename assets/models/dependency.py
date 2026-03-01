import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
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
        verbose_name=_("Essential asset"),
    )
    support_asset = models.ForeignKey(
        "assets.SupportAsset",
        on_delete=models.CASCADE,
        related_name="dependencies_as_support",
        verbose_name=_("Support asset"),
    )
    dependency_type = models.CharField(
        _("Dependency type"), max_length=20, choices=DependencyType.choices
    )
    criticality = models.CharField(
        _("Criticality"), max_length=20, choices=Criticality.choices
    )
    description = models.TextField(_("Description"), blank=True, default="")
    is_single_point_of_failure = models.BooleanField(
        _("Single point of failure (SPOF)"), default=False
    )
    redundancy_level = models.CharField(
        _("Redundancy level"),
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
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    is_approved = models.BooleanField(_("Approved"), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_dependencies",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(_("Approval date"), null=True, blank=True)
    version = models.PositiveIntegerField(_("Version"), default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Dependency relationship")
        verbose_name_plural = _("Dependency relationships")
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
                        {"support_asset": _("Cannot create a dependency to a decommissioned or disposed support asset.")}
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
