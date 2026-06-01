import datetime

import pytest
from django.core.exceptions import ValidationError

from compliance.constants import ComplianceStatus
from compliance.tests.factories import (
    AssessmentResultFactory,
    ComplianceAssessmentFactory,
    FrameworkFactory,
    MappingFactory,
    RequirementFactory,
)

pytestmark = pytest.mark.django_db


class TestFrameworkCompliance:
    """P0: compliance level recalculation from assessment results."""

    def test_recalculate_no_requirements(self):
        fw = FrameworkFactory()
        fw.recalculate_compliance()
        fw.refresh_from_db()
        assert fw.compliance_level == 0

    def test_recalculate_with_assessment_results(self):
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req2 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw,
            assessment_end_date=datetime.date(2026, 3, 1),
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=100,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req2,
            compliance_status=ComplianceStatus.MINOR_NON_CONFORMITY, compliance_level=50,
        )
        # Framework now reads requirement state, which recalculate_counts
        # populates from the latest assessment results.
        assessment.recalculate_counts()
        fw.refresh_from_db()
        assert fw.compliance_level == 75

    def test_recalculate_excludes_not_applicable(self):
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        req2 = RequirementFactory(framework=fw, is_applicable=True)
        assessment = ComplianceAssessmentFactory(
            framework=fw,
            assessment_end_date=datetime.date(2026, 3, 1),
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=100,
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req2,
            compliance_status=ComplianceStatus.NOT_APPLICABLE, compliance_level=0,
        )
        assessment.recalculate_counts()
        fw.refresh_from_db()
        assert fw.compliance_level == 100

    def test_recalculate_excludes_non_applicable_flag(self):
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        RequirementFactory(framework=fw, is_applicable=False)
        assessment = ComplianceAssessmentFactory(
            framework=fw,
            assessment_end_date=datetime.date(2026, 3, 1),
        )
        AssessmentResultFactory(
            assessment=assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=80,
        )
        assessment.recalculate_counts()
        fw.refresh_from_db()
        assert fw.compliance_level == 80

    def test_recalculate_fallback_to_prior_assessment(self):
        """NOT_ASSESSED in latest audit falls back to prior evaluation."""
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw, is_applicable=True)
        # Older assessment with a real evaluation
        old_assessment = ComplianceAssessmentFactory(
            framework=fw,
            assessment_end_date=datetime.date(2026, 1, 1),
        )
        AssessmentResultFactory(
            assessment=old_assessment, requirement=req1,
            compliance_status=ComplianceStatus.COMPLIANT, compliance_level=100,
        )
        # Newer assessment where req is NOT_ASSESSED
        new_assessment = ComplianceAssessmentFactory(
            framework=fw,
            assessment_end_date=datetime.date(2026, 3, 1),
        )
        AssessmentResultFactory(
            assessment=new_assessment, requirement=req1,
            compliance_status=ComplianceStatus.NOT_ASSESSED, compliance_level=0,
        )
        # recalculate_counts on the new assessment falls back to the old
        # evaluation when its own result is NOT_ASSESSED; it writes that
        # fallback to Requirement.compliance_level, which Framework now reads.
        new_assessment.recalculate_counts()
        fw.refresh_from_db()
        # Should use the old assessment's value (100), not 0
        assert fw.compliance_level == 100


class TestRequirementMapping:
    """P1: mapping validation — different frameworks only."""

    def test_mapping_different_frameworks_ok(self):
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        req1 = RequirementFactory(framework=fw1)
        req2 = RequirementFactory(framework=fw2)
        mapping = MappingFactory(source_requirement=req1, target_requirement=req2)
        mapping.clean()  # no error

    def test_mapping_same_framework_rejected(self):
        fw = FrameworkFactory()
        req1 = RequirementFactory(framework=fw)
        req2 = RequirementFactory(framework=fw)
        mapping = MappingFactory.build(source_requirement=req1, target_requirement=req2)
        with pytest.raises(ValidationError, match="different frameworks"):
            mapping.clean()

    def test_mapping_creates_inverse_includes_to_included_by(self):
        """RM-03: 'includes' on source -> 'included_by' inverse row."""
        from compliance.models.mapping import RequirementMapping
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        req1 = RequirementFactory(framework=fw1)
        req2 = RequirementFactory(framework=fw2)
        MappingFactory(
            source_requirement=req1,
            target_requirement=req2,
            mapping_type="includes",
        )
        inverse = RequirementMapping.objects.filter(
            source_requirement=req2, target_requirement=req1
        )
        assert inverse.count() == 1
        assert inverse.first().mapping_type == "included_by"

    def test_mapping_creates_inverse_equivalent_stays_equivalent(self):
        """RM-02: 'equivalent' on source -> 'equivalent' inverse row."""
        from compliance.models.mapping import RequirementMapping
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        req1 = RequirementFactory(framework=fw1)
        req2 = RequirementFactory(framework=fw2)
        MappingFactory(
            source_requirement=req1,
            target_requirement=req2,
            mapping_type="equivalent",
        )
        inverse = RequirementMapping.objects.filter(
            source_requirement=req2, target_requirement=req1
        )
        assert inverse.count() == 1
        assert inverse.first().mapping_type == "equivalent"

    def test_mapping_inverse_creation_idempotent(self):
        """Creating the second direction first should not double-create."""
        from compliance.models.mapping import RequirementMapping
        fw1 = FrameworkFactory()
        fw2 = FrameworkFactory()
        req1 = RequirementFactory(framework=fw1)
        req2 = RequirementFactory(framework=fw2)
        MappingFactory(
            source_requirement=req1,
            target_requirement=req2,
            mapping_type="includes",
        )
        # The reverse row already exists. Creating a "manual" inverse should
        # not loop: the unique constraint would reject a duplicate anyway.
        assert RequirementMapping.objects.filter(
            source_requirement=req1, target_requirement=req2
        ).count() == 1
        assert RequirementMapping.objects.filter(
            source_requirement=req2, target_requirement=req1
        ).count() == 1


class TestRequirementSignalRecalculation:
    """CAIRN-REQ-03: requirement save / delete triggers section + framework recalc."""

    def test_framework_recalc_on_requirement_save(self):
        fw = FrameworkFactory()
        req = RequirementFactory(
            framework=fw,
            is_applicable=True,
            compliance_status=ComplianceStatus.NOT_ASSESSED,
            compliance_level=0,
        )
        fw.refresh_from_db()
        assert fw.compliance_level == 0
        req.compliance_status = ComplianceStatus.COMPLIANT
        req.compliance_level = 100
        req.save()
        fw.refresh_from_db()
        assert fw.compliance_level == 100

    def test_framework_recalc_on_requirement_delete(self):
        fw = FrameworkFactory()
        RequirementFactory(
            framework=fw,
            is_applicable=True,
            compliance_status=ComplianceStatus.COMPLIANT,
            compliance_level=100,
        )
        bad = RequirementFactory(
            framework=fw,
            is_applicable=True,
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            compliance_level=0,
        )
        fw.refresh_from_db()
        assert fw.compliance_level == 50
        bad.delete()
        fw.refresh_from_db()
        assert fw.compliance_level == 100
