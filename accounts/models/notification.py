import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.constants import NotificationType


class Notification(models.Model):
    """In-app notification delivered to a single user.

    One row per recipient: the title and message are rendered in the
    recipient's language at creation time. The generic target points to the
    element the notification is about; ``target_url`` is resolved at creation
    so the notification stays usable even if the target is later deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
        verbose_name=_("Actor"),
    )
    notification_type = models.CharField(
        _("Type"),
        max_length=50,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(_("Title"), max_length=255)
    message = models.TextField(_("Message"), blank=True, default="")
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    target_object_id = models.CharField(max_length=64, blank=True, default="")
    target = GenericForeignKey("target_content_type", "target_object_id")
    target_url = models.CharField(_("Target URL"), max_length=500, blank=True, default="")
    is_read = models.BooleanField(_("Read"), default=False, db_index=True)
    read_at = models.DateTimeField(_("Read at"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.recipient} : {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
