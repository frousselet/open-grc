import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import (
    ExpectationType,
    InfluenceLevel,
    IssueType,
    Priority,
    StakeholderCategory,
    StakeholderStatus,
)
from .base import ScopedModel


class Stakeholder(ScopedModel):
    name = models.CharField("Nom", max_length=255)
    type = models.CharField(
        "Type", max_length=20, choices=IssueType.choices
    )
    category = models.CharField(
        "Catégorie", max_length=30, choices=StakeholderCategory.choices
    )
    description = models.TextField("Description", blank=True, default="")
    contact_name = models.CharField(
        "Nom du contact", max_length=255, blank=True, default=""
    )
    contact_email = models.EmailField("Email du contact", blank=True, default="")
    contact_phone = models.CharField(
        "Téléphone du contact", max_length=50, blank=True, default=""
    )
    influence_level = models.CharField(
        "Niveau d'influence", max_length=20, choices=InfluenceLevel.choices
    )
    interest_level = models.CharField(
        "Niveau d'intérêt", max_length=20, choices=InfluenceLevel.choices
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=StakeholderStatus.choices,
        default=StakeholderStatus.ACTIVE,
    )
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Partie intéressée"
        verbose_name_plural = "Parties intéressées"

    def __str__(self):
        return self.name


class StakeholderExpectation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stakeholder = models.ForeignKey(
        Stakeholder,
        on_delete=models.CASCADE,
        related_name="expectations",
        verbose_name="Partie intéressée",
    )
    description = models.TextField("Description")
    type = models.CharField("Type", max_length=20, choices=ExpectationType.choices)
    priority = models.CharField("Priorité", max_length=20, choices=Priority.choices)
    is_applicable = models.BooleanField("Applicable", default=True)
    # M2M vers Requirement omis — module non encore implémenté
    # linked_requirements = models.ManyToManyField("compliance.Requirement", ...)
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Attente"
        verbose_name_plural = "Attentes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.stakeholder.name} — {self.get_type_display()}"
