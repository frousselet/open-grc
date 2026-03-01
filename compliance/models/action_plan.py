from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import ActionPlanStatus, Priority
from context.models.base import ScopedModel


class ComplianceActionPlan(ScopedModel):
    REFERENCE_PREFIX = "CAP"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    assessment = models.ForeignKey(
        "compliance.ComplianceAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_plans",
        verbose_name=_("Source assessment"),
    )
    requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_plans",
        verbose_name=_("Related requirement"),
    )
    gap_description = models.TextField(_("Gap description"))
    remediation_plan = models.TextField(_("Remediation plan"))
    priority = models.CharField(
        _("Priority"), max_length=20, choices=Priority.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_action_plans",
        verbose_name=_("Owner"),
    )
    start_date = models.DateField(_("Start date"), null=True, blank=True)
    target_date = models.DateField(_("Target date"))
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    progress_percentage = models.PositiveIntegerField(
        _("Progress (%)"), default=0
    )
    cost_estimate = models.DecimalField(
        _("Cost estimate"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # linked_measures = models.ManyToManyField("measures.Measure", blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ActionPlanStatus.choices,
        default=ActionPlanStatus.PLANNED,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Compliance action plan")
        verbose_name_plural = _("Compliance action plans")

    def __str__(self):
        return f"{self.reference} : {self.name}"
