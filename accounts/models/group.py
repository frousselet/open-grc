import uuid

from django.conf import settings
from django.db import models


class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Nom", max_length=255, unique=True)
    description = models.TextField("Description", blank=True, default="")
    is_system = models.BooleanField("Groupe système", default=False)
    permissions = models.ManyToManyField(
        "accounts.Permission",
        blank=True,
        related_name="groups",
        verbose_name="Permissions",
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="custom_groups",
        verbose_name="Utilisateurs",
    )
    allowed_scopes = models.ManyToManyField(
        "context.Scope",
        blank=True,
        related_name="allowed_groups",
        verbose_name="Périmètres autorisés",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_groups",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"

    def __str__(self):
        return self.name
