import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import (
    RedundancyLevel,
    SiteAssetDependencyType,
    SiteSupplierDependencyType,
)
from context.constants import Criticality


class SiteAssetDependency(models.Model):
    """A support asset depends on a site (e.g. a server is located at a datacenter)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_asset = models.ForeignKey(
        "assets.SupportAsset",
        on_delete=models.CASCADE,
        related_name="site_dependencies",
        verbose_name=_("Support asset"),
    )
    site = models.ForeignKey(
        "context.Site",
        on_delete=models.CASCADE,
        related_name="asset_dependencies",
        verbose_name=_("Site"),
    )
    dependency_type = models.CharField(
        _("Dependency type"),
        max_length=20,
        choices=SiteAssetDependencyType.choices,
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
        related_name="created_site_asset_dependencies",
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
        related_name="approved_site_asset_dependencies",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(_("Approval date"), null=True, blank=True)
    version = models.PositiveIntegerField(_("Version"), default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Site–asset dependency")
        verbose_name_plural = _("Site–asset dependencies")
        constraints = [
            models.UniqueConstraint(
                fields=["support_asset", "site"],
                name="unique_site_asset_dependency",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.support_asset.reference} → {self.site.reference}"


class SiteSupplierDependency(models.Model):
    """A site depends on a supplier (e.g. a datacenter is maintained by a provider)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(
        "context.Site",
        on_delete=models.CASCADE,
        related_name="supplier_dependencies",
        verbose_name=_("Site"),
    )
    supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.CASCADE,
        related_name="site_dependencies",
        verbose_name=_("Supplier"),
    )
    dependency_type = models.CharField(
        _("Dependency type"),
        max_length=20,
        choices=SiteSupplierDependencyType.choices,
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
        related_name="created_site_supplier_dependencies",
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
        related_name="approved_site_supplier_dependencies",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(_("Approval date"), null=True, blank=True)
    version = models.PositiveIntegerField(_("Version"), default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Site–supplier dependency")
        verbose_name_plural = _("Site–supplier dependencies")
        constraints = [
            models.UniqueConstraint(
                fields=["site", "supplier"],
                name="unique_site_supplier_dependency",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.site.reference} → {self.supplier.reference}"
