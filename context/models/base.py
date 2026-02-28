import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name="Créé par",
    )
    is_approved = models.BooleanField("Approuvé", default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_approved",
        verbose_name="Approuvé par",
    )
    approved_at = models.DateTimeField("Date d'approbation", null=True, blank=True)
    version = models.PositiveIntegerField("Version", default=1)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ScopedModel(BaseModel):
    scope = models.ForeignKey(
        "context.Scope",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        verbose_name="Périmètre",
    )

    class Meta:
        abstract = True
