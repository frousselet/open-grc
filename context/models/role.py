import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import RaciType, RoleStatus, RoleType
from .base import ScopedModel


class Role(ScopedModel):
    name = models.CharField("Intitulé", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField("Type", max_length=20, choices=RoleType.choices)
    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="context_roles",
        verbose_name="Utilisateurs affectés",
    )
    is_mandatory = models.BooleanField("Rôle obligatoire", default=False)
    source_standard = models.CharField(
        "Référentiel d'origine", max_length=255, blank=True, default=""
    )
    status = models.CharField(
        "Statut", max_length=20, choices=RoleStatus.choices, default=RoleStatus.ACTIVE
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"

    def __str__(self):
        return self.name

    @property
    def compliance_alert(self):
        """RS-06: rôle obligatoire sans utilisateur affecté."""
        if self.is_mandatory and not self.assigned_users.exists():
            return "Rôle obligatoire sans utilisateur affecté"
        return ""


class Responsibility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="responsibilities",
        verbose_name="Rôle",
    )
    description = models.TextField("Description")
    raci_type = models.CharField("Type RACI", max_length=20, choices=RaciType.choices)
    related_activity = models.ForeignKey(
        "context.Activity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsibilities",
        verbose_name="Activité associée",
    )
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Responsabilité"
        verbose_name_plural = "Responsabilités"
        ordering = ["role", "raci_type"]

    def __str__(self):
        return f"{self.role.name} — {self.get_raci_type_display()}"
