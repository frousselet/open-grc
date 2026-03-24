import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from context.tests.factories import (
    IssueFactory,
    ObjectiveFactory,
    ScopeFactory,
    SwotAnalysisFactory,
    SwotItemFactory,
    SwotStrategyFactory,
)

pytestmark = pytest.mark.django_db


def _data(response):
    """Extract response payload, handling the StandardJSONRenderer wrapper."""
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


# ── Tag ViewSet ─────────────────────────────────────────────


class TestTagViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_tags(self):
        from context.models import Tag

        Tag.objects.create(name="tag1")
        response = self.client.get("/api/v1/context/tags/")
        assert response.status_code == 200

    def test_create_tag(self):
        response = self.client.post(
            "/api/v1/context/tags/",
            {"name": "security", "color": "#ff0000"},
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "security"

    def test_retrieve_tag(self):
        from context.models import Tag

        tag = Tag.objects.create(name="test-tag")
        response = self.client.get(f"/api/v1/context/tags/{tag.pk}/")
        assert response.status_code == 200

    def test_update_tag(self):
        from context.models import Tag

        tag = Tag.objects.create(name="old")
        response = self.client.patch(
            f"/api/v1/context/tags/{tag.pk}/",
            {"name": "new"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "new"

    def test_delete_tag(self):
        from context.models import Tag

        tag = Tag.objects.create(name="to-delete")
        response = self.client.delete(f"/api/v1/context/tags/{tag.pk}/")
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/tags/")
        assert response.status_code in (401, 403)


# ── Scope ViewSet ───────────────────────────────────────────


class TestScopeViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_scopes(self):
        ScopeFactory.create_batch(2)
        response = self.client.get("/api/v1/context/scopes/")
        assert response.status_code == 200
        assert len(_data(response)) >= 2

    def test_retrieve_scope(self):
        scope = ScopeFactory(name="My Scope")
        response = self.client.get(f"/api/v1/context/scopes/{scope.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "My Scope"

    def test_create_scope(self):
        response = self.client.post(
            "/api/v1/context/scopes/",
            {"name": "New Scope", "description": "desc"},
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "New Scope"
        assert _data(response)["created_by"] == str(self.user.pk)

    def test_update_scope(self):
        scope = ScopeFactory()
        response = self.client.patch(
            f"/api/v1/context/scopes/{scope.pk}/",
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated"

    def test_delete_scope(self):
        scope = ScopeFactory()
        response = self.client.delete(f"/api/v1/context/scopes/{scope.pk}/")
        assert response.status_code == 204

    def test_archive_action(self):
        scope = ScopeFactory()
        response = self.client.post(
            f"/api/v1/context/scopes/{scope.pk}/archive/"
        )
        assert response.status_code == 200
        assert _data(response)["status"] == "archived"

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/scopes/")
        assert response.status_code in (401, 403)


# ── Site ViewSet ────────────────────────────────────────────


class TestSiteViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_sites(self):
        response = self.client.get("/api/v1/context/sites/")
        assert response.status_code == 200

    def test_create_site(self):
        response = self.client.post(
            "/api/v1/context/sites/",
            {"name": "HQ", "type": "siege"},
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "HQ"

    def test_retrieve_site(self):
        from context.models import Site

        site = Site.objects.create(name="Office A", type="bureau")
        response = self.client.get(f"/api/v1/context/sites/{site.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Office A"

    def test_update_site(self):
        from context.models import Site

        site = Site.objects.create(name="Old", type="autre")
        response = self.client.patch(
            f"/api/v1/context/sites/{site.pk}/",
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "New Name"

    def test_delete_site(self):
        from context.models import Site

        site = Site.objects.create(name="Delete Me", type="autre")
        response = self.client.delete(f"/api/v1/context/sites/{site.pk}/")
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/sites/")
        assert response.status_code in (401, 403)


# ── Issue ViewSet ───────────────────────────────────────────


class TestIssueViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_issues(self):
        IssueFactory.create_batch(2)
        response = self.client.get("/api/v1/context/issues/")
        assert response.status_code == 200

    def test_create_issue(self):
        response = self.client.post(
            "/api/v1/context/issues/",
            {
                "name": "Test Issue",
                "type": "internal",
                "category": "strategic",
                "impact_level": "medium",
            },
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "Test Issue"

    def test_retrieve_issue(self):
        issue = IssueFactory(name="Retrieve Me")
        response = self.client.get(f"/api/v1/context/issues/{issue.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Retrieve Me"

    def test_update_issue(self):
        issue = IssueFactory()
        response = self.client.patch(
            f"/api/v1/context/issues/{issue.pk}/",
            {"name": "Updated Issue"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated Issue"

    def test_delete_issue(self):
        issue = IssueFactory()
        response = self.client.delete(f"/api/v1/context/issues/{issue.pk}/")
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/issues/")
        assert response.status_code in (401, 403)


# ── Stakeholder ViewSet ─────────────────────────────────────


class TestStakeholderViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_stakeholders(self):
        response = self.client.get("/api/v1/context/stakeholders/")
        assert response.status_code == 200

    def test_create_stakeholder(self):
        response = self.client.post(
            "/api/v1/context/stakeholders/",
            {
                "name": "Client Corp",
                "type": "external",
                "category": "customers",
                "influence_level": "high",
                "interest_level": "medium",
            },
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "Client Corp"

    def test_retrieve_stakeholder(self):
        from context.models import Stakeholder

        s = Stakeholder.objects.create(
            name="Partner Inc",
            type="external",
            category="partners",
            influence_level="medium",
            interest_level="high",
        )
        response = self.client.get(f"/api/v1/context/stakeholders/{s.pk}/")
        assert response.status_code == 200

    def test_update_stakeholder(self):
        from context.models import Stakeholder

        s = Stakeholder.objects.create(
            name="Old Name",
            type="internal",
            category="employees",
            influence_level="low",
            interest_level="low",
        )
        response = self.client.patch(
            f"/api/v1/context/stakeholders/{s.pk}/",
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "New Name"

    def test_delete_stakeholder(self):
        from context.models import Stakeholder

        s = Stakeholder.objects.create(
            name="Delete Me",
            type="internal",
            category="employees",
            influence_level="low",
            interest_level="low",
        )
        response = self.client.delete(f"/api/v1/context/stakeholders/{s.pk}/")
        assert response.status_code == 204

    def test_matrix_action(self):
        response = self.client.get("/api/v1/context/stakeholders/matrix/")
        assert response.status_code == 200

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/stakeholders/")
        assert response.status_code in (401, 403)


# ── StakeholderExpectation nested ───────────────────────────


class TestStakeholderExpectationViewSet:
    def setup_method(self):
        from context.models import Stakeholder

        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.stakeholder = Stakeholder.objects.create(
            name="S1",
            type="internal",
            category="employees",
            influence_level="low",
            interest_level="low",
        )

    def test_list_expectations(self):
        response = self.client.get(
            f"/api/v1/context/stakeholders/{self.stakeholder.pk}/expectations/"
        )
        assert response.status_code == 200

    def test_create_expectation(self):
        response = self.client.post(
            f"/api/v1/context/stakeholders/{self.stakeholder.pk}/expectations/",
            {
                "description": "We expect quality",
                "type": "requirement",
                "priority": "high",
                "stakeholder": str(self.stakeholder.pk),
            },
            format="json",
        )
        assert response.status_code == 201

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(
            f"/api/v1/context/stakeholders/{self.stakeholder.pk}/expectations/"
        )
        assert response.status_code in (401, 403)


# ── Objective ViewSet ───────────────────────────────────────


class TestObjectiveViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_objectives(self):
        ObjectiveFactory.create_batch(2)
        response = self.client.get("/api/v1/context/objectives/")
        assert response.status_code == 200

    def test_create_objective(self):
        response = self.client.post(
            "/api/v1/context/objectives/",
            {
                "name": "Reduce risk",
                "category": "confidentiality",
                "type": "security",
                "owner": str(self.user.pk),
                "status": "active",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve_objective(self):
        obj = ObjectiveFactory()
        response = self.client.get(f"/api/v1/context/objectives/{obj.pk}/")
        assert response.status_code == 200

    def test_update_objective(self):
        obj = ObjectiveFactory()
        response = self.client.patch(
            f"/api/v1/context/objectives/{obj.pk}/",
            {"name": "Updated Objective"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated Objective"

    def test_delete_objective(self):
        obj = ObjectiveFactory()
        response = self.client.delete(f"/api/v1/context/objectives/{obj.pk}/")
        assert response.status_code == 204

    def test_children_action(self):
        parent = ObjectiveFactory()
        ObjectiveFactory(parent_objective=parent)
        response = self.client.get(
            f"/api/v1/context/objectives/{parent.pk}/children/"
        )
        assert response.status_code == 200

    def test_tree_action(self):
        ObjectiveFactory()
        response = self.client.get("/api/v1/context/objectives/tree/")
        assert response.status_code == 200

    def test_dashboard_action(self):
        ObjectiveFactory(progress_percentage=50)
        response = self.client.get("/api/v1/context/objectives/dashboard/")
        assert response.status_code == 200
        data = _data(response)
        assert "total" in data
        assert "by_status" in data
        assert "average_progress" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/objectives/")
        assert response.status_code in (401, 403)


# ── SwotAnalysis ViewSet ────────────────────────────────────


class TestSwotAnalysisViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_swot_analyses(self):
        SwotAnalysisFactory.create_batch(2)
        response = self.client.get("/api/v1/context/swot-analyses/")
        assert response.status_code == 200

    def test_create_swot_analysis(self):
        response = self.client.post(
            "/api/v1/context/swot-analyses/",
            {
                "name": "SWOT 2024",
                "description": "Annual SWOT",
                "analysis_date": "2024-01-15",
                "status": "draft",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve_swot_analysis(self):
        sa = SwotAnalysisFactory()
        response = self.client.get(f"/api/v1/context/swot-analyses/{sa.pk}/")
        assert response.status_code == 200

    def test_update_swot_analysis(self):
        sa = SwotAnalysisFactory()
        response = self.client.patch(
            f"/api/v1/context/swot-analyses/{sa.pk}/",
            {"name": "Updated SWOT"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated SWOT"

    def test_delete_swot_analysis(self):
        sa = SwotAnalysisFactory()
        response = self.client.delete(
            f"/api/v1/context/swot-analyses/{sa.pk}/"
        )
        assert response.status_code == 204

    def test_validate_action(self):
        sa = SwotAnalysisFactory()
        response = self.client.post(
            f"/api/v1/context/swot-analyses/{sa.pk}/validate/"
        )
        assert response.status_code == 200
        assert _data(response)["status"] == "validated"

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/swot-analyses/")
        assert response.status_code in (401, 403)


# ── SwotItem nested ViewSet ─────────────────────────────────


class TestSwotItemViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.analysis = SwotAnalysisFactory()

    def test_list_items(self):
        SwotItemFactory(swot_analysis=self.analysis)
        response = self.client.get(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/items/"
        )
        assert response.status_code == 200

    def test_create_item(self):
        response = self.client.post(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/items/",
            {
                "swot_analysis": str(self.analysis.pk),
                "quadrant": "strength",
                "description": "Strong brand",
                "impact_level": "high",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve_item(self):
        item = SwotItemFactory(swot_analysis=self.analysis)
        response = self.client.get(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/items/{item.pk}/"
        )
        assert response.status_code == 200

    def test_update_item(self):
        item = SwotItemFactory(swot_analysis=self.analysis)
        response = self.client.patch(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/items/{item.pk}/",
            {"description": "Updated"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete_item(self):
        item = SwotItemFactory(swot_analysis=self.analysis)
        response = self.client.delete(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/items/{item.pk}/"
        )
        assert response.status_code == 204

    def test_reorder_items(self):
        item1 = SwotItemFactory(swot_analysis=self.analysis, order=0)
        item2 = SwotItemFactory(swot_analysis=self.analysis, order=1)
        response = self.client.patch(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/items/reorder/",
            {
                "items": [
                    {"id": str(item1.pk), "order": 1},
                    {"id": str(item2.pk), "order": 0},
                ]
            },
            format="json",
        )
        assert response.status_code == 200


# ── SwotStrategy nested ViewSet ─────────────────────────────


class TestSwotStrategyViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.analysis = SwotAnalysisFactory()

    def test_list_strategies(self):
        SwotStrategyFactory(swot_analysis=self.analysis)
        response = self.client.get(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/strategies/"
        )
        assert response.status_code == 200

    def test_create_strategy(self):
        response = self.client.post(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/strategies/",
            {
                "swot_analysis": str(self.analysis.pk),
                "quadrant": "so",
                "description": "Leverage strengths",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve_strategy(self):
        strat = SwotStrategyFactory(swot_analysis=self.analysis)
        response = self.client.get(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/strategies/{strat.pk}/"
        )
        assert response.status_code == 200

    def test_update_strategy(self):
        strat = SwotStrategyFactory(swot_analysis=self.analysis)
        response = self.client.patch(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/strategies/{strat.pk}/",
            {"description": "Updated strategy"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete_strategy(self):
        strat = SwotStrategyFactory(swot_analysis=self.analysis)
        response = self.client.delete(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/strategies/{strat.pk}/"
        )
        assert response.status_code == 204

    def test_reorder_strategies(self):
        s1 = SwotStrategyFactory(swot_analysis=self.analysis, order=0)
        s2 = SwotStrategyFactory(swot_analysis=self.analysis, order=1)
        response = self.client.patch(
            f"/api/v1/context/swot-analyses/{self.analysis.pk}/strategies/reorder/",
            {
                "strategies": [
                    {"id": str(s1.pk), "order": 1},
                    {"id": str(s2.pk), "order": 0},
                ]
            },
            format="json",
        )
        assert response.status_code == 200


# ── Role ViewSet ────────────────────────────────────────────


class TestRoleViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_roles(self):
        response = self.client.get("/api/v1/context/roles/")
        assert response.status_code == 200

    def test_create_role(self):
        response = self.client.post(
            "/api/v1/context/roles/",
            {"name": "RSSI", "type": "governance", "is_mandatory": True},
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "RSSI"

    def test_retrieve_role(self):
        from context.models import Role

        role = Role.objects.create(name="DPO", type="governance")
        response = self.client.get(f"/api/v1/context/roles/{role.pk}/")
        assert response.status_code == 200

    def test_update_role(self):
        from context.models import Role

        role = Role.objects.create(name="Old", type="operational")
        response = self.client.patch(
            f"/api/v1/context/roles/{role.pk}/",
            {"name": "New"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete_role(self):
        from context.models import Role

        role = Role.objects.create(name="Delete", type="support")
        response = self.client.delete(f"/api/v1/context/roles/{role.pk}/")
        assert response.status_code == 204

    def test_assign_action(self):
        from context.models import Role

        role = Role.objects.create(name="Assign Test", type="governance")
        target_user = UserFactory()
        response = self.client.post(
            f"/api/v1/context/roles/{role.pk}/assign/",
            {"user_id": str(target_user.pk)},
            format="json",
        )
        assert response.status_code == 200
        assert target_user in role.assigned_users.all()

    def test_assign_missing_user_id(self):
        from context.models import Role

        role = Role.objects.create(name="Assign Fail", type="governance")
        response = self.client.post(
            f"/api/v1/context/roles/{role.pk}/assign/",
            {},
            format="json",
        )
        assert response.status_code == 400

    def test_unassign_action(self):
        from context.models import Role

        role = Role.objects.create(name="Unassign Test", type="governance")
        target_user = UserFactory()
        role.assigned_users.add(target_user)
        response = self.client.delete(
            f"/api/v1/context/roles/{role.pk}/assign/{target_user.pk}/"
        )
        assert response.status_code == 204
        assert target_user not in role.assigned_users.all()

    def test_compliance_check_action(self):
        from context.models import Role

        role = Role.objects.create(
            name="Mandatory No Users", type="governance", is_mandatory=True
        )
        response = self.client.get("/api/v1/context/roles/compliance-check/")
        assert response.status_code == 200
        result = _data(response)
        assert any(a["role_id"] == str(role.pk) for a in result)

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/roles/")
        assert response.status_code in (401, 403)


# ── Responsibility nested ViewSet ───────────────────────────


class TestResponsibilityViewSet:
    def setup_method(self):
        from context.models import Role

        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.role = Role.objects.create(name="Test Role", type="operational")

    def test_list_responsibilities(self):
        response = self.client.get(
            f"/api/v1/context/roles/{self.role.pk}/responsibilities/"
        )
        assert response.status_code == 200

    def test_create_responsibility(self):
        response = self.client.post(
            f"/api/v1/context/roles/{self.role.pk}/responsibilities/",
            {
                "role": str(self.role.pk),
                "description": "Manage security",
                "raci_type": "responsible",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(
            f"/api/v1/context/roles/{self.role.pk}/responsibilities/"
        )
        assert response.status_code in (401, 403)


# ── Activity ViewSet ────────────────────────────────────────


class TestActivityViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_activities(self):
        response = self.client.get("/api/v1/context/activities/")
        assert response.status_code == 200

    def test_create_activity(self):
        response = self.client.post(
            "/api/v1/context/activities/",
            {
                "name": "Security monitoring",
                "type": "core_business",
                "criticality": "high",
                "owner": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve_activity(self):
        from context.models import Activity

        a = Activity.objects.create(name="A1", type="core_business", criticality="medium", owner=self.user)
        response = self.client.get(f"/api/v1/context/activities/{a.pk}/")
        assert response.status_code == 200

    def test_update_activity(self):
        from context.models import Activity

        a = Activity.objects.create(name="Old", type="core_business", criticality="low", owner=self.user)
        response = self.client.patch(
            f"/api/v1/context/activities/{a.pk}/",
            {"name": "New"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete_activity(self):
        from context.models import Activity

        a = Activity.objects.create(name="Del", type="support", criticality="low", owner=self.user)
        response = self.client.delete(f"/api/v1/context/activities/{a.pk}/")
        assert response.status_code == 204

    def test_children_action(self):
        from context.models import Activity

        parent = Activity.objects.create(name="P", type="core_business", criticality="medium", owner=self.user)
        Activity.objects.create(
            name="C", type="core_business", criticality="low", parent_activity=parent, owner=self.user
        )
        response = self.client.get(
            f"/api/v1/context/activities/{parent.pk}/children/"
        )
        assert response.status_code == 200

    def test_tree_action(self):
        response = self.client.get("/api/v1/context/activities/tree/")
        assert response.status_code == 200

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/activities/")
        assert response.status_code in (401, 403)


# ── Indicator ViewSet ───────────────────────────────────────


class TestIndicatorViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_indicators(self):
        response = self.client.get("/api/v1/context/indicators/")
        assert response.status_code == 200

    def test_create_indicator(self):
        response = self.client.post(
            "/api/v1/context/indicators/",
            {
                "name": "Patch rate",
                "indicator_type": "technical",
                "collection_method": "manual",
                "format": "number",
                "review_frequency": "monthly",
                "first_review_date": "2025-01-01",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve_indicator(self):
        from context.models import Indicator

        ind = Indicator.objects.create(
            review_frequency="monthly", first_review_date="2025-01-01",
            name="Ind1",
            indicator_type="technical",
            collection_method="manual",
            format="number",
        )
        response = self.client.get(f"/api/v1/context/indicators/{ind.pk}/")
        assert response.status_code == 200

    def test_update_indicator(self):
        from context.models import Indicator

        ind = Indicator.objects.create(
            review_frequency="monthly", first_review_date="2025-01-01",
            name="Old Ind",
            indicator_type="technical",
            collection_method="manual",
            format="number",
        )
        response = self.client.patch(
            f"/api/v1/context/indicators/{ind.pk}/",
            {"name": "New Ind"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete_indicator(self):
        from context.models import Indicator

        ind = Indicator.objects.create(
            review_frequency="monthly", first_review_date="2025-01-01",
            name="Del Ind",
            indicator_type="technical",
            collection_method="manual",
            format="number",
        )
        response = self.client.delete(f"/api/v1/context/indicators/{ind.pk}/")
        assert response.status_code == 204

    def test_record_measurement(self):
        from context.models import Indicator

        ind = Indicator.objects.create(
            review_frequency="monthly", first_review_date="2025-01-01",
            name="Record Test",
            indicator_type="technical",
            collection_method="manual",
            format="number",
        )
        response = self.client.post(
            f"/api/v1/context/indicators/{ind.pk}/record/",
            {"value": "42.5", "notes": "Q1 measurement", "indicator": str(ind.pk)},
            format="json",
        )
        assert response.status_code == 200

    def test_refresh_non_internal_indicator(self):
        from context.models import Indicator

        ind = Indicator.objects.create(
            review_frequency="monthly", first_review_date="2025-01-01",
            name="Non Internal",
            indicator_type="technical",
            collection_method="manual",
            format="number",
            is_internal=False,
        )
        response = self.client.post(
            f"/api/v1/context/indicators/{ind.pk}/refresh/"
        )
        assert response.status_code == 400

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/context/indicators/")
        assert response.status_code in (401, 403)


# ── IndicatorMeasurement nested ViewSet ─────────────────────


class TestIndicatorMeasurementViewSet:
    def setup_method(self):
        from context.models import Indicator

        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.indicator = Indicator.objects.create(
            review_frequency="monthly", first_review_date="2025-01-01",
            name="Meas Ind",
            indicator_type="technical",
            collection_method="manual",
            format="number",
        )

    def test_list_measurements(self):
        response = self.client.get(
            f"/api/v1/context/indicators/{self.indicator.pk}/measurements/"
        )
        assert response.status_code == 200

    def test_create_measurement(self):
        response = self.client.post(
            f"/api/v1/context/indicators/{self.indicator.pk}/measurements/",
            {"value": "99.5", "indicator": str(self.indicator.pk)},
            format="json",
        )
        assert response.status_code == 201

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(
            f"/api/v1/context/indicators/{self.indicator.pk}/measurements/"
        )
        assert response.status_code in (401, 403)
