import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.constants import PermissionAction


class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codename = models.CharField(
        _("Codename"),
        max_length=255,
        unique=True,
        help_text=_("Format: module.feature.action"),
    )
    name = models.CharField(_("Label"), max_length=255)
    module = models.CharField(_("Module"), max_length=100, db_index=True)
    feature = models.CharField(_("Feature"), max_length=100, db_index=True)
    action = models.CharField(
        _("Action"),
        max_length=20,
        choices=PermissionAction.choices,
    )
    description = models.TextField(_("Description"), blank=True, default="")
    is_system = models.BooleanField(_("System permission"), default=True)

    class Meta:
        ordering = ["module", "feature", "action"]
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")

    def __str__(self):
        return self.codename
