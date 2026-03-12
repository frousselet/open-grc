import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import AssessmentStatus, ComplianceStatus
from context.models.base import ScopedModel


class ComplianceAssessment(ScopedModel):
    REFERENCE_PREFIX = "CAST"

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
    major_non_conformity_count = models.PositiveIntegerField(
        _("Major non-conformity"), default=0
    )
    minor_non_conformity_count = models.PositiveIntegerField(
        _("Minor non-conformity"), default=0
    )
    observation_count = models.PositiveIntegerField(_("Observation"), default=0)
    improvement_opportunity_count = models.PositiveIntegerField(
        _("Improvement opportunity"), default=0
    )
    strength_count = models.PositiveIntegerField(_("Strength"), default=0)
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
        """Recompute summary counts from results and propagate to requirements/framework.

        For NOT_ASSESSED results, fall back to the last known result from a
        previous assessment on the same framework. If no prior result exists,
        the requirement counts as 0%.  NOT_APPLICABLE always counts as 100%.
        """
        results = self.results.select_related("requirement").all()
        self.total_requirements = results.count()
        self.compliant_count = results.filter(
            compliance_status=ComplianceStatus.COMPLIANT
        ).count()
        self.major_non_conformity_count = results.filter(
            compliance_status=ComplianceStatus.MAJOR_NON_CONFORMITY
        ).count()
        self.minor_non_conformity_count = results.filter(
            compliance_status=ComplianceStatus.MINOR_NON_CONFORMITY
        ).count()
        self.observation_count = results.filter(
            compliance_status=ComplianceStatus.OBSERVATION
        ).count()
        self.improvement_opportunity_count = results.filter(
            compliance_status=ComplianceStatus.IMPROVEMENT_OPPORTUNITY
        ).count()
        self.strength_count = results.filter(
            compliance_status=ComplianceStatus.STRENGTH
        ).count()
        self.not_assessed_count = results.filter(
            compliance_status=ComplianceStatus.NOT_ASSESSED
        ).count()

        # Build fallback map: requirement_id → (status, level) from prior assessments
        not_assessed_req_ids = [
            r.requirement_id for r in results
            if r.compliance_status == ComplianceStatus.NOT_ASSESSED
        ]
        prior_map = {}
        if not_assessed_req_ids:
            prior_results = (
                AssessmentResult.objects.filter(
                    assessment__framework=self.framework,
                    requirement_id__in=not_assessed_req_ids,
                )
                .exclude(assessment=self)
                .exclude(compliance_status=ComplianceStatus.NOT_ASSESSED)
                .order_by("-assessed_at")
                .values_list("requirement_id", "compliance_status", "compliance_level")
            )
            # Keep only the most recent result per requirement
            for req_id, status, level in prior_results:
                if req_id not in prior_map:
                    prior_map[req_id] = (status, level)

        def _effective_level(result):
            if result.compliance_status == ComplianceStatus.NOT_APPLICABLE:
                return 100
            if result.compliance_status == ComplianceStatus.NOT_ASSESSED:
                prior = prior_map.get(result.requirement_id)
                if prior:
                    status, level = prior
                    return 100 if status == ComplianceStatus.NOT_APPLICABLE else (level or 0)
                return 0
            return result.compliance_level or 0

        if self.total_requirements > 0:
            total_level = sum(_effective_level(r) for r in results)
            self.overall_compliance_level = total_level / self.total_requirements
        else:
            self.overall_compliance_level = 0
        ComplianceAssessment.objects.filter(pk=self.pk).update(
            total_requirements=self.total_requirements,
            compliant_count=self.compliant_count,
            major_non_conformity_count=self.major_non_conformity_count,
            minor_non_conformity_count=self.minor_non_conformity_count,
            observation_count=self.observation_count,
            improvement_opportunity_count=self.improvement_opportunity_count,
            strength_count=self.strength_count,
            not_assessed_count=self.not_assessed_count,
            overall_compliance_level=self.overall_compliance_level,
        )

        # ── Propagate to requirements ──
        from compliance.models.requirement import Requirement

        affected_section_ids = set()
        for result in results:
            req = result.requirement
            # For NOT_ASSESSED, propagate the prior status if available
            if result.compliance_status == ComplianceStatus.NOT_ASSESSED:
                prior = prior_map.get(result.requirement_id)
                if prior:
                    eff_status, eff_level = prior
                else:
                    eff_status = ComplianceStatus.NOT_ASSESSED
                    eff_level = 0
            else:
                eff_status = result.compliance_status
                eff_level = result.compliance_level
            Requirement.objects.filter(pk=req.pk).update(
                compliance_status=eff_status,
                compliance_level=eff_level,
            )
            if req.section_id:
                affected_section_ids.add(req.section_id)

        # ── Propagate to sections ──
        from compliance.models.section import Section

        for section in Section.objects.filter(pk__in=affected_section_ids):
            section.recalculate_compliance()

        # ── Propagate to framework ──
        self.framework.recalculate_compliance()


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
        max_length=30,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_ASSESSED,
    )
    compliance_level = models.PositiveIntegerField(
        _("Compliance level (%)"), default=0
    )
    finding = models.TextField(_("Finding"), blank=True, default="")
    auditor_recommendations = models.TextField(
        _("Auditor recommendations"), blank=True, default=""
    )
    evidence = models.TextField(_("Evidence"), blank=True, default="")
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
        ordering = ["requirement__requirement_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "requirement"],
                name="unique_result_per_assessment_requirement",
            )
        ]

    def __str__(self):
        return f"{self.requirement.reference} — {self.get_compliance_status_display()}"
