import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CalendarToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_tokens",
        verbose_name=_("User"),
    )
    token = models.UUIDField(_("Token"), unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    last_used_at = models.DateTimeField(_("Last used at"), null=True, blank=True)
    last_user_agent = models.CharField(
        _("Last user agent"), max_length=255, blank=True, default="",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Calendar token")
        verbose_name_plural = _("Calendar tokens")

    def __str__(self):
        return f"{self.name} ({self.user.email})"

    @property
    def token_hint(self):
        """Last 4 characters of the token for display."""
        return str(self.token)[-4:]

    @property
    def client_display(self):
        ua = self.last_user_agent
        if not ua:
            return ""
        ua_lower = ua.lower()
        if "apple" in ua_lower or "dataaccessd" in ua_lower:
            return "Apple Calendar"
        if "thunderbird" in ua_lower:
            return "Thunderbird"
        if "outlook" in ua_lower or "microsoft" in ua_lower:
            return "Outlook"
        if "google" in ua_lower:
            return "Google Calendar"
        if "curl" in ua_lower:
            return "curl"
        if "python" in ua_lower:
            return "Python"
        return ua[:50] + ("..." if len(ua) > 50 else "")
