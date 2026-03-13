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
        fw.recalculate_compliance()
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
        fw.recalculate_compliance()
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
        fw.recalculate_compliance()
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
        fw.recalculate_compliance()
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
