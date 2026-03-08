import pytest

from compliance.constants import (
    ActionPlanStatus,
    FindingStatus,
    FindingType,
)
from compliance.models.action_plan import ComplianceActionPlan
from compliance.tests.factories import (
    ComplianceAuditFactory,
    ComplianceControlFactory,
    FindingFactory,
    FrameworkFactory,
    RequirementFactory,
)
from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestFinding:
    def test_create_finding(self):
        finding = FindingFactory()
        assert finding.pk is not None
        assert finding.reference.startswith("FNDG-")
        assert finding.finding_type == FindingType.OBSERVATION

    def test_finding_str(self):
        finding = FindingFactory(name="Test finding")
        assert "Test finding" in str(finding)
        assert finding.reference in str(finding)

    def test_finding_types(self):
        for ft in FindingType:
            finding = FindingFactory(finding_type=ft)
            assert finding.finding_type == ft

    def test_finding_linked_to_audit(self):
        audit = ComplianceAuditFactory()
        finding = FindingFactory(audit=audit)
        assert finding.audit == audit
        assert finding in audit.audit_findings.all()

    def test_finding_linked_to_control(self):
        control = ComplianceControlFactory()
        finding = FindingFactory(control=control)
        assert finding.control == control
        assert finding in control.control_findings.all()

    def test_finding_linked_to_requirements(self):
        req1 = RequirementFactory()
        req2 = RequirementFactory(framework=req1.framework)
        finding = FindingFactory()
        finding.requirements.add(req1, req2)
        assert finding.requirements.count() == 2

    def test_related_findings(self):
        f1 = FindingFactory()
        f2 = FindingFactory()
        f3 = FindingFactory()
        f1.related_findings.add(f2, f3)
        assert f1.related_findings.count() == 2
        # M2M self-referential is symmetrical by default
        assert f2.related_findings.filter(pk=f1.pk).exists()


class TestFindingResolution:
    def test_unresolved_no_action_plans(self):
        finding = FindingFactory()
        assert not finding.is_resolved
        assert finding.status == FindingStatus.UNRESOLVED

    def test_unresolved_with_open_action_plan(self):
        finding = FindingFactory()
        owner = UserFactory()
        plan = ComplianceActionPlan.objects.create(
            name="Plan 1",
            gap_description="Gap",
            remediation_plan="Fix it",
            priority="high",
            owner=owner,
            target_date="2026-12-31",
            status=ActionPlanStatus.IN_PROGRESS,
        )
        finding.action_plans.add(plan)
        assert not finding.is_resolved
        assert finding.status == FindingStatus.UNRESOLVED

    def test_resolved_all_action_plans_completed(self):
        finding = FindingFactory()
        owner = UserFactory()
        plan = ComplianceActionPlan.objects.create(
            name="Plan 1",
            gap_description="Gap",
            remediation_plan="Fix it",
            priority="high",
            owner=owner,
            target_date="2026-12-31",
            status=ActionPlanStatus.COMPLETED,
        )
        finding.action_plans.add(plan)
        assert finding.is_resolved
        assert finding.status == FindingStatus.RESOLVED

    def test_unresolved_mixed_action_plans(self):
        finding = FindingFactory()
        owner = UserFactory()
        plan1 = ComplianceActionPlan.objects.create(
            name="Plan 1",
            gap_description="Gap",
            remediation_plan="Fix it",
            priority="high",
            owner=owner,
            target_date="2026-12-31",
            status=ActionPlanStatus.COMPLETED,
        )
        plan2 = ComplianceActionPlan.objects.create(
            name="Plan 2",
            gap_description="Gap 2",
            remediation_plan="Fix it too",
            priority="medium",
            owner=owner,
            target_date="2026-12-31",
            status=ActionPlanStatus.IN_PROGRESS,
        )
        finding.action_plans.add(plan1, plan2)
        assert not finding.is_resolved
        assert finding.status == FindingStatus.UNRESOLVED

    def test_finding_action_plan_reverse_relation(self):
        finding = FindingFactory()
        owner = UserFactory()
        plan = ComplianceActionPlan.objects.create(
            name="Plan 1",
            gap_description="Gap",
            remediation_plan="Fix it",
            priority="high",
            owner=owner,
            target_date="2026-12-31",
            status=ActionPlanStatus.PLANNED,
        )
        finding.action_plans.add(plan)
        assert plan.findings.first() == finding
