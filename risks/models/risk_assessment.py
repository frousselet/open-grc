from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from risks.constants import AssessmentStatus, Methodology


class RiskAssessment(ScopedModel):
    REFERENCE_PREFIX = "RA"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    methodology = models.CharField(
        _("Methodology"),
        max_length=20,
        choices=Methodology.choices,
        default=Methodology.ISO27005,
    )
    assessment_date = models.DateField(_("Assessment date"), null=True, blank=True)
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments_assessed",
        verbose_name=_("Assessor"),
    )
    risk_criteria = models.ForeignKey(
        "risks.RiskCriteria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        verbose_name=_("Risk criteria"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.DRAFT,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments_validated",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validation date"), null=True, blank=True)
    next_review_date = models.DateField(_("Next review"), null=True, blank=True)
    summary = models.TextField(_("Summary"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Risk assessment")
        verbose_name_plural = _("Risk assessments")

    def __str__(self):
        return f"{self.reference} : {self.name}"
