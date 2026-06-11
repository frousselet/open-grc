from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import EbiosStudyFrameworkStatus


class StudyFramework(BaseModel):
    """EBIOS RM Workshop 0 - Study framework.

    Captures the pre-requisites required by ANSSI before workshop 1:
    perimeters, participants, applicable frameworks, assumptions, constraints.
    Exactly one instance per ebios_rm RiskAssessment.
    """

    WORKFLOW_NAME = "ebios_study_framework"

    REFERENCE_PREFIX = "EFRA"

    assessment = models.OneToOneField(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_study_framework",
        verbose_name=_("Assessment"),
    )
    mission_statement = models.TextField(_("Mission statement"), blank=True)
    business_perimeter = models.TextField(_("Business perimeter"), blank=True)
    technical_perimeter = models.TextField(_("Technical perimeter"), blank=True)
    temporal_perimeter = models.TextField(_("Temporal perimeter"), blank=True)
    financial_envelope = models.DecimalField(
        _("Financial envelope"),
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="ebios_study_frameworks",
        verbose_name=_("Internal participants"),
    )
    participants_external = models.JSONField(
        _("External participants"),
        default=list,
        blank=True,
        help_text=_("List of external participants as {name, role, organization} entries."),
    )
    applicable_frameworks = models.ManyToManyField(
        "compliance.Framework",
        blank=True,
        related_name="ebios_study_frameworks",
        verbose_name=_("Applicable frameworks"),
    )
    assumptions = models.TextField(_("Assumptions"), blank=True)
    constraints = models.TextField(_("Constraints"), blank=True)
    expected_deliverables = models.TextField(_("Expected deliverables"), blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=EbiosStudyFrameworkStatus.choices,
        default=EbiosStudyFrameworkStatus.DRAFT,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("EBIOS RM study framework")
        verbose_name_plural = _("EBIOS RM study frameworks")

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_assessment"

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, EbiosStudyFrameworkStatus.DRAFT)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} : {self.assessment.name}"
