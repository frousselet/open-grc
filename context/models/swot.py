import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import ImpactLevel, SwotQuadrant, SwotStatus
from .base import ScopedModel


class SwotAnalysis(ScopedModel):
    name = models.CharField("Intitulé", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    analysis_date = models.DateField("Date de réalisation")
    status = models.CharField(
        "Statut", max_length=20, choices=SwotStatus.choices, default=SwotStatus.DRAFT
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_swot_analyses",
        verbose_name="Validé par",
    )
    validated_at = models.DateTimeField("Date de validation", null=True, blank=True)
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Analyse SWOT"
        verbose_name_plural = "Analyses SWOT"

    def __str__(self):
        return self.name


class SwotItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    swot_analysis = models.ForeignKey(
        SwotAnalysis,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Analyse SWOT",
    )
    quadrant = models.CharField(
        "Quadrant", max_length=20, choices=SwotQuadrant.choices
    )
    description = models.TextField("Description")
    impact_level = models.CharField(
        "Niveau d'impact",
        max_length=20,
        choices=[
            (ImpactLevel.LOW, ImpactLevel.LOW.label),
            (ImpactLevel.MEDIUM, ImpactLevel.MEDIUM.label),
            (ImpactLevel.HIGH, ImpactLevel.HIGH.label),
        ],
    )
    related_issues = models.ManyToManyField(
        "context.Issue",
        blank=True,
        related_name="swot_items",
        verbose_name="Enjeux associés",
    )
    related_objectives = models.ManyToManyField(
        "context.Objective",
        blank=True,
        related_name="swot_items",
        verbose_name="Objectifs associés",
    )
    order = models.IntegerField("Ordre", default=0)
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Élément SWOT"
        verbose_name_plural = "Éléments SWOT"
        ordering = ["quadrant", "order"]

    def __str__(self):
        return f"{self.get_quadrant_display()} — {self.description[:50]}"
