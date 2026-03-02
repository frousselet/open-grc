import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generate_client_id():
    return f"ogrc_{secrets.token_hex(16)}"


def _generate_client_secret():
    return secrets.token_urlsafe(48)


class OAuthApplication(models.Model):
    """OAuth 2.0 client credentials for MCP access, owned by a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Application name"), max_length=255)
    client_id = models.CharField(
        _("Client ID"),
        max_length=255,
        unique=True,
        default=_generate_client_id,
    )
    client_secret_hash = models.CharField(
        _("Client secret (hashed)"),
        max_length=128,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_applications",
        verbose_name=_("Owner"),
    )
    is_active = models.BooleanField(_("Active"), default=True)
    last_used_at = models.DateTimeField(_("Last used"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("OAuth application")
        verbose_name_plural = _("OAuth applications")

    def __str__(self):
        return f"{self.name} ({self.client_id})"

    @staticmethod
    def hash_secret(raw_secret):
        return hashlib.sha256(raw_secret.encode()).hexdigest()

    def set_secret(self, raw_secret):
        self.client_secret_hash = self.hash_secret(raw_secret)

    def verify_secret(self, raw_secret):
        return self.client_secret_hash == self.hash_secret(raw_secret)


class OAuthAccessToken(models.Model):
    """OAuth 2.0 access tokens issued to MCP clients."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        OAuthApplication,
        on_delete=models.CASCADE,
        related_name="access_tokens",
        verbose_name=_("Application"),
    )
    token_hash = models.CharField(
        _("Token (hashed)"),
        max_length=128,
        unique=True,
        db_index=True,
    )
    expires_at = models.DateTimeField(_("Expires at"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("OAuth access token")
        verbose_name_plural = _("OAuth access tokens")

    def __str__(self):
        return f"Token for {self.application.name}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @staticmethod
    def hash_token(raw_token):
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def create_token(cls, application, lifetime_seconds=3600):
        """Create a new access token and return (instance, raw_token)."""
        raw_token = secrets.token_urlsafe(48)
        token = cls(
            application=application,
            token_hash=cls.hash_token(raw_token),
            expires_at=timezone.now() + timezone.timedelta(seconds=lifetime_seconds),
        )
        token.save()
        return token, raw_token
