import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
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
    REFERENCE_PREFIX = "RTP"

    risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.CASCADE,
        related_name="treatment_plans",
        verbose_name=_("Risk"),
    )
    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    treatment_type = models.CharField(
        _("Treatment type"),
        max_length=20,
        choices=TreatmentType.choices,
    )
    expected_residual_likelihood = models.PositiveIntegerField(
        _("Expected residual likelihood"), null=True, blank=True
    )
    expected_residual_impact = models.PositiveIntegerField(
        _("Expected residual impact"), null=True, blank=True
    )
    cost_estimate = models.DecimalField(
        _("Estimated cost"),
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
        verbose_name=_("Owner"),
    )
    start_date = models.DateField(_("Start date"), null=True, blank=True)
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    progress_percentage = models.PositiveIntegerField(
        _("Progress (%)"),
        default=0,
        validators=[MaxValueValidator(100)],
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=TreatmentPlanStatus.choices,
        default=TreatmentPlanStatus.PLANNED,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Treatment plan")
        verbose_name_plural = _("Treatment plans")

    def __str__(self):
        return f"{self.reference} : {self.name}"

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
                _("Value must be one of %(levels)s.") % {"levels": sorted(l_levels)}
            )
        val = self.expected_residual_impact
        if val is not None and val not in i_levels:
            errors["expected_residual_impact"] = (
                _("Value must be one of %(levels)s.") % {"levels": sorted(i_levels)}
            )
        if errors:
            raise ValidationError(errors)


class TreatmentAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treatment_plan = models.ForeignKey(
        RiskTreatmentPlan,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("Treatment plan"),
    )
    description = models.TextField(_("Description"))
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="treatment_actions",
        verbose_name=_("Owner"),
    )
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ActionStatus.choices,
        default=ActionStatus.PLANNED,
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("Treatment action")
        verbose_name_plural = _("Treatment actions")

    def __str__(self):
        return f"Action {self.order} — {self.description[:50]}"
