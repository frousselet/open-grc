from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import (
    MeasurementFrequency,
    ObjectiveCategory,
    ObjectiveStatus,
    ObjectiveType,
)
from .base import ScopedModel


class Objective(ScopedModel):
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Intitulé", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    category = models.CharField(
        "Catégorie", max_length=20, choices=ObjectiveCategory.choices
    )
    type = models.CharField("Type", max_length=20, choices=ObjectiveType.choices)
    target_value = models.CharField("Valeur cible", max_length=255, blank=True, default="")
    current_value = models.CharField(
        "Valeur actuelle", max_length=255, blank=True, default=""
    )
    unit = models.CharField("Unité de mesure", max_length=50, blank=True, default="")
    measurement_method = models.TextField(
        "Méthode de mesure", blank=True, default=""
    )
    measurement_frequency = models.CharField(
        "Fréquence de mesure",
        max_length=20,
        choices=MeasurementFrequency.choices,
        blank=True,
        default="",
    )
    target_date = models.DateField("Date cible", null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_objectives",
        verbose_name="Responsable",
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=ObjectiveStatus.choices,
        default=ObjectiveStatus.DRAFT,
    )
    progress_percentage = models.IntegerField(
        "Avancement (%)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    related_issues = models.ManyToManyField(
        "context.Issue",
        blank=True,
        related_name="related_objectives",
        verbose_name="Enjeux adressés",
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_objectives",
        verbose_name="Parties intéressées",
    )
    parent_objective = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Objectif parent",
    )
    # M2M vers Measure omis — module non encore implémenté
    # linked_measures = models.ManyToManyField("measures.Measure", ...)
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Objectif"
        verbose_name_plural = "Objectifs"

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        # RS-02: achieved → 100%
        if self.status == ObjectiveStatus.ACHIEVED and self.progress_percentage != 100:
            raise ValidationError(
                {
                    "progress_percentage": "Un objectif atteint doit avoir un avancement de 100%."
                }
            )
        # RS-03: même scope que le parent
        if self.parent_objective_id and self.parent_objective.scope_id != self.scope_id:
            raise ValidationError(
                {
                    "parent_objective": "L'objectif enfant doit appartenir au même périmètre que son parent."
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
