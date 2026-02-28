import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    ActionStatus,
    DEFAULT_IMPACT_SCALES,
    DEFAULT_LIKELIHOOD_SCALES,
    TreatmentPlanStatus,
    TreatmentType,
)


class RiskTreatmentPlan(BaseModel):
    risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.CASCADE,
        related_name="treatment_plans",
        verbose_name="Risque",
    )
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True)
    treatment_type = models.CharField(
        "Type de traitement",
        max_length=20,
        choices=TreatmentType.choices,
    )
    expected_residual_likelihood = models.PositiveIntegerField(
        "Vraisemblance résiduelle attendue", null=True, blank=True
    )
    expected_residual_impact = models.PositiveIntegerField(
        "Impact résiduel attendu", null=True, blank=True
    )
    cost_estimate = models.DecimalField(
        "Estimation du coût",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_treatment_plans",
        verbose_name="Responsable",
    )
    start_date = models.DateField("Date de début", null=True, blank=True)
    target_date = models.DateField("Date cible", null=True, blank=True)
    completion_date = models.DateField("Date de réalisation", null=True, blank=True)
    progress_percentage = models.PositiveIntegerField(
        "Progression (%)",
        default=0,
        validators=[MaxValueValidator(100)],
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=TreatmentPlanStatus.choices,
        default=TreatmentPlanStatus.PLANNED,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Plan de traitement"
        verbose_name_plural = "Plans de traitement"

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        from risks.models.risk_criteria import RiskCriteria

        # Determine valid levels from the risk's assessment criteria, default
        # criteria, or hardcoded defaults (last resort).
        criteria = None
        if self.risk_id:
            criteria = getattr(
                getattr(self.risk, "assessment", None), "risk_criteria", None
            )
        if not criteria:
            criteria = (
                RiskCriteria.objects.filter(is_default=True).first()
                or RiskCriteria.objects.filter(status="active").first()
            )
        l_levels = {level for level, _ in DEFAULT_LIKELIHOOD_SCALES}
        i_levels = {level for level, _ in DEFAULT_IMPACT_SCALES}
        if criteria:
            cl = set(
                criteria.scale_levels.filter(scale_type="likelihood")
                .values_list("level", flat=True)
            )
            ci = set(
                criteria.scale_levels.filter(scale_type="impact")
                .values_list("level", flat=True)
            )
            if cl and ci:
                l_levels, i_levels = cl, ci
        errors = {}
        val = self.expected_residual_likelihood
        if val is not None and val not in l_levels:
            errors["expected_residual_likelihood"] = (
                f"La valeur doit être parmi {sorted(l_levels)}."
            )
        val = self.expected_residual_impact
        if val is not None and val not in i_levels:
            errors["expected_residual_impact"] = (
                f"La valeur doit être parmi {sorted(i_levels)}."
            )
        if errors:
            raise ValidationError(errors)


class TreatmentAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treatment_plan = models.ForeignKey(
        RiskTreatmentPlan,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name="Plan de traitement",
    )
    description = models.TextField("Description")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="treatment_actions",
        verbose_name="Responsable",
    )
    target_date = models.DateField("Date cible", null=True, blank=True)
    completion_date = models.DateField("Date de réalisation", null=True, blank=True)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=ActionStatus.choices,
        default=ActionStatus.PLANNED,
    )
    order = models.PositiveIntegerField("Ordre", default=0)
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Action de traitement"
        verbose_name_plural = "Actions de traitement"

    def __str__(self):
        return f"Action {self.order} — {self.description[:50]}"
