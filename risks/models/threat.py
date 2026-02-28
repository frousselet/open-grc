from django.db import models
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from risks.constants import ThreatCategory, ThreatOrigin, ThreatStatus, ThreatType


class Threat(ScopedModel):
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True)
    type = models.CharField(
        "Type", max_length=20, choices=ThreatType.choices
    )
    origin = models.CharField(
        "Origine", max_length=20, choices=ThreatOrigin.choices, blank=True
    )
    category = models.CharField(
        "Catégorie", max_length=30, choices=ThreatCategory.choices, blank=True
    )
    typical_likelihood = models.PositiveIntegerField(
        "Vraisemblance typique", null=True, blank=True
    )
    is_from_catalog = models.BooleanField("Issue du catalogue", default=False)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=ThreatStatus.choices,
        default=ThreatStatus.ACTIVE,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = "Menace"
        verbose_name_plural = "Menaces"

    def __str__(self):
        return f"{self.reference} — {self.name}"
