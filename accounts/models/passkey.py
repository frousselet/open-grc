import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Passkey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="passkeys",
        verbose_name=_("User"),
    )
    name = models.CharField(_("Name"), max_length=255)
    credential_id = models.BinaryField(_("Credential ID"), unique=True)
    public_key = models.BinaryField(_("Public key"))
    sign_count = models.PositiveIntegerField(_("Sign count"), default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    last_used_at = models.DateTimeField(_("Last used at"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Passkey")
        verbose_name_plural = _("Passkeys")

    def __str__(self):
        return f"{self.name} ({self.user.email})"
