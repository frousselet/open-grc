import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from risks.constants import ThreatType, TreatmentType
from risks.models import (
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskTreatmentPlan,
    Threat,
    Vulnerability,
)
from risks.tests.factories import (
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    RiskFactory,
    RiskLevelFactory,
    ScaleLevelFactory,
)

pytestmark = pytest.mark.django_db


# ── Helpers ─────────────────────────────────────────────────


def _superuser_client():
    """Return (client, user) where user is a logged-in superuser."""
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


def _build_criteria_3x3():
    """Create a 3x3 RiskCriteria with scale levels and risk levels."""
    criteria = RiskCriteriaFactory()
    for i in range(1, 4):
        ScaleLevelFactory(
            criteria=criteria, scale_type="likelihood", level=i, name=f"L{i}"
        )
        ScaleLevelFactory(
            criteria=criteria, scale_type="impact", level=i, name=f"I{i}"
        )
    for i in range(1, 4):
        RiskLevelFactory(criteria=criteria, level=i, name=f"R{i}")
    criteria.rebuild_risk_matrix()
    return criteria


# ── Risk Assessment Views ───────────────────────────────────


class TestRiskAssessmentListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:assessment-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:assessment-list"))
        assert resp.status_code == 200

    def test_list_contains_assessment(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory(name="TestAssessment")
        resp = client.get(reverse("risks:assessment-list"))
        assert resp.status_code == 200
        assert b"TestAssessment" in resp.content

    def test_list_filters_by_status(self):
        client, user = _superuser_client()
        RiskAssessmentFactory(name="DraftOne", status="draft")
        RiskAssessmentFactory(name="CompletedOne", status="completed")
        resp = client.get(reverse("risks:assessment-list"), {"status": "draft"})
        assert resp.status_code == 200
        assert b"DraftOne" in resp.content
        assert b"CompletedOne" not in resp.content


class TestRiskAssessmentDetailView:
    def test_login_required(self):
        assessment = RiskAssessmentFactory()
        resp = Client().get(
            reverse("risks:assessment-detail", args=[assessment.pk])
        )
        assert resp.status_code == 302

    def test_detail_loads_200(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        resp = client.get(
            reverse("risks:assessment-detail", args=[assessment.pk])
        )
        assert resp.status_code == 200

    def test_detail_contains_risks_context(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        RiskFactory(assessment=assessment, name="RiskInAssessment")
        resp = client.get(
            reverse("risks:assessment-detail", args=[assessment.pk])
        )
        assert "risks" in resp.context

    def test_detail_with_criteria_shows_matrices(self):
        client, user = _superuser_client()
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        resp = client.get(
            reverse("risks:assessment-detail", args=[assessment.pk])
        )
        assert resp.status_code == 200
        ctx = resp.context
        assert "matrix_criteria" in ctx
        assert ctx["matrix_criteria"] == criteria


class TestRiskAssessmentCreateView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:assessment-create"))
        assert resp.status_code == 302

    def test_get_form_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:assessment-create"))
        assert resp.status_code == 200

    def test_create_assessment(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("risks:assessment-create"),
            {"name": "New Assessment", "methodology": "iso27005", "status": "draft"},
        )
        assert resp.status_code == 302
        assert RiskAssessment.objects.filter(name="New Assessment").exists()
        assessment = RiskAssessment.objects.get(name="New Assessment")
        assert assessment.created_by == user


class TestRiskAssessmentUpdateView:
    def test_update_assessment(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory(name="OldName")
        resp = client.post(
            reverse("risks:assessment-update", args=[assessment.pk]),
            {"name": "UpdatedName", "methodology": "iso27005", "status": "draft"},
        )
        assert resp.status_code == 302
        assessment.refresh_from_db()
        assert assessment.name == "UpdatedName"


class TestRiskDashboardView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:dashboard"))
        assert resp.status_code == 302

    def test_dashboard_loads_200(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("risks:dashboard"))
        assert resp.status_code == 200
        assert b"Risk dashboard" in resp.content

    def test_dashboard_context_aggregates_counts(self):
        client, _ = _superuser_client()
        # Two risks under one assessment.
        a = RiskAssessmentFactory()
        RiskFactory(assessment=a, priority="critical", status="identified")
        RiskFactory(assessment=a, priority="medium", status="treated")
        resp = client.get(reverse("risks:dashboard"))
        ctx = resp.context
        assert ctx["risk_count_total"] == 2
        priorities = {p["key"]: p["count"] for p in ctx["risk_priority_breakdown"]}
        assert priorities["critical"] == 1
        assert priorities["medium"] == 1
        statuses = {s["key"]: s["count"] for s in ctx["risk_status_breakdown"]}
        assert statuses["identified"] == 1
        assert statuses["treated"] == 1

    def test_top_critical_risks_limited_to_ten(self):
        client, _ = _superuser_client()
        # 12 critical risks, all with current_risk_level=5
        for i in range(12):
            r = RiskFactory(priority="critical")
            r.current_risk_level = 5
            r.save(update_fields=["current_risk_level"])
        resp = client.get(reverse("risks:dashboard"))
        assert len(resp.context["top_critical_risks"]) == 10

    def test_overdue_treatment_plans_surface_in_context(self):
        from datetime import timedelta
        client, _ = _superuser_client()
        today = timezone.localdate()
        risk = RiskFactory()
        # One overdue (past target_date, not COMPLETED), one ok (future target).
        overdue = RiskTreatmentPlan.objects.create(
            risk=risk, name="LateOne", treatment_type="mitigate",
            status="in_progress", target_date=today - timedelta(days=2),
        )
        RiskTreatmentPlan.objects.create(
            risk=risk, name="OnTime", treatment_type="mitigate",
            status="in_progress", target_date=today + timedelta(days=10),
        )
        resp = client.get(reverse("risks:dashboard"))
        plans = resp.context["overdue_treatment_plans"]
        assert overdue in plans
        assert len(plans) == 1

    def test_expiring_acceptances_within_90_days(self):
        from datetime import timedelta
        from risks.models import RiskAcceptance
        client, _ = _superuser_client()
        today = timezone.localdate()
        risk = RiskFactory()
        soon = RiskAcceptance.objects.create(
            risk=risk, status="active", justification="J1",
            valid_until=today + timedelta(days=30),
        )
        far = RiskAcceptance.objects.create(
            risk=risk, status="active", justification="J2",
            valid_until=today + timedelta(days=180),
        )
        resp = client.get(reverse("risks:dashboard"))
        expiring = resp.context["expiring_acceptances"]
        assert soon in expiring
        assert far not in expiring

    def test_scope_filter_applied_to_dashboard(self):
        from accounts.models import Group, Permission
        from accounts.tests.factories import UserFactory as _UF
        from context.tests.factories import ScopeFactory

        scope_in = ScopeFactory()
        scope_out = ScopeFactory()
        a_in = RiskAssessmentFactory()
        a_in.scopes.add(scope_in)
        a_out = RiskAssessmentFactory()
        a_out.scopes.add(scope_out)
        RiskFactory(assessment=a_in, name="Inside")
        RiskFactory(assessment=a_out, name="Outside")

        group = Group.objects.create(name="dash scope group")
        group.allowed_scopes.add(scope_in)
        for codename in ["risks.risk.read"]:
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={"name": codename, "module": "risks", "feature": "risk", "action": "read", "is_system": True},
            )
            group.permissions.add(perm)
        user = _UF(is_superuser=False, is_staff=False)
        group.users.add(user)

        client = Client()
        client.force_login(user)
        resp = client.get(reverse("risks:dashboard"))
        assert resp.status_code == 200
        assert resp.context["risk_count_total"] == 1


class TestRiskAssessmentDeleteView:
    def test_login_required(self):
        assessment = RiskAssessmentFactory()
        resp = Client().get(
            reverse("risks:assessment-delete", args=[assessment.pk])
        )
        assert resp.status_code == 302

    def test_delete_assessment(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        pk = assessment.pk
        resp = client.post(
            reverse("risks:assessment-delete", args=[pk])
        )
        assert resp.status_code == 302
        assert not RiskAssessment.objects.filter(pk=pk).exists()


class TestRiskAssessmentApproveView:
    def test_approve_assessment(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        assert assessment.is_approved is False
        resp = client.post(reverse("risks:assessment-approve", args=[assessment.pk]))
        assert resp.status_code == 302
        assessment.refresh_from_db()
        assert assessment.is_approved is True
        assert assessment.approved_by == user

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        assessment = RiskAssessmentFactory()
        resp = client.get(reverse("risks:assessment-detail", args=[assessment.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:assessment-approve", args=[assessment.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content


# ── Risk Views ──────────────────────────────────────────────


class TestRiskListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:risk-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:risk-list"))
        assert resp.status_code == 200

    def test_list_contains_risk(self):
        client, user = _superuser_client()
        RiskFactory(name="VisibleRisk")
        resp = client.get(reverse("risks:risk-list"))
        assert b"VisibleRisk" in resp.content

    def test_list_filters_by_assessment(self):
        client, user = _superuser_client()
        a1 = RiskAssessmentFactory()
        a2 = RiskAssessmentFactory()
        RiskFactory(assessment=a1, name="RiskA1")
        RiskFactory(assessment=a2, name="RiskA2")
        resp = client.get(
            reverse("risks:risk-list"), {"assessment": str(a1.pk)}
        )
        assert b"RiskA1" in resp.content
        assert b"RiskA2" not in resp.content

    def test_list_filters_by_status(self):
        client, user = _superuser_client()
        RiskFactory(name="Identified", status="identified")
        RiskFactory(name="Closed", status="closed")
        resp = client.get(reverse("risks:risk-list"), {"status": "identified"})
        assert b"Identified" in resp.content
        assert b"Closed" not in resp.content

    def test_list_filters_by_priority(self):
        client, user = _superuser_client()
        RiskFactory(name="LowPri", priority="low")
        RiskFactory(name="CriticalPri", priority="critical")
        resp = client.get(reverse("risks:risk-list"), {"priority": "critical"})
        assert b"CriticalPri" in resp.content
        assert b"LowPri" not in resp.content

    def test_list_filters_by_treatment_decision(self):
        client, _ = _superuser_client()
        RiskFactory(name="AvoidR", treatment_decision="avoid")
        RiskFactory(name="MitigateR", treatment_decision="mitigate")
        resp = client.get(
            reverse("risks:risk-list"), {"treatment_decision": "avoid"},
        )
        assert b"AvoidR" in resp.content
        assert b"MitigateR" not in resp.content

    def test_list_filters_by_date_range(self):
        from datetime import timedelta
        client, _ = _superuser_client()
        old = RiskFactory(name="OldRisk")
        recent = RiskFactory(name="RecentRisk")
        # Force created_at by direct update (auto_now_add blocks normal assignment)
        from risks.models import Risk
        Risk.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=30),
        )
        Risk.objects.filter(pk=recent.pk).update(
            created_at=timezone.now() - timedelta(days=1),
        )
        cutoff = (timezone.now() - timedelta(days=15)).date().isoformat()
        resp = client.get(
            reverse("risks:risk-list"), {"date_after": cutoff},
        )
        assert b"RecentRisk" in resp.content
        assert b"OldRisk" not in resp.content

    def test_list_filters_by_essential_asset(self):
        from assets.tests.factories import EssentialAssetFactory
        client, _ = _superuser_client()
        asset = EssentialAssetFactory()
        in_asset = RiskFactory(name="InAsset")
        out_asset = RiskFactory(name="OutAsset")
        in_asset.affected_essential_assets.add(asset)
        resp = client.get(
            reverse("risks:risk-list"), {"essential_asset": str(asset.pk)},
        )
        assert b"InAsset" in resp.content
        assert b"OutAsset" not in resp.content

    def test_list_filters_by_linked_requirement(self):
        from compliance.tests.factories import (
            FrameworkFactory, RequirementFactory,
        )
        client, _ = _superuser_client()
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, requirement_number="A.5.99")
        r_with = RiskFactory(name="WithReq")
        r_without = RiskFactory(name="WithoutReq")
        r_with.linked_requirements.add(req)
        resp = client.get(
            reverse("risks:risk-list"), {"linked_requirement": str(req.pk)},
        )
        assert b"WithReq" in resp.content
        assert b"WithoutReq" not in resp.content

    def test_list_filters_by_threat_via_iso27005_source(self):
        from risks.models import ISO27005Risk
        from risks.tests.factories import ThreatFactory, VulnerabilityFactory
        client, _ = _superuser_client()
        threat = ThreatFactory()
        vuln = VulnerabilityFactory()
        assessment = RiskAssessmentFactory()
        r_with = RiskFactory(assessment=assessment, name="ThreatHit")
        r_without = RiskFactory(assessment=assessment, name="ThreatMiss")
        ISO27005Risk.objects.create(
            assessment=assessment, threat=threat, vulnerability=vuln, risk=r_with,
        )
        resp = client.get(
            reverse("risks:risk-list"), {"threat": str(threat.pk)},
        )
        assert b"ThreatHit" in resp.content
        assert b"ThreatMiss" not in resp.content

    def test_context_exposes_choice_lists(self):
        from assets.tests.factories import EssentialAssetFactory
        client, _ = _superuser_client()
        asset = EssentialAssetFactory(name="ContextEssential")
        risk = RiskFactory()
        risk.affected_essential_assets.add(asset)
        resp = client.get(reverse("risks:risk-list"))
        choices = list(resp.context["essential_asset_choices"])
        assert asset in choices
        assert "treatment_decision_choices" in resp.context


class TestRiskDetailView:
    def test_login_required(self):
        risk = RiskFactory()
        resp = Client().get(reverse("risks:risk-detail", args=[risk.pk]))
        assert resp.status_code == 302

    def test_detail_loads_200(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        resp = client.get(reverse("risks:risk-detail", args=[risk.pk]))
        assert resp.status_code == 200

    def test_detail_context_has_treatment_plans(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        resp = client.get(reverse("risks:risk-detail", args=[risk.pk]))
        assert "treatment_plans" in resp.context
        assert "acceptances" in resp.context


class TestRiskCreateView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:risk-create"))
        assert resp.status_code == 302

    def test_redirects_without_assessment_param(self):
        """RiskCreateView redirects to assessment list when no assessment query param."""
        client, user = _superuser_client()
        resp = client.get(reverse("risks:risk-create"))
        assert resp.status_code == 302
        assert "assessment" in resp.url

    def test_get_form_with_assessment_param(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        resp = client.get(
            reverse("risks:risk-create"),
            {"assessment": str(assessment.pk)},
        )
        assert resp.status_code == 200

    def test_create_risk(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        resp = client.post(
            reverse("risks:risk-create") + f"?assessment={assessment.pk}",
            {
                "assessment": str(assessment.pk),
                "name": "New Risk",
                "risk_source": "manual",
                "treatment_decision": "not_decided",
                "priority": "low",
                "status": "identified",
            },
        )
        assert resp.status_code == 302
        assert Risk.objects.filter(name="New Risk").exists()


class TestRiskUpdateView:
    def test_update_risk(self):
        client, user = _superuser_client()
        assessment = RiskAssessmentFactory()
        risk = RiskFactory(assessment=assessment, name="OldRisk")
        resp = client.post(
            reverse("risks:risk-update", args=[risk.pk]),
            {
                "assessment": str(assessment.pk),
                "name": "UpdatedRisk",
                "risk_source": "manual",
                "treatment_decision": "not_decided",
                "priority": "medium",
                "status": "identified",
            },
        )
        assert resp.status_code == 302
        risk.refresh_from_db()
        assert risk.name == "UpdatedRisk"


class TestRiskDeleteView:
    def test_delete_risk(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        pk = risk.pk
        resp = client.post(reverse("risks:risk-delete", args=[pk]))
        assert resp.status_code == 302
        assert not Risk.objects.filter(pk=pk).exists()


class TestRiskApproveView:
    def test_approve_risk(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        assert risk.is_approved is False
        resp = client.post(reverse("risks:risk-approve", args=[risk.pk]))
        assert resp.status_code == 302
        risk.refresh_from_db()
        assert risk.is_approved is True
        assert risk.approved_by == user

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        risk = RiskFactory()
        resp = client.get(reverse("risks:risk-detail", args=[risk.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:risk-approve", args=[risk.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content


# ── Treatment Plan Views ────────────────────────────────────


class TestTreatmentPlanListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:treatment-plan-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:treatment-plan-list"))
        assert resp.status_code == 200

    def test_list_filters_by_status(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        RiskTreatmentPlan.objects.create(
            risk=risk, name="PlannedPlan", treatment_type="mitigate", status="planned"
        )
        RiskTreatmentPlan.objects.create(
            risk=risk, name="CompletedPlan", treatment_type="mitigate", status="completed"
        )
        resp = client.get(
            reverse("risks:treatment-plan-list"), {"status": "planned"}
        )
        assert b"PlannedPlan" in resp.content
        assert b"CompletedPlan" not in resp.content


class TestTreatmentPlanDetailView:
    def test_detail_loads_200(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        plan = RiskTreatmentPlan.objects.create(
            risk=risk, name="Detail Plan", treatment_type="mitigate"
        )
        resp = client.get(
            reverse("risks:treatment-plan-detail", args=[plan.pk])
        )
        assert resp.status_code == 200
        assert "actions" in resp.context


class TestTreatmentPlanCreateView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:treatment-plan-create"))
        assert resp.status_code == 302

    def test_get_form_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:treatment-plan-create"))
        assert resp.status_code == 200

    def test_create_plan(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        resp = client.post(
            reverse("risks:treatment-plan-create"),
            {
                "risk": str(risk.pk),
                "name": "New Plan",
                "treatment_type": "mitigate",
                "status": "planned",
                "progress_percentage": 0,
            },
        )
        assert resp.status_code == 302
        assert RiskTreatmentPlan.objects.filter(name="New Plan").exists()


class TestTreatmentPlanUpdateView:
    def test_update_plan(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        plan = RiskTreatmentPlan.objects.create(
            risk=risk, name="OldPlan", treatment_type="mitigate"
        )
        resp = client.post(
            reverse("risks:treatment-plan-update", args=[plan.pk]),
            {
                "risk": str(risk.pk),
                "name": "UpdatedPlan",
                "treatment_type": "transfer",
                "status": "in_progress",
                "progress_percentage": 50,
            },
        )
        assert resp.status_code == 302
        plan.refresh_from_db()
        assert plan.name == "UpdatedPlan"
        assert plan.treatment_type == "transfer"


class TestTreatmentPlanDeleteView:
    def test_delete_plan(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        plan = RiskTreatmentPlan.objects.create(
            risk=risk, name="ToDelete", treatment_type="mitigate"
        )
        pk = plan.pk
        resp = client.post(
            reverse("risks:treatment-plan-delete", args=[pk])
        )
        assert resp.status_code == 302
        assert not RiskTreatmentPlan.objects.filter(pk=pk).exists()


class TestRiskBulkActionView:
    """C4: bulk approve / delete on the risk register."""

    def test_bulk_approve_marks_all_selected(self):
        client, user = _superuser_client()
        r1 = RiskFactory()
        r2 = RiskFactory()
        r3 = RiskFactory()
        resp = client.post(
            reverse("risks:risk-bulk-action"),
            {"action": "approve", "risk_ids": [str(r1.pk), str(r3.pk)]},
        )
        assert resp.status_code == 302
        r1.refresh_from_db()
        r2.refresh_from_db()
        r3.refresh_from_db()
        assert r1.is_approved is True
        assert r2.is_approved is False
        assert r3.is_approved is True
        assert r1.approved_by == user

    def test_bulk_delete_removes_selected(self):
        client, _ = _superuser_client()
        r1 = RiskFactory()
        r2 = RiskFactory()
        resp = client.post(
            reverse("risks:risk-bulk-action"),
            {"action": "delete", "risk_ids": [str(r1.pk)]},
        )
        assert resp.status_code == 302
        assert not Risk.objects.filter(pk=r1.pk).exists()
        assert Risk.objects.filter(pk=r2.pk).exists()

    def test_bulk_unknown_action_warns(self):
        client, _ = _superuser_client()
        r1 = RiskFactory()
        resp = client.post(
            reverse("risks:risk-bulk-action"),
            {"action": "burn", "risk_ids": [str(r1.pk)]},
        )
        # Redirects with a warning, no destruction.
        assert resp.status_code == 302
        assert Risk.objects.filter(pk=r1.pk).exists()

    def test_bulk_no_selection_warns(self):
        client, _ = _superuser_client()
        RiskFactory()
        resp = client.post(
            reverse("risks:risk-bulk-action"),
            {"action": "approve"},
        )
        assert resp.status_code == 302

    def test_bulk_scope_filtered_ignores_outsiders(self):
        from accounts.models import Group, Permission
        from accounts.tests.factories import UserFactory as _UF
        from context.tests.factories import ScopeFactory

        scope_in = ScopeFactory()
        scope_out = ScopeFactory()
        a_in = RiskAssessmentFactory()
        a_in.scopes.add(scope_in)
        a_out = RiskAssessmentFactory()
        a_out.scopes.add(scope_out)
        r_in = RiskFactory(assessment=a_in)
        r_out = RiskFactory(assessment=a_out)

        group = Group.objects.create(name="bulk scope group")
        group.allowed_scopes.add(scope_in)
        for codename in ["risks.risk.read", "risks.risk.delete"]:
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename, "module": "risks", "feature": "risk",
                    "action": codename.split(".")[-1], "is_system": True,
                },
            )
            group.permissions.add(perm)
        user = _UF(is_superuser=False, is_staff=False)
        group.users.add(user)

        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse("risks:risk-bulk-action"),
            {"action": "delete", "risk_ids": [str(r_in.pk), str(r_out.pk)]},
        )
        assert resp.status_code == 302
        assert not Risk.objects.filter(pk=r_in.pk).exists()
        assert Risk.objects.filter(pk=r_out.pk).exists()


class TestTreatmentActionViews:
    """C3: inline HTMX edit/create/delete of TreatmentAction rows."""

    def _make_plan(self):
        risk = RiskFactory()
        return RiskTreatmentPlan.objects.create(
            risk=risk, name="ParentPlan", treatment_type="mitigate",
        )

    def test_create_action_redirects_to_plan_detail(self):
        client, _ = _superuser_client()
        plan = self._make_plan()
        resp = client.post(
            reverse("risks:treatment-action-create", args=[plan.pk]),
            {
                "treatment_plan": str(plan.pk),
                "description": "Patch server",
                "status": "planned",
                "order": 1,
            },
        )
        assert resp.status_code == 302
        assert plan.actions.filter(description="Patch server").exists()

    def test_update_action(self):
        from risks.tests.factories import TreatmentActionFactory
        client, _ = _superuser_client()
        plan = self._make_plan()
        action = TreatmentActionFactory(
            treatment_plan=plan, description="Old", order=2,
        )
        resp = client.post(
            reverse("risks:treatment-action-update", args=[action.pk]),
            {
                "treatment_plan": str(plan.pk),
                "description": "Renamed",
                "status": "in_progress",
                "order": 2,
            },
        )
        assert resp.status_code == 302
        action.refresh_from_db()
        assert action.description == "Renamed"
        assert action.status == "in_progress"

    def test_delete_action(self):
        from risks.tests.factories import TreatmentActionFactory
        client, _ = _superuser_client()
        plan = self._make_plan()
        action = TreatmentActionFactory(treatment_plan=plan)
        pk = action.pk
        resp = client.post(
            reverse("risks:treatment-action-delete", args=[pk]),
        )
        assert resp.status_code == 302
        assert not plan.actions.filter(pk=pk).exists()

    def test_detail_exposes_inline_buttons(self):
        from risks.tests.factories import TreatmentActionFactory
        client, _ = _superuser_client()
        plan = self._make_plan()
        action = TreatmentActionFactory(treatment_plan=plan)
        resp = client.get(reverse("risks:treatment-plan-detail", args=[plan.pk]))
        assert resp.status_code == 200
        body = resp.content
        assert reverse("risks:treatment-action-create", args=[plan.pk]).encode() in body
        assert reverse("risks:treatment-action-update", args=[action.pk]).encode() in body
        assert reverse("risks:treatment-action-delete", args=[action.pk]).encode() in body


class TestTreatmentPlanApproveView:
    def test_approve_plan(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        plan = RiskTreatmentPlan.objects.create(
            risk=risk, name="ToApprove", treatment_type="mitigate",
        )
        assert plan.is_approved is False
        resp = client.post(reverse("risks:treatment-plan-approve", args=[plan.pk]))
        assert resp.status_code == 302
        plan.refresh_from_db()
        assert plan.is_approved is True
        assert plan.approved_by == user

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        risk = RiskFactory()
        plan = RiskTreatmentPlan.objects.create(
            risk=risk, name="ApproveURL", treatment_type="mitigate",
        )
        resp = client.get(reverse("risks:treatment-plan-detail", args=[plan.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:treatment-plan-approve", args=[plan.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content


# ── Risk Acceptance Views ───────────────────────────────────


class TestRiskAcceptanceListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:acceptance-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:acceptance-list"))
        assert resp.status_code == 200


class TestRiskAcceptanceDetailView:
    def test_detail_loads_200(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(
            risk=risk, justification="Justified", status="active"
        )
        resp = client.get(
            reverse("risks:acceptance-detail", args=[acceptance.pk])
        )
        assert resp.status_code == 200


class TestRiskAcceptanceCreateView:
    def test_get_form_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:acceptance-create"))
        assert resp.status_code == 200

    def test_create_acceptance(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        resp = client.post(
            reverse("risks:acceptance-create"),
            {
                "risk": str(risk.pk),
                "justification": "Accepted because low impact",
            },
        )
        assert resp.status_code == 302
        assert RiskAcceptance.objects.filter(risk=risk).exists()


class TestRiskAcceptanceDeleteView:
    def test_delete_acceptance(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(
            risk=risk, justification="To be deleted"
        )
        pk = acceptance.pk
        resp = client.post(
            reverse("risks:acceptance-delete", args=[pk])
        )
        assert resp.status_code == 302
        assert not RiskAcceptance.objects.filter(pk=pk).exists()


class TestRiskAcceptanceApproveView:
    def test_login_required(self):
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(risk=risk, justification="J")
        resp = Client().post(reverse("risks:acceptance-approve", args=[acceptance.pk]))
        assert resp.status_code == 302

    def test_approve_acceptance(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(
            risk=risk, justification="J", status="active"
        )
        assert acceptance.is_approved is False
        resp = client.post(reverse("risks:acceptance-approve", args=[acceptance.pk]))
        assert resp.status_code == 302
        acceptance.refresh_from_db()
        assert acceptance.is_approved is True
        assert acceptance.approved_by == user
        assert acceptance.approved_at is not None

    def test_approve_only_accepts_post(self):
        client, _ = _superuser_client()
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(risk=risk, justification="J")
        resp = client.get(reverse("risks:acceptance-approve", args=[acceptance.pk]))
        assert resp.status_code == 405

    def test_approve_without_permission_redirects(self):
        user = UserFactory(is_superuser=False, is_staff=False)
        client = Client()
        client.force_login(user)
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(risk=risk, justification="J")
        resp = client.post(reverse("risks:acceptance-approve", args=[acceptance.pk]))
        # PermissionRequiredMixin denies before the view runs
        assert resp.status_code in (302, 403)
        acceptance.refresh_from_db()
        assert acceptance.is_approved is False

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(risk=risk, justification="J")
        resp = client.get(reverse("risks:acceptance-detail", args=[acceptance.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:acceptance-approve", args=[acceptance.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content

    def test_update_resets_approval(self):
        client, user = _superuser_client()
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(
            risk=risk, justification="Original", status="active",
            is_approved=True, approved_by=user,
        )
        resp = client.post(
            reverse("risks:acceptance-update", args=[acceptance.pk]),
            {
                "risk": str(risk.pk),
                "justification": "Updated justification",
                "status": "active",
            },
        )
        assert resp.status_code == 302
        acceptance.refresh_from_db()
        assert acceptance.is_approved is False
        assert acceptance.approved_by is None


# ── Threat Views ────────────────────────────────────────────


class TestThreatListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:threat-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:threat-list"))
        assert resp.status_code == 200

    def test_list_contains_threat(self):
        client, user = _superuser_client()
        Threat.objects.create(name="PhishingThreat", type=ThreatType.DELIBERATE)
        resp = client.get(reverse("risks:threat-list"))
        assert b"PhishingThreat" in resp.content


class TestThreatDetailView:
    def test_detail_loads_200(self):
        client, user = _superuser_client()
        threat = Threat.objects.create(
            name="DetailThreat", type=ThreatType.DELIBERATE
        )
        resp = client.get(reverse("risks:threat-detail", args=[threat.pk]))
        assert resp.status_code == 200


class TestThreatCreateView:
    def test_get_form_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:threat-create"))
        assert resp.status_code == 200

    def test_create_threat(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("risks:threat-create"),
            {
                "name": "New Threat",
                "type": "deliberate",
                "status": "active",
            },
        )
        assert resp.status_code == 302
        assert Threat.objects.filter(name="New Threat").exists()


class TestThreatUpdateView:
    def test_update_threat(self):
        client, user = _superuser_client()
        threat = Threat.objects.create(
            name="OldThreat", type=ThreatType.DELIBERATE
        )
        resp = client.post(
            reverse("risks:threat-update", args=[threat.pk]),
            {
                "name": "UpdatedThreat",
                "type": "accidental",
                "status": "active",
            },
        )
        assert resp.status_code == 302
        threat.refresh_from_db()
        assert threat.name == "UpdatedThreat"
        assert threat.type == "accidental"


class TestThreatDeleteView:
    def test_delete_threat(self):
        client, user = _superuser_client()
        threat = Threat.objects.create(
            name="ToDeleteThreat", type=ThreatType.DELIBERATE
        )
        pk = threat.pk
        resp = client.post(reverse("risks:threat-delete", args=[pk]))
        assert resp.status_code == 302
        assert not Threat.objects.filter(pk=pk).exists()


# ── Vulnerability Views ─────────────────────────────────────


class TestVulnerabilityListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:vulnerability-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:vulnerability-list"))
        assert resp.status_code == 200

    def test_list_contains_vulnerability(self):
        client, user = _superuser_client()
        Vulnerability.objects.create(name="MissingPatch", severity="high")
        resp = client.get(reverse("risks:vulnerability-list"))
        assert b"MissingPatch" in resp.content


class TestVulnerabilityDetailView:
    def test_detail_loads_200(self):
        client, user = _superuser_client()
        vuln = Vulnerability.objects.create(name="DetailVuln", severity="medium")
        resp = client.get(
            reverse("risks:vulnerability-detail", args=[vuln.pk])
        )
        assert resp.status_code == 200


class TestVulnerabilityCreateView:
    def test_get_form_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:vulnerability-create"))
        assert resp.status_code == 200

    def test_create_vulnerability(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("risks:vulnerability-create"),
            {
                "name": "New Vuln",
                "severity": "high",
                "status": "identified",
            },
        )
        assert resp.status_code == 302
        assert Vulnerability.objects.filter(name="New Vuln").exists()


class TestVulnerabilityUpdateView:
    def test_update_vulnerability(self):
        client, user = _superuser_client()
        vuln = Vulnerability.objects.create(
            name="OldVuln", severity="medium"
        )
        resp = client.post(
            reverse("risks:vulnerability-update", args=[vuln.pk]),
            {
                "name": "UpdatedVuln",
                "severity": "critical",
                "status": "confirmed",
            },
        )
        assert resp.status_code == 302
        vuln.refresh_from_db()
        assert vuln.name == "UpdatedVuln"
        assert vuln.severity == "critical"


class TestVulnerabilityDeleteView:
    def test_delete_vulnerability(self):
        client, user = _superuser_client()
        vuln = Vulnerability.objects.create(
            name="ToDeleteVuln", severity="low"
        )
        pk = vuln.pk
        resp = client.post(
            reverse("risks:vulnerability-delete", args=[pk])
        )
        assert resp.status_code == 302
        assert not Vulnerability.objects.filter(pk=pk).exists()


class TestThreatApproveView:
    def test_approve_threat(self):
        client, user = _superuser_client()
        threat = Threat.objects.create(name="Phish", type=ThreatType.DELIBERATE)
        assert threat.is_approved is False
        resp = client.post(reverse("risks:threat-approve", args=[threat.pk]))
        assert resp.status_code == 302
        threat.refresh_from_db()
        assert threat.is_approved is True
        assert threat.approved_by == user

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        threat = Threat.objects.create(name="Phish2", type=ThreatType.DELIBERATE)
        resp = client.get(reverse("risks:threat-detail", args=[threat.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:threat-approve", args=[threat.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content

    def test_update_resets_approval(self):
        client, user = _superuser_client()
        threat = Threat.objects.create(
            name="ApprovedThreat", type=ThreatType.DELIBERATE,
            is_approved=True, approved_by=user,
        )
        resp = client.post(
            reverse("risks:threat-update", args=[threat.pk]),
            {"name": "Renamed", "type": ThreatType.DELIBERATE, "status": "active"},
        )
        assert resp.status_code == 302
        threat.refresh_from_db()
        assert threat.is_approved is False
        assert threat.approved_by is None


class TestVulnerabilityApproveView:
    def test_approve_vulnerability(self):
        client, user = _superuser_client()
        vuln = Vulnerability.objects.create(name="VulnApprove", severity="medium")
        assert vuln.is_approved is False
        resp = client.post(reverse("risks:vulnerability-approve", args=[vuln.pk]))
        assert resp.status_code == 302
        vuln.refresh_from_db()
        assert vuln.is_approved is True
        assert vuln.approved_by == user

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        vuln = Vulnerability.objects.create(name="VulnApprove2", severity="low")
        resp = client.get(reverse("risks:vulnerability-detail", args=[vuln.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:vulnerability-approve", args=[vuln.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content


class TestISO27005RiskApproveView:
    def _make_analysis(self):
        threat = Threat.objects.create(name="T-iso", type=ThreatType.DELIBERATE)
        vuln = Vulnerability.objects.create(name="V-iso", severity="medium")
        assessment = RiskAssessmentFactory()
        from risks.models import ISO27005Risk
        return ISO27005Risk.objects.create(
            assessment=assessment, threat=threat, vulnerability=vuln,
        )

    def test_approve_iso27005(self):
        client, user = _superuser_client()
        analysis = self._make_analysis()
        assert analysis.is_approved is False
        resp = client.post(reverse("risks:iso27005-approve", args=[analysis.pk]))
        assert resp.status_code == 302
        analysis.refresh_from_db()
        assert analysis.is_approved is True
        assert analysis.approved_by == user

    def test_detail_exposes_approve_url(self):
        client, _ = _superuser_client()
        analysis = self._make_analysis()
        resp = client.get(reverse("risks:iso27005-detail", args=[analysis.pk]))
        assert resp.status_code == 200
        # The legacy approval bar is retired: validation goes through the
        # lifecycle stepper (the approve endpoint stays for API compat).
        assert reverse("risks:iso27005-approve", args=[analysis.pk]).encode() not in resp.content
        assert b"workflow-stepper-" in resp.content


# ── Risk Criteria Views ─────────────────────────────────────


class TestRiskCriteriaListView:
    def test_login_required(self):
        resp = Client().get(reverse("risks:criteria-list"))
        assert resp.status_code == 302

    def test_list_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("risks:criteria-list"))
        assert resp.status_code == 200


class TestRiskCriteriaDetailView:
    def test_detail_loads_200(self):
        client, user = _superuser_client()
        criteria = RiskCriteriaFactory(name="TestCriteria")
        resp = client.get(
            reverse("risks:criteria-detail", args=[criteria.pk])
        )
        assert resp.status_code == 200
        assert "scale_levels" in resp.context
        assert "risk_levels" in resp.context


class TestRiskCriteriaDeleteView:
    def test_delete_criteria(self):
        client, user = _superuser_client()
        criteria = RiskCriteriaFactory()
        pk = criteria.pk
        resp = client.post(
            reverse("risks:criteria-delete", args=[pk])
        )
        assert resp.status_code == 302
        assert not RiskCriteria.objects.filter(pk=pk).exists()


# ── Risk Model Validation ───────────────────────────────────


class TestRiskClean:
    """Test Risk.clean() validation for likelihood/impact levels."""

    def test_valid_levels_pass_clean(self):
        """Valid likelihood and impact values should not raise."""
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=1,
            current_impact=2,
        )
        # Should not raise
        risk.clean()

    def test_invalid_likelihood_raises(self):
        """Likelihood value outside scale levels should raise ValidationError."""
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=99,
            current_impact=1,
        )
        with pytest.raises(ValidationError) as exc_info:
            risk.clean()
        assert "current_likelihood" in exc_info.value.message_dict

    def test_invalid_impact_raises(self):
        """Impact value outside scale levels should raise ValidationError."""
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=1,
            current_impact=99,
        )
        with pytest.raises(ValidationError) as exc_info:
            risk.clean()
        assert "current_impact" in exc_info.value.message_dict

    def test_none_values_pass_clean(self):
        """None values for likelihood/impact should pass validation."""
        assessment = RiskAssessmentFactory()
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=None,
            current_impact=None,
        )
        risk.clean()  # Should not raise

    def test_all_level_fields_validated(self):
        """All six likelihood/impact fields should be validated."""
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(
            assessment=assessment,
            initial_likelihood=99,
            initial_impact=99,
            current_likelihood=99,
            current_impact=99,
            residual_likelihood=99,
            residual_impact=99,
        )
        with pytest.raises(ValidationError) as exc_info:
            risk.clean()
        errors = exc_info.value.message_dict
        assert "initial_likelihood" in errors
        assert "initial_impact" in errors
        assert "current_likelihood" in errors
        assert "current_impact" in errors
        assert "residual_likelihood" in errors
        assert "residual_impact" in errors

    def test_default_scales_used_when_no_criteria(self):
        """When no criteria exist, default 1-5 scale should be used."""
        # Delete any existing criteria to force default fallback
        RiskCriteria.objects.all().delete()
        assessment = RiskAssessmentFactory(risk_criteria=None)
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=3,
            current_impact=4,
        )
        risk.clean()  # Should not raise - 3 and 4 are valid in default 1-5

    def test_default_scales_reject_invalid(self):
        """Default 1-5 scale should reject values outside range."""
        RiskCriteria.objects.all().delete()
        assessment = RiskAssessmentFactory(risk_criteria=None)
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=10,
            current_impact=1,
        )
        with pytest.raises(ValidationError) as exc_info:
            risk.clean()
        assert "current_likelihood" in exc_info.value.message_dict


# ── Treatment Plan Model Validation ─────────────────────────


class TestTreatmentPlanClean:
    """Test RiskTreatmentPlan.clean() validation."""

    def test_valid_levels_pass_clean(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        plan = RiskTreatmentPlan(
            risk=risk,
            name="Valid Plan",
            treatment_type=TreatmentType.MITIGATE,
            expected_residual_likelihood=2,
            expected_residual_impact=1,
        )
        plan.clean()  # Should not raise

    def test_invalid_residual_likelihood_raises(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        plan = RiskTreatmentPlan(
            risk=risk,
            name="Invalid Plan",
            treatment_type=TreatmentType.MITIGATE,
            expected_residual_likelihood=99,
            expected_residual_impact=1,
        )
        with pytest.raises(ValidationError) as exc_info:
            plan.clean()
        assert "expected_residual_likelihood" in exc_info.value.message_dict

    def test_invalid_residual_impact_raises(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        plan = RiskTreatmentPlan(
            risk=risk,
            name="Invalid Plan",
            treatment_type=TreatmentType.MITIGATE,
            expected_residual_likelihood=1,
            expected_residual_impact=99,
        )
        with pytest.raises(ValidationError) as exc_info:
            plan.clean()
        assert "expected_residual_impact" in exc_info.value.message_dict

    def test_none_values_pass_clean(self):
        risk = RiskFactory()
        plan = RiskTreatmentPlan(
            risk=risk,
            name="Plan with None",
            treatment_type=TreatmentType.MITIGATE,
            expected_residual_likelihood=None,
            expected_residual_impact=None,
        )
        plan.clean()  # Should not raise

    def test_default_scales_used_when_no_criteria(self):
        """When no criteria, default 1-5 scale should apply."""
        RiskCriteria.objects.all().delete()
        assessment = RiskAssessmentFactory(risk_criteria=None)
        risk = RiskFactory(assessment=assessment)
        plan = RiskTreatmentPlan(
            risk=risk,
            name="Default Plan",
            treatment_type=TreatmentType.MITIGATE,
            expected_residual_likelihood=3,
            expected_residual_impact=2,
        )
        plan.clean()  # Should not raise


# ── Risk.calculate_risk_level ───────────────────────────────


class TestRiskCalculateRiskLevel:
    def test_returns_level_from_matrix(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        level = risk.calculate_risk_level(3, 3)
        assert level == 3  # max in 3x3 matrix

    def test_returns_none_when_no_criteria(self):
        assessment = RiskAssessmentFactory(risk_criteria=None)
        risk = RiskFactory(assessment=assessment)
        assert risk.calculate_risk_level(1, 1) is None

    def test_returns_none_with_none_inputs(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(assessment=assessment)
        assert risk.calculate_risk_level(None, 3) is None
        assert risk.calculate_risk_level(3, None) is None


# ── Risk.save auto-calculation ──────────────────────────────


class TestRiskSaveAutoCalculation:
    def test_save_calculates_all_risk_levels(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(
            assessment=assessment,
            initial_likelihood=1,
            initial_impact=1,
            current_likelihood=2,
            current_impact=2,
            residual_likelihood=3,
            residual_impact=3,
        )
        risk.save()
        risk.refresh_from_db()
        assert risk.initial_risk_level is not None
        assert risk.current_risk_level is not None
        assert risk.residual_risk_level is not None

    def test_save_skips_when_likelihood_is_none(self):
        criteria = _build_criteria_3x3()
        assessment = RiskAssessmentFactory(risk_criteria=criteria)
        risk = RiskFactory(
            assessment=assessment,
            current_likelihood=None,
            current_impact=2,
        )
        risk.save()
        risk.refresh_from_db()
        # Should not auto-calculate when likelihood is None
        assert risk.current_risk_level is None


# ── Model __str__ methods ───────────────────────────────────


class TestModelStrMethods:
    def test_risk_str(self):
        risk = RiskFactory(name="Test Risk")
        result = str(risk)
        assert "Test Risk" in result
        assert risk.reference in result

    def test_assessment_str(self):
        assessment = RiskAssessmentFactory(name="Test Assessment")
        result = str(assessment)
        assert "Test Assessment" in result

    def test_threat_str(self):
        threat = Threat.objects.create(
            name="Test Threat", type=ThreatType.DELIBERATE
        )
        result = str(threat)
        assert "Test Threat" in result
        assert threat.reference in result

    def test_vulnerability_str(self):
        vuln = Vulnerability.objects.create(name="Test Vuln", severity="high")
        result = str(vuln)
        assert "Test Vuln" in result
        assert vuln.reference in result

    def test_treatment_plan_str(self):
        risk = RiskFactory()
        plan = RiskTreatmentPlan.objects.create(
            risk=risk, name="Test Plan", treatment_type="mitigate"
        )
        result = str(plan)
        assert "Test Plan" in result

    def test_acceptance_str(self):
        risk = RiskFactory()
        acceptance = RiskAcceptance.objects.create(
            risk=risk, justification="Justified"
        )
        result = str(acceptance)
        assert acceptance.reference in result

    def test_criteria_str(self):
        criteria = RiskCriteriaFactory(name="Test Criteria")
        result = str(criteria)
        assert "Test Criteria" in result
