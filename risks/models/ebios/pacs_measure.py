from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    PACSMeasurePriority,
    PACSMeasureStatus,
    PACSMeasureType,
)


class PACSMeasure(BaseModel):
    """EBIOS RM Workshop 5 - PACS measure.

    Structured entry of the Plan d'Amélioration Continue de la Sécurité.
    Each measure may be linked to one or more RiskTreatmentPlans, baseline
    gaps and compliance requirements so the PACS doubles as a roadmap and
    as a traceability matrix.
    """

    WORKFLOW_NAME = "ebios_pacs_measure"

    REFERENCE_PREFIX = "EPAC"

    summary = models.ForeignKey(
        "risks.EbiosSummary",
        on_delete=models.CASCADE,
        related_name="pacs_measures",
        verbose_name=_("EBIOS summary"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    measure_type = models.CharField(
        _("Measure type"),
        max_length=20,
        choices=PACSMeasureType.choices,
        default=PACSMeasureType.PROTECTION,
    )
    linked_treatment_plans = models.ManyToManyField(
        "risks.RiskTreatmentPlan",
        blank=True,
        related_name="pacs_measures",
        verbose_name=_("Linked treatment plans"),
    )
    linked_baseline_gaps = models.ManyToManyField(
        "risks.BaselineGap",
        blank=True,
        related_name="pacs_measures",
        verbose_name=_("Linked baseline gaps"),
    )
    linked_requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="pacs_measures",
        verbose_name=_("Linked compliance requirements"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacs_measures_owned",
        verbose_name=_("Owner"),
    )
    start_date = models.DateField(_("Start date"), null=True, blank=True)
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    cost_estimate = models.DecimalField(
        _("Cost estimate"),
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    expected_gain = models.TextField(_("Expected gain"), blank=True)
    priority = models.CharField(
        _("Priority"),
        max_length=16,
        choices=PACSMeasurePriority.choices,
        default=PACSMeasurePriority.MEDIUM,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=PACSMeasureStatus.choices,
        default=PACSMeasureStatus.PLANNED,
    )
    progress_percentage = models.PositiveSmallIntegerField(
        _("Progress percentage"), null=True, blank=True,
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    history = HistoricalRecords()

    class Meta:
        ordering = ["summary", "order", "target_date"]
        verbose_name = _("EBIOS RM PACS measure")
        verbose_name_plural = _("EBIOS RM PACS measures")

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_summary"

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, PACSMeasureStatus.PLANNED)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} : {self.name}"
