from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import SiteType, Status
from .base import BaseModel


class Site(BaseModel):
    name = models.CharField("Nom", max_length=255)
    type = models.CharField(
        "Type", max_length=20, choices=SiteType.choices, default=SiteType.OTHER
    )
    address = models.TextField("Adresse", blank=True, default="")
    description = models.TextField("Description", blank=True, default="")
    parent_site = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Site parent",
    )
    status = models.CharField(
        "Statut", max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = "Site"
        verbose_name_plural = "Sites"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.parent_site_id:
            parent = self.parent_site
            visited = {self.pk}
            while parent is not None:
                if parent.pk in visited:
                    raise ValidationError(
                        {"parent_site": "Référence circulaire détectée."}
                    )
                visited.add(parent.pk)
                parent = parent.parent_site

    def get_ancestors(self):
        """Retourne la liste des ancêtres du plus éloigné au plus proche."""
        ancestors = []
        parent = self.parent_site
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent_site
        return ancestors

    @property
    def full_path(self):
        """Chemin hiérarchique complet (ex: Siège / Datacenter)."""
        ancestors = self.get_ancestors()
        names = [a.name for a in ancestors] + [self.name]
        return " / ".join(names)

    @property
    def level(self):
        """Profondeur dans l'arbre (0 = racine)."""
        n, parent = 0, self.parent_site
        while parent:
            n += 1
            parent = parent.parent_site
        return n
