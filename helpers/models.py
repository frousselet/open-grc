from django.db import models


class HelpContent(models.Model):
    """Contextual help content, translatable per language."""

    key = models.CharField(
        max_length=100,
        verbose_name="Clé",
        help_text="Identifiant unique de la page ou fonctionnalité (ex: context.scope_list).",
    )
    language = models.CharField(
        max_length=10,
        default="fr",
        verbose_name="Langue",
        help_text="Code langue ISO 639-1 (ex: fr, en).",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Titre",
    )
    body = models.TextField(
        verbose_name="Contenu",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        unique_together = ("key", "language")
        ordering = ["key", "language"]
        verbose_name = "Contenu d'aide"
        verbose_name_plural = "Contenus d'aide"

    def __str__(self):
        return f"{self.key} ({self.language})"
