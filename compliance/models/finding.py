from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import FindingStatus, FindingType
from context.models.base import ScopedModel


class Finding(ScopedModel):
    REFERENCE_PREFIX = "FNDG"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")

    finding_type = models.CharField(
        _("Finding type"),
        max_length=30,
        choices=FindingType.choices,
        default=FindingType.OBSERVATION,
    )

    # Link to exactly one audit OR one control (not both required, but at least one)
    audit = models.ForeignKey(
        "compliance.ComplianceAudit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_findings",
        verbose_name=_("Audit"),
    )
    control = models.ForeignKey(
        "compliance.ComplianceControl",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="control_findings",
        verbose_name=_("Control"),
    )

    # Action plans (M2M)
    action_plans = models.ManyToManyField(
        "compliance.ComplianceActionPlan",
        blank=True,
        related_name="findings",
        verbose_name=_("Action plans"),
    )

    # Associated activities and requirements
    activities = models.ManyToManyField(
        "context.Activity",
        blank=True,
        related_name="findings",
        verbose_name=_("Activities"),
    )
    requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="findings",
        verbose_name=_("Requirements"),
    )

    # Related findings (self-referential M2M for recurring findings across audits)
    related_findings = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name=_("Related findings"),
    )

    evidence = models.TextField(_("Evidence"), blank=True, default="")

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Finding")
        verbose_name_plural = _("Findings")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    @property
    def is_resolved(self):
        """A finding is resolved when it has at least one action plan
        and all linked action plans are completed."""
        plans = self.action_plans.all()
        if not plans.exists():
            return False
        return not plans.exclude(status="completed").exists()

    @property
    def status(self):
        if self.is_resolved:
            return FindingStatus.RESOLVED
        return FindingStatus.UNRESOLVED
