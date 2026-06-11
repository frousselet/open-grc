"""Tests for the lifecycle transition surfaces: DRF endpoint and MCP tools (phase 5).

Exercised through the Scope entity (default workflow, `context.scope` permissions).
"""

import json

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


def _data(response):
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


def _user_with_perms(*codenames):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        module, feature, action = codename.split(".")
        perm = PermissionFactory(
            codename=codename, module=module, feature=feature, action=action,
        )
        group.permissions.add(perm)
    group.users.add(user)
    return user


class TestTransitionEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.superuser = UserFactory(is_superuser=True)

    def _url(self, scope):
        return f"/api/v1/context/scopes/{scope.pk}/transition/"

    def test_get_lists_allowed_transitions(self):
        self.client.force_authenticate(self.superuser)
        scope = ScopeFactory()
        response = self.client.get(self._url(scope))
        assert response.status_code == 200
        payload = _data(response)
        assert payload["workflow_state"] == "draft"
        assert [t["target"] for t in payload["allowed_transitions"]] == ["pending"]

    def test_get_filters_by_caller_permissions(self):
        user = _user_with_perms("context.scope.read", "context.scope.update")
        self.client.force_authenticate(user)
        scope = ScopeFactory()
        scope.transition_to("pending")
        response = self.client.get(self._url(scope))
        targets = {t["target"] for t in _data(response)["allowed_transitions"]}
        # Send back to draft (update) yes; Validate (approve) filtered out.
        assert targets == {"draft"}

    def test_post_submits_draft(self):
        self.client.force_authenticate(self.superuser)
        scope = ScopeFactory()
        response = self.client.post(
            self._url(scope), {"target_state": "pending"}, format="json",
        )
        assert response.status_code == 200
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_post_validate_requires_approve_permission(self):
        user = _user_with_perms("context.scope.read", "context.scope.update")
        self.client.force_authenticate(user)
        scope = ScopeFactory()
        scope.transition_to("pending")
        response = self.client.post(
            self._url(scope), {"target_state": "validated"}, format="json",
        )
        assert response.status_code == 403
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_post_validate_stamps_approval(self):
        self.client.force_authenticate(self.superuser)
        scope = ScopeFactory()
        scope.transition_to("pending")
        response = self.client.post(
            self._url(scope), {"target_state": "validated"}, format="json",
        )
        assert response.status_code == 200
        scope.refresh_from_db()
        assert scope.workflow_state == "validated"
        assert scope.is_approved is True
        assert scope.approved_by == self.superuser

    def test_post_illegal_transition_is_400(self):
        self.client.force_authenticate(self.superuser)
        scope = ScopeFactory()
        response = self.client.post(
            self._url(scope), {"target_state": "validated"}, format="json",
        )
        assert response.status_code == 400
        scope.refresh_from_db()
        assert scope.workflow_state == "draft"

    def test_post_missing_target_is_400(self):
        self.client.force_authenticate(self.superuser)
        scope = ScopeFactory()
        response = self.client.post(self._url(scope), {}, format="json")
        assert response.status_code == 400

    def test_list_filter_by_workflow_state(self):
        self.client.force_authenticate(self.superuser)
        ScopeFactory()  # draft
        validated = ScopeFactory(is_approved=True)
        response = self.client.get("/api/v1/context/scopes/?workflow_state=validated")
        payload = _data(response)
        items = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        assert [item["id"] for item in items] == [str(validated.pk)]

    def test_approve_action_rejects_terminal_state(self):
        self.client.force_authenticate(self.superuser)
        scope = ScopeFactory(is_approved=True)
        scope.transition_to("archived")
        response = self.client.post(f"/api/v1/context/scopes/{scope.pk}/approve/")
        assert response.status_code == 400
        scope.refresh_from_db()
        assert scope.workflow_state == "archived"
        assert scope.is_approved is False


class TestTransitionMCPTools:
    def setup_method(self):
        from mcp.server import McpServer
        from mcp.tools import register_all_tools

        self.srv = McpServer()
        register_all_tools(self.srv)
        self.superuser = UserFactory(is_superuser=True)

    def _call(self, user, name, arguments=None):
        result = self.srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }), user)
        return json.loads(result["result"]["content"][0]["text"])

    def test_generic_tools_are_registered(self):
        assert "transition_scope" in self.srv._tools
        assert "scope_allowed_transitions" in self.srv._tools
        assert "transition_risk" in self.srv._tools
        # Bespoke status-machine tools are not clobbered.
        assert "transition_management_review" in self.srv._tools
        assert "action_plan_allowed_transitions" in self.srv._tools

    def test_transition_happy_path(self):
        scope = ScopeFactory()
        result = self._call(
            self.superuser, "transition_scope",
            {"id": str(scope.pk), "target_state": "pending"},
        )
        assert result["workflow_state"] == "pending"
        assert result["previous_state"] == "draft"
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_allowed_transitions(self):
        scope = ScopeFactory()
        scope.transition_to("pending")
        result = self._call(
            self.superuser, "scope_allowed_transitions", {"id": str(scope.pk)},
        )
        assert result["workflow_state"] == "pending"
        assert {t["target"] for t in result["allowed_transitions"]} == {"draft", "validated"}

    def test_illegal_transition_errors(self):
        scope = ScopeFactory()
        result = self._call(
            self.superuser, "transition_scope",
            {"id": str(scope.pk), "target_state": "archived"},
        )
        assert "error" in result

    def test_validate_requires_approve_permission(self):
        user = _user_with_perms("context.scope.read", "context.scope.update")
        scope = ScopeFactory()
        scope.transition_to("pending")
        result = self._call(
            user, "transition_scope",
            {"id": str(scope.pk), "target_state": "validated"},
        )
        assert "error" in result
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_validate_with_permission_stamps(self):
        scope = ScopeFactory()
        scope.transition_to("pending")
        result = self._call(
            self.superuser, "transition_scope",
            {"id": str(scope.pk), "target_state": "validated"},
        )
        assert result["workflow_state"] == "validated"
        scope.refresh_from_db()
        assert scope.is_approved is True
        assert scope.approved_by == self.superuser

    def test_approve_alias_rejects_terminal_state(self):
        scope = ScopeFactory(is_approved=True)
        scope.transition_to("archived")
        result = self._call(self.superuser, "approve_scope", {"id": str(scope.pk)})
        assert "error" in result
        scope.refresh_from_db()
        assert scope.workflow_state == "archived"

    def test_approve_alias_still_validates_draft(self):
        scope = ScopeFactory()
        result = self._call(self.superuser, "approve_scope", {"id": str(scope.pk)})
        assert result.get("approved") is True
        assert result.get("workflow_state") == "validated"
        scope.refresh_from_db()
        assert scope.workflow_state == "validated"
