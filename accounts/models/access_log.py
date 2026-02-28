import uuid

from django.conf import settings
from django.db import models

from accounts.constants import AccessEventType, FailureReason


class AccessLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField("Horodatage", auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name="Utilisateur",
    )
    email_attempted = models.CharField(
        "Email utilisé",
        max_length=255,
        db_index=True,
    )
    event_type = models.CharField(
        "Type d'événement",
        max_length=30,
        choices=AccessEventType.choices,
        db_index=True,
    )
    ip_address = models.GenericIPAddressField("Adresse IP", null=True, blank=True)
    user_agent = models.TextField("User-Agent", blank=True, default="")
    failure_reason = models.CharField(
        "Raison de l'échec",
        max_length=30,
        choices=FailureReason.choices,
        blank=True,
        default="",
    )
    metadata = models.JSONField("Métadonnées", default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Journal des accès"
        verbose_name_plural = "Journal des accès"

    def __str__(self):
        return f"{self.timestamp} — {self.event_type} — {self.email_attempted}"
