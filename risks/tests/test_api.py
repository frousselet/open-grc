import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from risks.tests.factories import (
    RiskAssessmentFactory,
    RiskCriteriaFactory,
    RiskFactory,
)

pytestmark = pytest.mark.django_db


def _data(response):
    """Extract response payload, handling the StandardJSONRenderer wrapper."""
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


# ── RiskCriteria ViewSet ────────────────────────────────────


class TestRiskCriteriaViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        RiskCriteriaFactory.create_batch(2)
        response = self.client.get("/api/v1/risks/criteria/")
        assert response.status_code == 200

    def test_retrieve(self):
        rc = RiskCriteriaFactory(name="Standard Criteria")
        response = self.client.get(f"/api/v1/risks/criteria/{rc.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Standard Criteria"

    def test_create(self):
        response = self.client.post(
            "/api/v1/risks/criteria/",
            {"name": "New Criteria", "status": "active"},
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "New Criteria"

    def test_update(self):
        rc = RiskCriteriaFactory()
        response = self.client.patch(
            f"/api/v1/risks/criteria/{rc.pk}/",
            {"name": "Updated Criteria"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated Criteria"

    def test_delete(self):
        rc = RiskCriteriaFactory()
        response = self.client.delete(f"/api/v1/risks/criteria/{rc.pk}/")
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/criteria/")
        assert response.status_code in (401, 403)


# ── RiskAssessment ViewSet ──────────────────────────────────


class TestRiskAssessmentViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        RiskAssessmentFactory.create_batch(2)
        response = self.client.get("/api/v1/risks/assessments/")
        assert response.status_code == 200

    def test_retrieve(self):
        ra = RiskAssessmentFactory(name="RA 2024")
        response = self.client.get(f"/api/v1/risks/assessments/{ra.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "RA 2024"

    def test_create(self):
        response = self.client.post(
            "/api/v1/risks/assessments/",
            {
                "name": "New Assessment",
                "methodology": "iso27005",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_update(self):
        ra = RiskAssessmentFactory()
        response = self.client.patch(
            f"/api/v1/risks/assessments/{ra.pk}/",
            {"name": "Updated Assessment"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        ra = RiskAssessmentFactory()
        response = self.client.delete(f"/api/v1/risks/assessments/{ra.pk}/")
        assert response.status_code == 204

    def test_approve(self):
        ra = RiskAssessmentFactory()
        response = self.client.post(f"/api/v1/risks/assessments/{ra.pk}/approve/")
        assert response.status_code == 200, response.json()
        ra.refresh_from_db()
        assert ra.is_approved is True
        assert ra.approved_by == self.user

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/assessments/")
        assert response.status_code in (401, 403)


# ── Risk ViewSet ────────────────────────────────────────────


class TestRiskViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        RiskFactory.create_batch(2)
        response = self.client.get("/api/v1/risks/risks/")
        assert response.status_code == 200

    def test_retrieve(self):
        risk = RiskFactory(name="Data Breach")
        response = self.client.get(f"/api/v1/risks/risks/{risk.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Data Breach"

    def test_create(self):
        ra = RiskAssessmentFactory()
        response = self.client.post(
            "/api/v1/risks/risks/",
            {
                "assessment": str(ra.pk),
                "name": "New Risk",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        risk = RiskFactory()
        response = self.client.patch(
            f"/api/v1/risks/risks/{risk.pk}/",
            {"name": "Updated Risk"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        risk = RiskFactory()
        response = self.client.delete(f"/api/v1/risks/risks/{risk.pk}/")
        assert response.status_code == 204

    def test_approve(self):
        risk = RiskFactory()
        response = self.client.post(f"/api/v1/risks/risks/{risk.pk}/approve/")
        assert response.status_code == 200, response.json()
        risk.refresh_from_db()
        assert risk.is_approved is True

    def test_filter_by_treatment_decision(self):
        RiskFactory(name="A1", treatment_decision="avoid")
        RiskFactory(name="M1", treatment_decision="mitigate")
        response = self.client.get(
            "/api/v1/risks/risks/", {"treatment_decision": "avoid"},
        )
        body = _data(response)
        items = body["results"] if isinstance(body, dict) else body
        names = [r["name"] for r in items]
        assert "A1" in names
        assert "M1" not in names

    def test_filter_by_linked_requirement(self):
        from compliance.tests.factories import (
            FrameworkFactory, RequirementFactory,
        )
        fw = FrameworkFactory()
        req = RequirementFactory(framework=fw, requirement_number="A.5.42")
        r_with = RiskFactory(name="LinkedReqRisk")
        RiskFactory(name="NoReqRisk")
        r_with.linked_requirements.add(req)
        response = self.client.get(
            "/api/v1/risks/risks/", {"linked_requirement": str(req.pk)},
        )
        body = _data(response)
        items = body["results"] if isinstance(body, dict) else body
        names = [r["name"] for r in items]
        assert "LinkedReqRisk" in names
        assert "NoReqRisk" not in names

    def test_filter_by_essential_asset(self):
        from assets.tests.factories import EssentialAssetFactory
        asset = EssentialAssetFactory()
        r_with = RiskFactory(name="AssetRisk")
        RiskFactory(name="NoAssetRisk")
        r_with.affected_essential_assets.add(asset)
        response = self.client.get(
            "/api/v1/risks/risks/", {"essential_asset": str(asset.pk)},
        )
        body = _data(response)
        items = body["results"] if isinstance(body, dict) else body
        names = [r["name"] for r in items]
        assert "AssetRisk" in names
        assert "NoAssetRisk" not in names

    def test_filter_by_threat(self):
        from risks.models import ISO27005Risk
        from risks.tests.factories import ThreatFactory, VulnerabilityFactory
        threat = ThreatFactory()
        vuln = VulnerabilityFactory()
        assessment = RiskAssessmentFactory()
        r_with = RiskFactory(assessment=assessment, name="ThreatRisk")
        RiskFactory(assessment=assessment, name="NoThreatRisk")
        ISO27005Risk.objects.create(
            assessment=assessment, threat=threat, vulnerability=vuln, risk=r_with,
        )
        response = self.client.get(
            "/api/v1/risks/risks/", {"threat": str(threat.pk)},
        )
        body = _data(response)
        items = body["results"] if isinstance(body, dict) else body
        names = [r["name"] for r in items]
        assert "ThreatRisk" in names
        assert "NoThreatRisk" not in names

    def test_filter_by_date_after(self):
        from datetime import timedelta
        from django.utils import timezone as tz
        from risks.models import Risk
        old = RiskFactory(name="OldOne")
        recent = RiskFactory(name="RecentOne")
        Risk.objects.filter(pk=old.pk).update(
            created_at=tz.now() - timedelta(days=30),
        )
        Risk.objects.filter(pk=recent.pk).update(
            created_at=tz.now() - timedelta(days=1),
        )
        cutoff = (tz.now() - timedelta(days=15)).date().isoformat()
        response = self.client.get(
            "/api/v1/risks/risks/", {"date_after": cutoff},
        )
        body = _data(response)
        items = body["results"] if isinstance(body, dict) else body
        names = [r["name"] for r in items]
        assert "RecentOne" in names
        assert "OldOne" not in names

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/risks/")
        assert response.status_code in (401, 403)


# ── RiskTreatmentPlan ViewSet ───────────────────────────────


class TestRiskTreatmentPlanViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get("/api/v1/risks/treatment-plans/")
        assert response.status_code == 200

    def test_create(self):
        risk = RiskFactory()
        response = self.client.post(
            "/api/v1/risks/treatment-plans/",
            {
                "risk": str(risk.pk),
                "name": "Mitigation Plan",
                "treatment_type": "mitigate",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve(self):
        from risks.models import RiskTreatmentPlan

        risk = RiskFactory()
        rtp = RiskTreatmentPlan.objects.create(
            risk=risk, name="Plan A", treatment_type="mitigate"
        )
        response = self.client.get(f"/api/v1/risks/treatment-plans/{rtp.pk}/")
        assert response.status_code == 200

    def test_update(self):
        from risks.models import RiskTreatmentPlan

        risk = RiskFactory()
        rtp = RiskTreatmentPlan.objects.create(
            risk=risk, name="Old Plan", treatment_type="mitigate"
        )
        response = self.client.patch(
            f"/api/v1/risks/treatment-plans/{rtp.pk}/",
            {"name": "New Plan"},
            format="json",
        )
        assert response.status_code == 200

    def test_link_action_plans_via_api(self):
        from compliance.tests.factories import ComplianceActionPlanFactory
        from risks.models import RiskTreatmentPlan

        risk = RiskFactory()
        rtp = RiskTreatmentPlan.objects.create(
            risk=risk, name="Plan", treatment_type="mitigate"
        )
        ap1 = ComplianceActionPlanFactory()
        ap2 = ComplianceActionPlanFactory()
        response = self.client.patch(
            f"/api/v1/risks/treatment-plans/{rtp.pk}/",
            {"related_action_plans": [str(ap1.pk), str(ap2.pk)]},
            format="json",
        )
        assert response.status_code == 200, response.json()
        rtp.refresh_from_db()
        assert set(rtp.related_action_plans.values_list("pk", flat=True)) == {ap1.pk, ap2.pk}

    def test_delete(self):
        from risks.models import RiskTreatmentPlan

        risk = RiskFactory()
        rtp = RiskTreatmentPlan.objects.create(
            risk=risk, name="Del", treatment_type="transfer"
        )
        response = self.client.delete(
            f"/api/v1/risks/treatment-plans/{rtp.pk}/"
        )
        assert response.status_code == 204

    def test_approve(self):
        from risks.models import RiskTreatmentPlan

        risk = RiskFactory()
        rtp = RiskTreatmentPlan.objects.create(
            risk=risk, name="Approvable Plan", treatment_type="mitigate"
        )
        response = self.client.post(
            f"/api/v1/risks/treatment-plans/{rtp.pk}/approve/",
        )
        assert response.status_code == 200, response.json()
        rtp.refresh_from_db()
        assert rtp.is_approved is True

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/treatment-plans/")
        assert response.status_code in (401, 403)


# ── RiskAcceptance ViewSet ──────────────────────────────────


class TestRiskAcceptanceViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get("/api/v1/risks/acceptances/")
        assert response.status_code == 200

    def test_create(self):
        risk = RiskFactory()
        response = self.client.post(
            "/api/v1/risks/acceptances/",
            {
                "risk": str(risk.pk),
                "accepted_by": str(self.user.pk),
                "justification": "Low impact risk",
                "status": "active",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_retrieve(self):
        from risks.models import RiskAcceptance

        risk = RiskFactory()
        ra = RiskAcceptance.objects.create(
            risk=risk,
            accepted_by=self.user,
            justification="Acceptable risk",
            status="active",
        )
        response = self.client.get(f"/api/v1/risks/acceptances/{ra.pk}/")
        assert response.status_code == 200

    def test_update(self):
        from risks.models import RiskAcceptance

        risk = RiskFactory()
        ra = RiskAcceptance.objects.create(
            risk=risk,
            accepted_by=self.user,
            justification="Old",
            status="active",
        )
        response = self.client.patch(
            f"/api/v1/risks/acceptances/{ra.pk}/",
            {"justification": "Updated justification"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        from risks.models import RiskAcceptance

        risk = RiskFactory()
        ra = RiskAcceptance.objects.create(
            risk=risk,
            accepted_by=self.user,
            justification="Del",
            status="active",
        )
        response = self.client.delete(f"/api/v1/risks/acceptances/{ra.pk}/")
        assert response.status_code == 204

    def test_approve(self):
        from risks.models import RiskAcceptance

        risk = RiskFactory()
        ra = RiskAcceptance.objects.create(
            risk=risk, accepted_by=self.user,
            justification="Approve me", status="active",
        )
        assert ra.is_approved is False
        response = self.client.post(f"/api/v1/risks/acceptances/{ra.pk}/approve/")
        assert response.status_code == 200, response.json()
        ra.refresh_from_db()
        assert ra.is_approved is True
        assert ra.approved_by == self.user
        assert ra.approved_at is not None

    def test_reject(self):
        from django.utils import timezone

        from risks.models import RiskAcceptance

        risk = RiskFactory()
        ra = RiskAcceptance.objects.create(
            risk=risk, accepted_by=self.user,
            justification="Reject me", status="active",
            is_approved=True, approved_by=self.user, approved_at=timezone.now(),
        )
        response = self.client.post(f"/api/v1/risks/acceptances/{ra.pk}/reject/")
        assert response.status_code == 200, response.json()
        ra.refresh_from_db()
        assert ra.is_approved is False
        assert ra.approved_by is None

    def test_update_resets_approval(self):
        from risks.models import RiskAcceptance

        risk = RiskFactory()
        ra = RiskAcceptance.objects.create(
            risk=risk, accepted_by=self.user,
            justification="Original", status="active",
            is_approved=True, approved_by=self.user,
        )
        response = self.client.patch(
            f"/api/v1/risks/acceptances/{ra.pk}/",
            {"justification": "Reworded"},
            format="json",
        )
        assert response.status_code == 200
        ra.refresh_from_db()
        assert ra.is_approved is False
        assert ra.approved_by is None

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/acceptances/")
        assert response.status_code in (401, 403)


# ── Threat ViewSet ──────────────────────────────────────────


class TestThreatViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get("/api/v1/risks/threats/")
        assert response.status_code == 200

    def test_create(self):
        response = self.client.post(
            "/api/v1/risks/threats/",
            {
                "name": "Phishing",
                "type": "deliberate",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve(self):
        from risks.models import Threat

        t = Threat.objects.create(name="Malware", type="deliberate")
        response = self.client.get(f"/api/v1/risks/threats/{t.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Malware"

    def test_update(self):
        from risks.models import Threat

        t = Threat.objects.create(name="Old", type="deliberate")
        response = self.client.patch(
            f"/api/v1/risks/threats/{t.pk}/",
            {"name": "Updated Threat"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        from risks.models import Threat

        t = Threat.objects.create(name="Del", type="accidental")
        response = self.client.delete(f"/api/v1/risks/threats/{t.pk}/")
        assert response.status_code == 204

    def test_approve(self):
        from risks.models import Threat
        t = Threat.objects.create(name="Approvable", type="deliberate")
        response = self.client.post(f"/api/v1/risks/threats/{t.pk}/approve/")
        assert response.status_code == 200, response.json()
        t.refresh_from_db()
        assert t.is_approved is True
        assert t.approved_by == self.user

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/threats/")
        assert response.status_code in (401, 403)


# ── Vulnerability ViewSet ───────────────────────────────────


class TestVulnerabilityViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get("/api/v1/risks/vulnerabilities/")
        assert response.status_code == 200

    def test_create(self):
        response = self.client.post(
            "/api/v1/risks/vulnerabilities/",
            {
                "name": "Weak Password Policy",
                "category": "weak_authentication",
                "severity": "high",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve(self):
        from risks.models import Vulnerability

        v = Vulnerability.objects.create(
            name="Missing Patch", category="missing_patch", severity="medium"
        )
        response = self.client.get(f"/api/v1/risks/vulnerabilities/{v.pk}/")
        assert response.status_code == 200

    def test_update(self):
        from risks.models import Vulnerability

        v = Vulnerability.objects.create(
            name="Old", category="design_flaw", severity="low"
        )
        response = self.client.patch(
            f"/api/v1/risks/vulnerabilities/{v.pk}/",
            {"name": "Updated Vuln"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        from risks.models import Vulnerability

        v = Vulnerability.objects.create(
            name="Del", category="coding_error", severity="medium"
        )
        response = self.client.delete(f"/api/v1/risks/vulnerabilities/{v.pk}/")
        assert response.status_code == 204

    def test_approve(self):
        from risks.models import Vulnerability
        v = Vulnerability.objects.create(name="Approvable", severity="high")
        response = self.client.post(
            f"/api/v1/risks/vulnerabilities/{v.pk}/approve/",
        )
        assert response.status_code == 200, response.json()
        v.refresh_from_db()
        assert v.is_approved is True

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/vulnerabilities/")
        assert response.status_code in (401, 403)


# ── ISO27005Risk ViewSet ────────────────────────────────────


class TestISO27005RiskViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get("/api/v1/risks/iso27005-risks/")
        assert response.status_code == 200

    def test_create(self):
        from risks.models import Threat, Vulnerability

        ra = RiskAssessmentFactory()
        threat = Threat.objects.create(name="T1", type="deliberate")
        vuln = Vulnerability.objects.create(
            name="V1", category="design_flaw", severity="medium"
        )
        response = self.client.post(
            "/api/v1/risks/iso27005-risks/",
            {
                "assessment": str(ra.pk),
                "threat": str(threat.pk),
                "vulnerability": str(vuln.pk),
                "threat_likelihood": 3,
                "vulnerability_exposure": 2,
                "impact_confidentiality": 3,
                "impact_integrity": 2,
                "impact_availability": 1,
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve(self):
        from risks.models import ISO27005Risk, Threat, Vulnerability

        ra = RiskAssessmentFactory()
        threat = Threat.objects.create(name="T2", type="accidental")
        vuln = Vulnerability.objects.create(
            name="V2", category="missing_patch", severity="high"
        )
        iso_risk = ISO27005Risk.objects.create(
            assessment=ra,
            threat=threat,
            vulnerability=vuln,
            threat_likelihood=2,
            vulnerability_exposure=3,
            impact_confidentiality=2,
            impact_integrity=1,
            impact_availability=1,
        )
        response = self.client.get(
            f"/api/v1/risks/iso27005-risks/{iso_risk.pk}/"
        )
        assert response.status_code == 200

    def test_update(self):
        from risks.models import ISO27005Risk, Threat, Vulnerability

        ra = RiskAssessmentFactory()
        threat = Threat.objects.create(name="T3", type="environmental")
        vuln = Vulnerability.objects.create(
            name="V3", category="configuration_weakness", severity="low"
        )
        iso_risk = ISO27005Risk.objects.create(
            assessment=ra,
            threat=threat,
            vulnerability=vuln,
            threat_likelihood=1,
            vulnerability_exposure=1,
            impact_confidentiality=1,
            impact_integrity=1,
            impact_availability=1,
        )
        response = self.client.patch(
            f"/api/v1/risks/iso27005-risks/{iso_risk.pk}/",
            {"threat_likelihood": 4},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        from risks.models import ISO27005Risk, Threat, Vulnerability

        ra = RiskAssessmentFactory()
        threat = Threat.objects.create(name="T4", type="other")
        vuln = Vulnerability.objects.create(
            name="V4", category="coding_error", severity="medium"
        )
        iso_risk = ISO27005Risk.objects.create(
            assessment=ra,
            threat=threat,
            vulnerability=vuln,
            threat_likelihood=2,
            vulnerability_exposure=2,
            impact_confidentiality=2,
            impact_integrity=2,
            impact_availability=2,
        )
        response = self.client.delete(
            f"/api/v1/risks/iso27005-risks/{iso_risk.pk}/"
        )
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/risks/iso27005-risks/")
        assert response.status_code in (401, 403)

    def test_approve(self):
        from risks.models import ISO27005Risk, Threat, Vulnerability

        ra = RiskAssessmentFactory()
        threat = Threat.objects.create(name="T-approve", type="deliberate")
        vuln = Vulnerability.objects.create(
            name="V-approve", category="design_flaw", severity="medium",
        )
        iso = ISO27005Risk.objects.create(
            assessment=ra, threat=threat, vulnerability=vuln,
        )
        response = self.client.post(
            f"/api/v1/risks/iso27005-risks/{iso.pk}/approve/",
        )
        assert response.status_code == 200, response.json()
        iso.refresh_from_db()
        assert iso.is_approved is True
        assert iso.approved_by == self.user


# ── Batch create endpoints ─────────────────────────────────


class TestBatchCreateThreats:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/risks/threats/batch/"

    def test_batch_create_success(self):
        items = [
            {"name": f"Threat {i}", "type": "deliberate"}
            for i in range(5)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["total"] == 5
        assert data["created"] == 5
        assert data["errors"] == 0
        assert data["status"] == "completed"

    def test_batch_create_partial_error(self):
        items = [
            {"name": "Valid Threat", "type": "deliberate"},
            {"type": "deliberate"},  # Missing name
            {"name": "Another Valid", "type": "environmental"},
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 2
        assert data["errors"] == 1


class TestBatchCreateVulnerabilities:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/risks/vulnerabilities/batch/"

    def test_batch_create_success(self):
        items = [
            {
                "name": f"Vulnerability {i}",
                "category": "design_flaw",
                "affected_assets": [],
                "affected_asset_types": [],
            }
            for i in range(3)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 3, f"Results: {data['results']}"
        assert data["errors"] == 0


class TestBatchCreateRisks:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/risks/risks/batch/"

    def test_batch_create_success(self):
        assessment = RiskAssessmentFactory()
        items = [
            {
                "assessment": str(assessment.pk),
                "name": f"Risk {i}",
            }
            for i in range(3)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 3
        assert data["errors"] == 0


# ── New polish-pass endpoints: TreatmentAction / ScaleLevel / RiskLevel ──


class TestTreatmentActionViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def _make_plan(self):
        from risks.models import RiskTreatmentPlan
        return RiskTreatmentPlan.objects.create(
            risk=RiskFactory(), name="Plan", treatment_type="mitigate",
        )

    def test_list(self):
        from risks.tests.factories import TreatmentActionFactory
        plan = self._make_plan()
        TreatmentActionFactory(treatment_plan=plan)
        response = self.client.get("/api/v1/risks/treatment-actions/")
        assert response.status_code == 200

    def test_create(self):
        plan = self._make_plan()
        response = self.client.post(
            "/api/v1/risks/treatment-actions/",
            {
                "treatment_plan": str(plan.pk),
                "description": "Patch the server",
                "status": "planned",
                "order": 1,
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_filter_by_treatment_plan(self):
        from risks.models import TreatmentAction
        from risks.tests.factories import TreatmentActionFactory
        p1 = self._make_plan()
        p2 = self._make_plan()
        a1 = TreatmentActionFactory(treatment_plan=p1, description="A1")
        TreatmentActionFactory(treatment_plan=p2, description="A2")
        response = self.client.get(
            "/api/v1/risks/treatment-actions/",
            {"treatment_plan": str(p1.pk)},
        )
        body = response.json()
        items = body.get("data", body)
        items = items["results"] if isinstance(items, dict) and "results" in items else items
        descriptions = [a["description"] for a in items]
        assert "A1" in descriptions
        assert "A2" not in descriptions


class TestScaleLevelViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        from risks.tests.factories import RiskCriteriaFactory, ScaleLevelFactory
        criteria = RiskCriteriaFactory()
        ScaleLevelFactory(criteria=criteria, scale_type="likelihood", level=1, name="VL")
        response = self.client.get("/api/v1/risks/scale-levels/")
        assert response.status_code == 200

    def test_create_forbidden(self):
        # Read-only viewset returns 405 on POST.
        response = self.client.post(
            "/api/v1/risks/scale-levels/", {}, format="json",
        )
        assert response.status_code == 405


class TestRiskLevelViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        from risks.tests.factories import RiskCriteriaFactory, RiskLevelFactory
        criteria = RiskCriteriaFactory()
        RiskLevelFactory(criteria=criteria, level=1, name="Low")
        response = self.client.get("/api/v1/risks/risk-levels/")
        assert response.status_code == 200

    def test_create_forbidden(self):
        response = self.client.post(
            "/api/v1/risks/risk-levels/", {}, format="json",
        )
        assert response.status_code == 405


# ── Batch create for the remaining writable viewsets ──────


class TestBatchCreateTreatmentPlans:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_batch_create_success(self):
        risk = RiskFactory()
        items = [
            {
                "risk": str(risk.pk),
                "name": f"Plan {i}",
                "treatment_type": "mitigate",
            }
            for i in range(3)
        ]
        response = self.client.post(
            "/api/v1/risks/treatment-plans/batch/",
            {"items": items}, format="json",
        )
        assert response.status_code == 200
        data = response.json().get("data", response.json())
        assert data["created"] == 3


class TestBatchCreateAcceptances:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_batch_create_success(self):
        risk = RiskFactory()
        items = [
            {
                "risk": str(risk.pk),
                "justification": f"Acceptable {i}",
                "status": "active",
            }
            for i in range(3)
        ]
        response = self.client.post(
            "/api/v1/risks/acceptances/batch/",
            {"items": items}, format="json",
        )
        assert response.status_code == 200
        data = response.json().get("data", response.json())
        assert data["created"] == 3


class TestBatchCreateISO27005Risks:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_batch_create_success(self):
        from risks.tests.factories import ThreatFactory, VulnerabilityFactory
        assessment = RiskAssessmentFactory()
        items = [
            {
                "assessment": str(assessment.pk),
                "threat": str(ThreatFactory().pk),
                "vulnerability": str(VulnerabilityFactory().pk),
            }
            for _ in range(3)
        ]
        response = self.client.post(
            "/api/v1/risks/iso27005-risks/batch/",
            {"items": items}, format="json",
        )
        assert response.status_code == 200
        data = response.json().get("data", response.json())
        assert data["created"] == 3
