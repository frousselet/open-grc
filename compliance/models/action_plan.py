from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from compliance.constants import ActionPlanStatus, Priority
from context.models.base import ScopedModel


class ComplianceActionPlan(ScopedModel):
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True, default="")
    assessment = models.ForeignKey(
        "compliance.ComplianceAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_plans",
        verbose_name="Évaluation source",
    )
    requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_plans",
        verbose_name="Exigence concernée",
    )
    gap_description = models.TextField("Description de l'écart")
    remediation_plan = models.TextField("Plan de remédiation")
    priority = models.CharField(
        "Priorité", max_length=20, choices=Priority.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_action_plans",
        verbose_name="Responsable",
    )
    start_date = models.DateField("Date de début", null=True, blank=True)
    target_date = models.DateField("Date cible")
    completion_date = models.DateField("Date d'achèvement", null=True, blank=True)
    progress_percentage = models.PositiveIntegerField(
        "Avancement (%)", default=0
    )
    cost_estimate = models.DecimalField(
        "Estimation du coût",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # linked_measures = models.ManyToManyField("measures.Measure", blank=True)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=ActionPlanStatus.choices,
        default=ActionPlanStatus.PLANNED,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = "Plan d'action de conformité"
        verbose_name_plural = "Plans d'action de conformité"

    def __str__(self):
        return f"{self.reference} — {self.name}"
