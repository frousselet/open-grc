import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import (
    AssessmentStatus,
    ComplianceStatus,
    FINDING_SEVERITY_ORDER,
    FINDING_TYPE_COMPLIANCE_LEVEL,
)
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
    evaluated_count = models.PositiveIntegerField(_("Evaluated"), default=0)
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
        self.evaluated_count = results.filter(
            compliance_status=ComplianceStatus.EVALUATED
        ).count()
        self.not_assessed_count = results.filter(
            compliance_status=ComplianceStatus.NOT_ASSESSED
        ).count()

        # Build fallback map: requirement_id → (status, level) from prior assessments
        not_assessed_req_ids = [
            r.requirement_id for r in results
            if r.compliance_status in (
                ComplianceStatus.NOT_ASSESSED,
                ComplianceStatus.EVALUATED,
            )
        ]
        prior_map = {}
        if not_assessed_req_ids:
            prior_results = (
                AssessmentResult.objects.filter(
                    assessment__framework=self.framework,
                    requirement_id__in=not_assessed_req_ids,
                )
                .exclude(assessment=self)
                .exclude(compliance_status__in=[
                    ComplianceStatus.NOT_ASSESSED,
                    ComplianceStatus.EVALUATED,
                ])
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
            if result.compliance_status in (
                ComplianceStatus.NOT_ASSESSED,
                ComplianceStatus.EVALUATED,
            ):
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
            evaluated_count=self.evaluated_count,
            not_assessed_count=self.not_assessed_count,
            overall_compliance_level=self.overall_compliance_level,
        )

        # ── Propagate to requirements ──
        from compliance.models.requirement import Requirement

        affected_section_ids = set()
        for result in results:
            req = result.requirement
            # For NOT_ASSESSED/EVALUATED, propagate the prior status if available
            if result.compliance_status in (
                ComplianceStatus.NOT_ASSESSED,
                ComplianceStatus.EVALUATED,
            ):
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

    def apply_findings_to_results(self):
        """Update assessment results based on linked findings (worst-finding-wins).

        For each requirement that has findings linked in this assessment,
        the most severe finding determines the compliance status and level.
        """
        from compliance.models.finding import Finding

        # Map finding_type -> ComplianceStatus
        FINDING_TYPE_TO_STATUS = {
            "major_nc": ComplianceStatus.MAJOR_NON_CONFORMITY,
            "minor_nc": ComplianceStatus.MINOR_NON_CONFORMITY,
            "observation": ComplianceStatus.OBSERVATION,
            "improvement": ComplianceStatus.IMPROVEMENT_OPPORTUNITY,
            "strength": ComplianceStatus.STRENGTH,
        }

        findings = self.findings.prefetch_related("requirements").all()
        # Build: requirement_id -> worst finding type
        req_worst = {}  # requirement_id -> finding_type (most severe)
        for finding in findings:
            for req in finding.requirements.all():
                current = req_worst.get(req.pk)
                if current is None:
                    req_worst[req.pk] = finding.finding_type
                else:
                    # Compare severity: lower index in FINDING_SEVERITY_ORDER = more severe
                    current_idx = (
                        FINDING_SEVERITY_ORDER.index(current)
                        if current in FINDING_SEVERITY_ORDER
                        else len(FINDING_SEVERITY_ORDER)
                    )
                    new_idx = (
                        FINDING_SEVERITY_ORDER.index(finding.finding_type)
                        if finding.finding_type in FINDING_SEVERITY_ORDER
                        else len(FINDING_SEVERITY_ORDER)
                    )
                    if new_idx < current_idx:
                        req_worst[req.pk] = finding.finding_type

        # Update existing results for affected requirements
        existing_req_ids = set()
        for result in self.results.filter(requirement_id__in=req_worst.keys()):
            existing_req_ids.add(result.requirement_id)
            worst_type = req_worst[result.requirement_id]
            new_status = FINDING_TYPE_TO_STATUS.get(worst_type)
            new_level = FINDING_TYPE_COMPLIANCE_LEVEL.get(worst_type, 0)
            if new_status:
                result.compliance_status = new_status
                result.compliance_level = new_level
                result.save(update_fields=["compliance_status", "compliance_level"])

        # Create results for requirements that have findings but no result yet
        from django.utils import timezone

        missing_req_ids = set(req_worst.keys()) - existing_req_ids
        if missing_req_ids:
            now = timezone.now()
            for req_id in missing_req_ids:
                worst_type = req_worst[req_id]
                new_status = FINDING_TYPE_TO_STATUS.get(worst_type)
                new_level = FINDING_TYPE_COMPLIANCE_LEVEL.get(worst_type, 0)
                if new_status:
                    AssessmentResult.objects.create(
                        assessment=self,
                        requirement_id=req_id,
                        compliance_status=new_status,
                        compliance_level=new_level,
                        assessed_by=self.assessor,
                        assessed_at=now,
                    )

        # Reset results whose findings were all removed back to NOT_ASSESSED
        finding_statuses = set(FINDING_TYPE_TO_STATUS.values())
        self.results.filter(
            compliance_status__in=finding_statuses,
        ).exclude(
            requirement_id__in=req_worst.keys(),
        ).update(
            compliance_status=ComplianceStatus.NOT_ASSESSED,
            compliance_level=0,
        )

        # Recalculate counts after applying findings
        self.recalculate_counts()


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
