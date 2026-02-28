from django.db import models
from django.utils.translation import gettext_lazy as _


class HelpContent(models.Model):
    """Contextual help content, translatable per language."""

    key = models.CharField(
        max_length=100,
        verbose_name=_("Key"),
        help_text=_("Unique identifier of the page or feature (e.g. context.scope_list)."),
    )
    language = models.CharField(
        max_length=10,
        default="fr",
        verbose_name=_("Language"),
        help_text=_("ISO 639-1 language code (e.g. fr, en)."),
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Title"),
    )
    body = models.TextField(
        verbose_name=_("Content"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last modified"))

    class Meta:
        unique_together = ("key", "language")
        ordering = ["key", "language"]
        verbose_name = _("Help content")
        verbose_name_plural = _("Help contents")

    def __str__(self):
        return f"{self.key} ({self.language})"
