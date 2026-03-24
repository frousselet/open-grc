import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

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
