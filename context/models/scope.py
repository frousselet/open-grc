from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import Status
from .base import BaseModel


class Scope(BaseModel):
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description")
    parent_scope = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Périmètre parent",
    )
    status = models.CharField(
        "Statut", max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    boundaries = models.TextField("Limites et exclusions", blank=True, default="")
    justification_exclusions = models.TextField(
        "Justification des exclusions", blank=True, default=""
    )
    geographic_scope = models.TextField(
        "Périmètre géographique", blank=True, default=""
    )
    organizational_scope = models.TextField(
        "Périmètre organisationnel", blank=True, default=""
    )
    technical_scope = models.TextField("Périmètre technique", blank=True, default="")
    included_sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="included_in_scopes",
        verbose_name="Sites inclus",
    )
    excluded_sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="excluded_from_scopes",
        verbose_name="Sites exclus",
    )
    # M2M vers Referential omis — module non encore implémenté
    # applicable_standards = models.ManyToManyField("referential.Referential", ...)
    effective_date = models.DateField(
        "Date d'entrée en vigueur", null=True, blank=True
    )
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Périmètre"
        verbose_name_plural = "Périmètres"

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def clean(self):
        super().clean()
        if self.parent_scope_id:
            parent = self.parent_scope
            visited = {self.pk}
            while parent is not None:
                if parent.pk in visited:
                    raise ValidationError(
                        {"parent_scope": "Référence circulaire détectée."}
                    )
                visited.add(parent.pk)
                parent = parent.parent_scope

    def get_ancestors(self):
        """Retourne la liste des ancêtres du plus éloigné au plus proche."""
        ancestors = []
        parent = self.parent_scope
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent_scope
        return ancestors

    @property
    def full_path(self):
        """Chemin hiérarchique complet (ex: Groupe / Filiale / Site)."""
        ancestors = self.get_ancestors()
        names = [a.name for a in ancestors] + [self.name]
        return " / ".join(names)

    @property
    def level(self):
        """Profondeur dans l'arbre (0 = racine)."""
        n, parent = 0, self.parent_scope
        while parent:
            n += 1
            parent = parent.parent_scope
        return n
