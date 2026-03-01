import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import AssessmentStatus, ComplianceStatus
from context.models.base import ScopedModel


class ComplianceAssessment(ScopedModel):
    REFERENCE_PREFIX = "CA"

    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.CASCADE,
        related_name="assessments",
        verbose_name=_("Framework"),
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    assessment_date = models.DateField(_("Assessment date"))
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="led_assessments",
        verbose_name=_("Lead assessor"),
    )
    methodology = models.TextField(_("Methodology"), blank=True, default="")
    overall_compliance_level = models.DecimalField(
        _("Overall compliance level (%)"),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    total_requirements = models.PositiveIntegerField(
        _("Total applicable requirements"), default=0
    )
    compliant_count = models.PositiveIntegerField(_("Compliant"), default=0)
    partially_compliant_count = models.PositiveIntegerField(
        _("Partially compliant"), default=0
    )
    non_compliant_count = models.PositiveIntegerField(_("Non-compliant"), default=0)
    not_assessed_count = models.PositiveIntegerField(_("Not assessed"), default=0)
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
        related_name="validated_assessments",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validation date"), null=True, blank=True)
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Compliance assessment")
        verbose_name_plural = _("Compliance assessments")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def recalculate_counts(self):
        """Recompute summary counts from results."""
        results = self.results.all()
        self.total_requirements = results.exclude(
            compliance_status=ComplianceStatus.NOT_APPLICABLE
        ).count()
        self.compliant_count = results.filter(
            compliance_status=ComplianceStatus.COMPLIANT
        ).count()
        self.partially_compliant_count = results.filter(
            compliance_status=ComplianceStatus.PARTIALLY_COMPLIANT
        ).count()
        self.non_compliant_count = results.filter(
            compliance_status=ComplianceStatus.NON_COMPLIANT
        ).count()
        self.not_assessed_count = results.filter(
            compliance_status=ComplianceStatus.NOT_ASSESSED
        ).count()
        if self.total_requirements > 0:
            total_level = sum(
                r.compliance_level or 0
                for r in results.exclude(
                    compliance_status=ComplianceStatus.NOT_APPLICABLE
                )
            )
            self.overall_compliance_level = total_level / self.total_requirements
        else:
            self.overall_compliance_level = 0
        ComplianceAssessment.objects.filter(pk=self.pk).update(
            total_requirements=self.total_requirements,
            compliant_count=self.compliant_count,
            partially_compliant_count=self.partially_compliant_count,
            non_compliant_count=self.non_compliant_count,
            not_assessed_count=self.not_assessed_count,
            overall_compliance_level=self.overall_compliance_level,
        )


class AssessmentResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        ComplianceAssessment,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name=_("Assessment"),
    )
    requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.CASCADE,
        related_name="assessment_results",
        verbose_name=_("Requirement"),
    )
    compliance_status = models.CharField(
        _("Compliance status"),
        max_length=25,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_ASSESSED,
    )
    compliance_level = models.PositiveIntegerField(
        _("Compliance level (%)"), default=0
    )
    evidence = models.TextField(_("Evidence"), blank=True, default="")
    gaps = models.TextField(_("Gaps"), blank=True, default="")
    observations = models.TextField(_("Observations"), blank=True, default="")
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_results",
        verbose_name=_("Assessor"),
    )
    assessed_at = models.DateTimeField(_("Assessment date"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Assessment result")
        verbose_name_plural = _("Assessment results")
        ordering = ["requirement__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "requirement"],
                name="unique_result_per_assessment_requirement",
            )
        ]

    def __str__(self):
        return f"{self.requirement.reference} — {self.get_compliance_status_display()}"
