from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import (
    EXTERNAL_CATEGORIES,
    INTERNAL_CATEGORIES,
    ImpactLevel,
    IssueCategory,
    IssueStatus,
    IssueType,
    Trend,
)
from .base import ScopedModel


class Issue(ScopedModel):
    name = models.CharField("Intitulé", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField("Type", max_length=20, choices=IssueType.choices)
    category = models.CharField(
        "Catégorie", max_length=30, choices=IssueCategory.choices
    )
    impact_level = models.CharField(
        "Niveau d'impact", max_length=20, choices=ImpactLevel.choices
    )
    trend = models.CharField(
        "Tendance", max_length=20, choices=Trend.choices, blank=True, default=""
    )
    source = models.CharField("Source", max_length=255, blank=True, default="")
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_issues",
        verbose_name="Parties intéressées liées",
    )
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)
    status = models.CharField(
        "Statut", max_length=20, choices=IssueStatus.choices, default=IssueStatus.IDENTIFIED
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Enjeu"
        verbose_name_plural = "Enjeux"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        # RS-01: cohérence type / catégorie
        if self.type == IssueType.INTERNAL and self.category not in INTERNAL_CATEGORIES:
            raise ValidationError(
                {
                    "category": "Un enjeu interne ne peut avoir qu'une catégorie interne."
                }
            )
        if self.type == IssueType.EXTERNAL and self.category not in EXTERNAL_CATEGORIES:
            raise ValidationError(
                {
                    "category": "Un enjeu externe ne peut avoir qu'une catégorie externe."
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
