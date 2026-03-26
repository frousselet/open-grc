import uuid

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from compliance.tests.factories import (
    ActionPlanCommentFactory,
    ComplianceActionPlanFactory,
    ComplianceAssessmentFactory,
    FindingFactory,
    FrameworkFactory,
    MappingFactory,
    RequirementFactory,
    SectionFactory,
)

pytestmark = pytest.mark.django_db


def _data(response):
    """Extract response payload, handling the StandardJSONRenderer wrapper."""
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


# ── Framework ViewSet ───────────────────────────────────────


class TestFrameworkViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        FrameworkFactory.create_batch(2)
        response = self.client.get("/api/v1/compliance/frameworks/")
        assert response.status_code == 200

    def test_retrieve(self):
        fw = FrameworkFactory(name="ISO 27001")
        response = self.client.get(f"/api/v1/compliance/frameworks/{fw.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "ISO 27001"

    def test_create(self):
        from context.tests.factories import ScopeFactory

        scope = ScopeFactory()
        response = self.client.post(
            "/api/v1/compliance/frameworks/",
            {
                "name": "New Framework",
                "type": "standard",
                "category": "information_security",
                "owner": str(self.user.pk),
                "scopes": [str(scope.pk)],
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        assert _data(response)["name"] == "New Framework"

    def test_update(self):
        fw = FrameworkFactory()
        response = self.client.patch(
            f"/api/v1/compliance/frameworks/{fw.pk}/",
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated"

    def test_delete(self):
        fw = FrameworkFactory()
        response = self.client.delete(f"/api/v1/compliance/frameworks/{fw.pk}/")
        assert response.status_code == 204

    def test_compliance_summary_action(self):
        fw = FrameworkFactory()
        SectionFactory(framework=fw)
        RequirementFactory(framework=fw, is_applicable=True)
        response = self.client.get(
            f"/api/v1/compliance/frameworks/{fw.pk}/compliance_summary/"
        )
        assert response.status_code == 200
        data = _data(response)
        assert "compliance_level" in data
        assert "sections" in data
        assert "total_requirements" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/compliance/frameworks/")
        assert response.status_code in (401, 403)


# ── Section ViewSet ─────────────────────────────────────────


class TestSectionViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        SectionFactory.create_batch(2)
        response = self.client.get("/api/v1/compliance/sections/")
        assert response.status_code == 200

    def test_retrieve(self):
        section = SectionFactory(name="A.5")
        response = self.client.get(f"/api/v1/compliance/sections/{section.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "A.5"

    def test_create(self):
        fw = FrameworkFactory()
        response = self.client.post(
            "/api/v1/compliance/sections/",
            {
                "framework": str(fw.pk),
                "name": "Section 1",
                "order": 1,
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        section = SectionFactory()
        response = self.client.patch(
            f"/api/v1/compliance/sections/{section.pk}/",
            {"name": "Updated Section"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        section = SectionFactory()
        response = self.client.delete(
            f"/api/v1/compliance/sections/{section.pk}/"
        )
        assert response.status_code == 204

    def test_children_action(self):
        parent = SectionFactory()
        SectionFactory(
            framework=parent.framework, parent_section=parent
        )
        response = self.client.get(
            f"/api/v1/compliance/sections/{parent.pk}/children/"
        )
        assert response.status_code == 200

    def test_tree_action(self):
        fw = FrameworkFactory()
        SectionFactory(framework=fw)
        response = self.client.get(
            f"/api/v1/compliance/sections/tree/?framework_id={fw.pk}"
        )
        assert response.status_code == 200

    def test_tree_missing_framework_id(self):
        response = self.client.get("/api/v1/compliance/sections/tree/")
        assert response.status_code == 400

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/compliance/sections/")
        assert response.status_code in (401, 403)


# ── Requirement ViewSet ─────────────────────────────────────


class TestRequirementViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        RequirementFactory.create_batch(2)
        response = self.client.get("/api/v1/compliance/requirements/")
        assert response.status_code == 200

    def test_retrieve(self):
        req = RequirementFactory(name="Access Control")
        response = self.client.get(f"/api/v1/compliance/requirements/{req.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Access Control"

    def test_create(self):
        fw = FrameworkFactory()
        response = self.client.post(
            "/api/v1/compliance/requirements/",
            {
                "framework": str(fw.pk),
                "requirement_number": "REQ-100",
                "name": "New Req",
                "description": "Test description",
                "type": "mandatory",
                "is_applicable": True,
                "compliance_status": "not_assessed",
                "compliance_level": 0,
                "linked_risks": [],
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_update(self):
        req = RequirementFactory()
        response = self.client.patch(
            f"/api/v1/compliance/requirements/{req.pk}/",
            {"name": "Updated Req"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        req = RequirementFactory()
        response = self.client.delete(
            f"/api/v1/compliance/requirements/{req.pk}/"
        )
        assert response.status_code == 204

    def test_assess_action(self):
        req = RequirementFactory()
        response = self.client.patch(
            f"/api/v1/compliance/requirements/{req.pk}/assess/",
            {
                "compliance_status": "compliant",
                "compliance_level": 100,
                "compliance_evidence": "Evidence provided",
            },
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["compliance_status"] == "compliant"

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/compliance/requirements/")
        assert response.status_code in (401, 403)


# ── ComplianceAssessment ViewSet ────────────────────────────


class TestComplianceAssessmentViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        ComplianceAssessmentFactory()
        response = self.client.get("/api/v1/compliance/assessments/")
        assert response.status_code == 200

    def test_retrieve(self):
        ca = ComplianceAssessmentFactory(name="Audit 2024")
        response = self.client.get(f"/api/v1/compliance/assessments/{ca.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Audit 2024"

    def test_create(self):
        response = self.client.post(
            "/api/v1/compliance/assessments/",
            {
                "name": "New Audit",
                "assessor": str(self.user.pk),
                "status": "draft",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        ca = ComplianceAssessmentFactory()
        response = self.client.patch(
            f"/api/v1/compliance/assessments/{ca.pk}/",
            {"name": "Updated Audit"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        ca = ComplianceAssessmentFactory()
        response = self.client.delete(
            f"/api/v1/compliance/assessments/{ca.pk}/"
        )
        assert response.status_code == 204

    def test_transition_action(self):
        ca = ComplianceAssessmentFactory(status="draft")
        response = self.client.post(
            f"/api/v1/compliance/assessments/{ca.pk}/transition/",
            {"status": "planned"},
            format="json",
        )
        assert response.status_code == 200

    def test_transition_missing_status(self):
        ca = ComplianceAssessmentFactory(status="draft")
        response = self.client.post(
            f"/api/v1/compliance/assessments/{ca.pk}/transition/",
            {},
            format="json",
        )
        assert response.status_code == 400

    def test_transition_invalid_status(self):
        ca = ComplianceAssessmentFactory(status="draft")
        response = self.client.post(
            f"/api/v1/compliance/assessments/{ca.pk}/transition/",
            {"status": "closed"},
            format="json",
        )
        assert response.status_code == 400

    def test_summary_action(self):
        ca = ComplianceAssessmentFactory()
        response = self.client.get(
            f"/api/v1/compliance/assessments/{ca.pk}/summary/"
        )
        assert response.status_code == 200
        data = _data(response)
        assert "overall_compliance_level" in data
        assert "total_requirements" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/compliance/assessments/")
        assert response.status_code in (401, 403)


# ── AssessmentResult nested ViewSet ─────────────────────────


class TestAssessmentResultViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.assessment = ComplianceAssessmentFactory()

    def test_list(self):
        response = self.client.get(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/results/"
        )
        assert response.status_code == 200

    def test_create(self):
        req = RequirementFactory()
        response = self.client.post(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/results/",
            {
                "assessment": str(self.assessment.pk),
                "requirement": str(req.pk),
                "compliance_status": "compliant",
                "compliance_level": 100,
                "assessed_by": str(self.user.pk),
                "assessed_at": "2025-01-15T10:00:00Z",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/results/"
        )
        assert response.status_code in (401, 403)


# ── Finding nested ViewSet ──────────────────────────────────


class TestFindingViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.assessment = ComplianceAssessmentFactory()

    def test_list(self):
        FindingFactory(assessment=self.assessment)
        response = self.client.get(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/findings/"
        )
        assert response.status_code == 200

    def test_create(self):
        response = self.client.post(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/findings/",
            {
                "assessment": str(self.assessment.pk),
                "finding_type": "major_nc",
                "description": "Missing firewall policy",
                "assessor": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_retrieve(self):
        f = FindingFactory(assessment=self.assessment)
        response = self.client.get(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/findings/{f.pk}/"
        )
        assert response.status_code == 200

    def test_update(self):
        f = FindingFactory(assessment=self.assessment)
        response = self.client.patch(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/findings/{f.pk}/",
            {"description": "Updated finding"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        f = FindingFactory(assessment=self.assessment)
        response = self.client.delete(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/findings/{f.pk}/"
        )
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(
            f"/api/v1/compliance/assessments/{self.assessment.pk}/findings/"
        )
        assert response.status_code in (401, 403)


# ── RequirementMapping ViewSet ──────────────────────────────


class TestRequirementMappingViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        MappingFactory()
        response = self.client.get("/api/v1/compliance/mappings/")
        assert response.status_code == 200

    def test_retrieve(self):
        m = MappingFactory()
        response = self.client.get(f"/api/v1/compliance/mappings/{m.pk}/")
        assert response.status_code == 200

    def test_create_equivalent_mapping(self):
        req1 = RequirementFactory()
        req2 = RequirementFactory()
        response = self.client.post(
            "/api/v1/compliance/mappings/",
            {
                "source_requirement": str(req1.pk),
                "target_requirement": str(req2.pk),
                "mapping_type": "equivalent",
            },
            format="json",
        )
        assert response.status_code == 201
        from compliance.models import RequirementMapping

        assert RequirementMapping.objects.filter(
            source_requirement=req2,
            target_requirement=req1,
            mapping_type="equivalent",
        ).exists()

    def test_create_includes_mapping(self):
        req1 = RequirementFactory()
        req2 = RequirementFactory()
        response = self.client.post(
            "/api/v1/compliance/mappings/",
            {
                "source_requirement": str(req1.pk),
                "target_requirement": str(req2.pk),
                "mapping_type": "includes",
            },
            format="json",
        )
        assert response.status_code == 201
        from compliance.models import RequirementMapping

        assert RequirementMapping.objects.filter(
            source_requirement=req2,
            target_requirement=req1,
            mapping_type="included_by",
        ).exists()

    def test_update(self):
        m = MappingFactory()
        response = self.client.patch(
            f"/api/v1/compliance/mappings/{m.pk}/",
            {"description": "Updated mapping"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        m = MappingFactory()
        response = self.client.delete(f"/api/v1/compliance/mappings/{m.pk}/")
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/compliance/mappings/")
        assert response.status_code in (401, 403)


# ── ComplianceActionPlan ViewSet ────────────────────────────


class TestComplianceActionPlanViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        ComplianceActionPlanFactory.create_batch(2)
        response = self.client.get("/api/v1/compliance/action-plans/")
        assert response.status_code == 200

    def test_retrieve(self):
        ap = ComplianceActionPlanFactory(name="Fix Firewall")
        response = self.client.get(f"/api/v1/compliance/action-plans/{ap.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Fix Firewall"

    def test_create(self):
        response = self.client.post(
            "/api/v1/compliance/action-plans/",
            {
                "name": "Implement MFA",
                "gap_description": "No MFA in place",
                "remediation_plan": "Deploy MFA for all users",
                "priority": "high",
                "owner": str(self.user.pk),
                "target_date": "2025-12-31",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        ap = ComplianceActionPlanFactory()
        response = self.client.patch(
            f"/api/v1/compliance/action-plans/{ap.pk}/",
            {"name": "Updated Plan"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        ap = ComplianceActionPlanFactory()
        response = self.client.delete(
            f"/api/v1/compliance/action-plans/{ap.pk}/"
        )
        assert response.status_code == 204

    def test_transition_action(self):
        ap = ComplianceActionPlanFactory(status="new")
        response = self.client.post(
            f"/api/v1/compliance/action-plans/{ap.pk}/transition/",
            {"status": "to_define", "comment": "Starting work"},
            format="json",
        )
        assert response.status_code == 200

    def test_transition_invalid(self):
        ap = ComplianceActionPlanFactory(status="new")
        response = self.client.post(
            f"/api/v1/compliance/action-plans/{ap.pk}/transition/",
            {"status": "closed"},
            format="json",
        )
        assert response.status_code == 400

    def test_transitions_history(self):
        ap = ComplianceActionPlanFactory()
        response = self.client.get(
            f"/api/v1/compliance/action-plans/{ap.pk}/transitions/"
        )
        assert response.status_code == 200

    def test_kanban_action(self):
        ComplianceActionPlanFactory()
        response = self.client.get("/api/v1/compliance/action-plans/kanban/")
        assert response.status_code == 200
        data = _data(response)
        assert "new" in data

    def test_dashboard_action(self):
        ComplianceActionPlanFactory()
        response = self.client.get("/api/v1/compliance/action-plans/dashboard/")
        assert response.status_code == 200
        data = _data(response)
        assert "total" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert "overdue" in data

    def test_comments_get(self):
        ap = ComplianceActionPlanFactory()
        ActionPlanCommentFactory(action_plan=ap)
        response = self.client.get(
            f"/api/v1/compliance/action-plans/{ap.pk}/comments/"
        )
        assert response.status_code == 200

    def test_comments_post(self):
        ap = ComplianceActionPlanFactory()
        response = self.client.post(
            f"/api/v1/compliance/action-plans/{ap.pk}/comments/",
            {"content": "This needs review"},
            format="json",
        )
        assert response.status_code == 201

    def test_comments_post_reply(self):
        ap = ComplianceActionPlanFactory()
        parent = ActionPlanCommentFactory(action_plan=ap)
        response = self.client.post(
            f"/api/v1/compliance/action-plans/{ap.pk}/comments/",
            {"content": "Reply to parent", "parent": str(parent.pk)},
            format="json",
        )
        assert response.status_code == 201

    def test_comments_post_invalid_parent(self):
        ap = ComplianceActionPlanFactory()
        response = self.client.post(
            f"/api/v1/compliance/action-plans/{ap.pk}/comments/",
            {"content": "Bad parent", "parent": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == 404

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/compliance/action-plans/")
        assert response.status_code in (401, 403)


# ── Batch create endpoints ─────────────────────────────────


class TestBatchCreateRequirements:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/compliance/requirements/batch/"

    def test_batch_create_success(self):
        fw = FrameworkFactory()
        section = SectionFactory(framework=fw)
        items = [
            {
                "framework": str(fw.pk),
                "section": str(section.pk),
                "requirement_number": f"A.5.{i}",
                "name": f"Requirement {i}",
                "description": f"Description {i}",
                "type": "mandatory",
                "linked_risks": [],
            }
            for i in range(5)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["total"] == 5
        assert data["created"] == 5, f"Results: {data['results']}"
        assert data["errors"] == 0
        assert data["status"] == "completed"

    def test_batch_create_partial_error(self):
        fw = FrameworkFactory()
        items = [
            {
                "framework": str(fw.pk),
                "requirement_number": "A.5.1",
                "name": "Valid requirement",
                "description": "Desc",
                "type": "mandatory",
                "linked_risks": [],
            },
            {
                # Missing framework
                "requirement_number": "A.5.2",
                "name": "Invalid requirement",
                "description": "Desc",
                "type": "mandatory",
                "linked_risks": [],
            },
            {
                "framework": str(fw.pk),
                "requirement_number": "A.5.3",
                "name": "Another valid",
                "description": "Desc",
                "type": "mandatory",
                "linked_risks": [],
            },
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 2
        assert data["errors"] == 1
        assert data["status"] == "completed_with_errors"

    def test_batch_create_exceeds_limit(self):
        items = [{"name": f"R{i}"} for i in range(101)]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 400

    def test_batch_create_empty_list(self):
        response = self.client.post(self.url, {"items": []}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["total"] == 0
        assert data["created"] == 0

    def test_batch_create_permission_denied(self):
        non_admin = UserFactory(is_superuser=False)
        client = APIClient()
        client.force_authenticate(user=non_admin)
        fw = FrameworkFactory()
        items = [
            {
                "framework": str(fw.pk),
                "requirement_number": "A.5.1",
                "name": "Req",
                "description": "Desc",
                "type": "mandatory",
                "linked_risks": [],
            }
        ]
        response = client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 403


class TestBatchCreateSections:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/compliance/sections/batch/"

    def test_batch_create_success(self):
        fw = FrameworkFactory()
        items = [
            {
                "framework": str(fw.pk),
                "name": f"Section {i}",
                "order": i,
            }
            for i in range(3)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 3
