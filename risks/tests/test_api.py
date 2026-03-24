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
