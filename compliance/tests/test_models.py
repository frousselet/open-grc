import pytest
from django.core.exceptions import ValidationError

from compliance.constants import ComplianceStatus
from compliance.tests.factories import (
    FrameworkFactory,
    MappingFactory,
    RequirementFactory,
)

pytestmark = pytest.mark.django_db


class TestFrameworkCompliance:
    """P0: compliance level recalculation."""

    def test_recalculate_no_requirements(self):
        fw = FrameworkFactory()
        fw.recalculate_compliance()
        fw.refresh_from_db()
        assert fw.compliance_level == 0

    def test_recalculate_with_requirements(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, compliance_level=100, is_applicable=True)
        RequirementFactory(framework=fw, compliance_level=50, is_applicable=True)
        fw.recalculate_compliance()
        fw.refresh_from_db()
        assert fw.compliance_level == 75

    def test_recalculate_excludes_not_applicable(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, compliance_level=100, is_applicable=True)
        RequirementFactory(
            framework=fw,
            compliance_level=0,
            is_applicable=True,
            compliance_status=ComplianceStatus.NOT_APPLICABLE,
        )
        fw.recalculate_compliance()
        fw.refresh_from_db()
        assert fw.compliance_level == 100

    def test_recalculate_excludes_non_applicable_flag(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, compliance_level=80, is_applicable=True)
        RequirementFactory(framework=fw, compliance_level=0, is_applicable=False)
        fw.recalculate_compliance()
        fw.refresh_from_db()
        assert fw.compliance_level == 80


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
