import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import RaciType, RoleStatus, RoleType
from .base import ScopedModel


class Role(ScopedModel):
    REFERENCE_PREFIX = "ROLE"

    name = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(_("Type"), max_length=20, choices=RoleType.choices)
    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="context_roles",
        verbose_name=_("Assigned users"),
    )
    is_mandatory = models.BooleanField(_("Mandatory role"), default=False)
    source_standard = models.CharField(
        _("Source standard"), max_length=255, blank=True, default=""
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=RoleStatus.choices, default=RoleStatus.ACTIVE
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")

    def __str__(self):
        return f"{self.reference} — {self.name}"

    @property
    def compliance_alert(self):
        """RS-06: mandatory role without assigned user."""
        if self.is_mandatory and not self.assigned_users.exists():
            return _("Mandatory role without assigned user")
        return ""


class Responsibility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="responsibilities",
        verbose_name=_("Role"),
    )
    description = models.TextField(_("Description"))
    raci_type = models.CharField(_("RACI type"), max_length=20, choices=RaciType.choices)
    related_activity = models.ForeignKey(
        "context.Activity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsibilities",
        verbose_name=_("Related activity"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Responsibility")
        verbose_name_plural = _("Responsibilities")
        ordering = ["role", "raci_type"]

    def __str__(self):
        return f"{self.role.name} — {self.get_raci_type_display()}"
