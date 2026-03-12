import pytest
from django.test import TestCase

from compliance.constants import (
    FindingType,
    FINDING_REFERENCE_PREFIXES,
    FINDING_TYPE_COMPLIANCE_LEVEL,
)
from compliance.models import Finding
from .factories import (
    ComplianceAssessmentFactory,
    FindingFactory,
    RequirementFactory,
)


@pytest.mark.django_db
class TestFindingModel:
    def test_create_finding(self):
        finding = FindingFactory()
        assert finding.pk is not None
        assert finding.reference.startswith("NCMAJ-")

    def test_reference_generation_by_type(self):
        """Each finding type generates a reference with the correct prefix."""
        assessment = ComplianceAssessmentFactory()
        for ft_value, prefix in FINDING_REFERENCE_PREFIXES.items():
            finding = FindingFactory(
                assessment=assessment,
                finding_type=ft_value,
            )
            assert finding.reference.startswith(f"{prefix}-"), (
                f"Expected {prefix}- prefix for {ft_value}, got {finding.reference}"
            )

    def test_reference_uniqueness(self):
        """References are unique and auto-increment."""
        f1 = FindingFactory(finding_type=FindingType.MAJOR_NON_CONFORMITY)
        f2 = FindingFactory(finding_type=FindingType.MAJOR_NON_CONFORMITY)
        assert f1.reference != f2.reference
        # Both start with NCMAJ-
        assert f1.reference.startswith("NCMAJ-")
        assert f2.reference.startswith("NCMAJ-")
        # Second should have a higher number
        num1 = int(f1.reference.split("-")[1])
        num2 = int(f2.reference.split("-")[1])
        assert num2 > num1

    def test_reference_across_types(self):
        """Different finding types have independent reference sequences."""
        f_major = FindingFactory(finding_type=FindingType.MAJOR_NON_CONFORMITY)
        f_obs = FindingFactory(finding_type=FindingType.OBSERVATION)
        assert f_major.reference.startswith("NCMAJ-")
        assert f_obs.reference.startswith("OBS-")

    def test_finding_requirements_m2m(self):
        """Findings can be linked to requirements."""
        assessment = ComplianceAssessmentFactory()
        req1 = RequirementFactory(framework=assessment.framework)
        req2 = RequirementFactory(framework=assessment.framework)
        finding = FindingFactory(assessment=assessment)
        finding.requirements.add(req1, req2)
        assert finding.requirements.count() == 2
        assert req1.findings.count() == 1

    def test_str_representation(self):
        finding = FindingFactory(finding_type=FindingType.OBSERVATION)
        assert "OBS-" in str(finding)

    def test_finding_type_compliance_level_mapping(self):
        """Verify compliance level mapping is complete."""
        for ft in FindingType:
            assert ft.value in FINDING_TYPE_COMPLIANCE_LEVEL, (
                f"Missing compliance level for {ft.value}"
            )

    def test_cascade_delete_with_assessment(self):
        """Findings are deleted when their assessment is deleted."""
        finding = FindingFactory()
        assessment_pk = finding.assessment.pk
        finding_pk = finding.pk
        finding.assessment.delete()
        assert not Finding.objects.filter(pk=finding_pk).exists()
