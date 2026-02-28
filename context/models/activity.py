from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from context.constants import ActivityStatus, ActivityType, Criticality
from .base import ScopedModel


class Activity(ScopedModel):
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField("Type", max_length=20, choices=ActivityType.choices)
    criticality = models.CharField(
        "Criticité", max_length=20, choices=Criticality.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_activities",
        verbose_name="Responsable",
    )
    parent_activity = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Activité parente",
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_activities",
        verbose_name="Parties intéressées",
    )
    related_objectives = models.ManyToManyField(
        "context.Objective",
        blank=True,
        related_name="related_activities",
        verbose_name="Objectifs contributifs",
    )
    # M2M vers EssentialAsset omis — module non encore implémenté
    # linked_assets = models.ManyToManyField("assets.EssentialAsset", ...)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=ActivityStatus.choices,
        default=ActivityStatus.ACTIVE,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Activité"
        verbose_name_plural = "Activités"

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        # RS-04: même scope que le parent
        if self.parent_activity_id and self.parent_activity.scope_id != self.scope_id:
            raise ValidationError(
                {
                    "parent_activity": "L'activité enfant doit appartenir au même périmètre que son parent."
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
