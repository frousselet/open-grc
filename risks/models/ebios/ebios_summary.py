from collections import Counter

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import EbiosSummaryStatus


class EbiosSummary(BaseModel):
    """EBIOS RM Workshop 5 - Assessment summary.

    Single instance per ebios_rm RiskAssessment. Holds the residual risk
    strategy, monitoring plan and PACS summary plus two JSON snapshots
    (`risk_mapping_before`, `risk_mapping_after`) used to render the
    before / after cartography. Snapshots are captured on demand via the
    `capture_risk_mappings()` method rather than at every Risk save() so
    the user controls when the cartography baseline is set.
    """

    WORKFLOW_NAME = "ebios_summary"

    REFERENCE_PREFIX = "ESUM"

    assessment = models.OneToOneField(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_summary",
        verbose_name=_("Assessment"),
    )
    residual_risk_strategy = models.TextField(_("Residual risk strategy"), blank=True)
    monitoring_plan = models.TextField(_("Monitoring plan"), blank=True)
    pacs_summary = models.TextField(_("PACS summary"), blank=True)
    risk_mapping_before = models.JSONField(
        _("Risk mapping before treatment"),
        null=True,
        blank=True,
        help_text=_("Snapshot of the risk register before treatment, captured on demand."),
    )
    risk_mapping_after = models.JSONField(
        _("Risk mapping after treatment"),
        null=True,
        blank=True,
        help_text=_("Snapshot of the risk register after treatment, captured on demand."),
    )
    next_strategic_cycle_date = models.DateField(
        _("Next strategic cycle date"), null=True, blank=True,
    )
    next_operational_cycle_date = models.DateField(
        _("Next operational cycle date"), null=True, blank=True,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_summaries_validated",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validated at"), null=True, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=EbiosSummaryStatus.choices,
        default=EbiosSummaryStatus.DRAFT,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("EBIOS RM summary")
        verbose_name_plural = _("EBIOS RM summaries")

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_summary"

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, EbiosSummaryStatus.DRAFT)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} : {self.assessment.name}"

    def _build_snapshot(self):
        """Aggregate the current state of the assessment's risk register.

        The snapshot is a stable dict shape (totals + counters per status,
        priority and risk level) that the UI can render as a matrix or a
        kanban without re-querying the DB.
        """
        if not self.assessment_id:
            return None
        risks = self.assessment.risks.all()
        if not risks.exists():
            return {
                "total": 0,
                "by_status": {},
                "by_priority": {},
                "by_initial_risk_level": {},
                "by_current_risk_level": {},
                "by_residual_risk_level": {},
            }
        return {
            "total": risks.count(),
            "by_status": dict(Counter(risks.values_list("status", flat=True))),
            "by_priority": dict(Counter(risks.values_list("priority", flat=True))),
            "by_initial_risk_level": {
                str(k): v
                for k, v in Counter(
                    risks.values_list("initial_risk_level", flat=True)
                ).items()
                if k is not None
            },
            "by_current_risk_level": {
                str(k): v
                for k, v in Counter(
                    risks.values_list("current_risk_level", flat=True)
                ).items()
                if k is not None
            },
            "by_residual_risk_level": {
                str(k): v
                for k, v in Counter(
                    risks.values_list("residual_risk_level", flat=True)
                ).items()
                if k is not None
            },
        }

    def capture_risk_mappings(self, *, capture_before=True, capture_after=True):
        """Snapshot the current risk register into `risk_mapping_before/after`.

        Splitting the two captures allows the user to take a baseline before
        starting treatment (`before`) and a follow-up snapshot once treatment
        is in progress (`after`). Pass `capture_before=False` or
        `capture_after=False` to update only one of the two slots.
        """
        snapshot = self._build_snapshot()
        if capture_before:
            self.risk_mapping_before = snapshot
        if capture_after:
            self.risk_mapping_after = snapshot
        update_fields = []
        if capture_before:
            update_fields.append("risk_mapping_before")
        if capture_after:
            update_fields.append("risk_mapping_after")
        if update_fields:
            self.save(update_fields=update_fields)
