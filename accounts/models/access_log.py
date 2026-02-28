import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.constants import AccessEventType, FailureReason


class AccessLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name=_("User"),
    )
    email_attempted = models.CharField(
        _("Email used"),
        max_length=255,
        db_index=True,
    )
    event_type = models.CharField(
        _("Event type"),
        max_length=30,
        choices=AccessEventType.choices,
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.TextField(_("User-Agent"), blank=True, default="")
    failure_reason = models.CharField(
        _("Failure reason"),
        max_length=30,
        choices=FailureReason.choices,
        blank=True,
        default="",
    )
    metadata = models.JSONField(_("Metadata"), default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = _("Access log")
        verbose_name_plural = _("Access logs")

    def __str__(self):
        return f"{self.timestamp} — {self.event_type} — {self.email_attempted}"
