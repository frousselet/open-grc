import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True, default="")
    is_system = models.BooleanField(_("System group"), default=False)
    permissions = models.ManyToManyField(
        "accounts.Permission",
        blank=True,
        related_name="groups",
        verbose_name=_("Permissions"),
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="custom_groups",
        verbose_name=_("Users"),
    )
    allowed_scopes = models.ManyToManyField(
        "context.Scope",
        blank=True,
        related_name="allowed_groups",
        verbose_name=_("Allowed scopes"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_groups",
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Group")
        verbose_name_plural = _("Groups")

    def __str__(self):
        return self.name
