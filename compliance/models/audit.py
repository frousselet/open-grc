from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import AuditStatus, AuditType
from context.models.base import ScopedModel


class ComplianceAudit(ScopedModel):
    REFERENCE_PREFIX = "AUDT"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")

    audit_type = models.CharField(
        _("Audit type"),
        max_length=20,
        choices=AuditType.choices,
        default=AuditType.FIRST_PARTY,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.PLANNED,
    )

    # Scope: entire frameworks or specific sections
    frameworks = models.ManyToManyField(
        "compliance.Framework",
        blank=True,
        related_name="audits",
        verbose_name=_("Frameworks"),
    )
    sections = models.ManyToManyField(
        "compliance.Section",
        blank=True,
        related_name="audits",
        verbose_name=_("Sections"),
    )

    lead_auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audits_led",
        verbose_name=_("Lead auditor"),
    )
    control_body = models.ForeignKey(
        "compliance.ControlBody",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audits",
        verbose_name=_("Control body"),
    )

    planned_start_date = models.DateField(_("Planned start date"), null=True, blank=True)
    planned_end_date = models.DateField(_("Planned end date"), null=True, blank=True)
    actual_start_date = models.DateField(_("Actual start date"), null=True, blank=True)
    actual_end_date = models.DateField(_("Actual end date"), null=True, blank=True)

    objectives = models.TextField(_("Audit objectives"), blank=True, default="")
    conclusion = models.TextField(_("Conclusion"), blank=True, default="")
    findings_summary = models.TextField(_("Findings summary"), blank=True, default="")

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Audit")
        verbose_name_plural = _("Audits")

    def __str__(self):
        return f"{self.reference} : {self.name}"
