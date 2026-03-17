"""Tests for MCP action plan transition tools."""

import json

import pytest

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from compliance.constants import ActionPlanStatus
from compliance.tests.factories import ComplianceActionPlanFactory
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


def _make_server_and_user(permissions=None, superuser=False):
    srv = McpServer()
    register_all_tools(srv)
    user = UserFactory(is_superuser=superuser)
    if permissions:
        group = GroupFactory()
        for codename in permissions:
            perm = PermissionFactory(codename=codename)
            group.permissions.add(perm)
        group.users.add(user)
    return srv, user


def _call_tool(srv, user, tool_name, arguments):
    result = srv.handle_request(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }), user)
    return result


class TestActionPlanTransitionsHistory:
    """Test the action_plan_transitions MCP tool (history endpoint)."""

    def test_transitions_history_empty(self):
        """Test getting transitions for an action plan with no transitions."""
        srv, user = _make_server_and_user(superuser=True)
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        result = _call_tool(srv, user, "action_plan_transitions", {
            "action_plan_id": str(ap.pk),
        })
        # Should NOT be a JSON-RPC error
        assert "error" not in result, f"Got JSON-RPC error: {result}"
        content = json.loads(result["result"]["content"][0]["text"])
        assert isinstance(content, list)
        assert len(content) == 0

    def test_transitions_history_after_transition(self):
        """Test getting transitions after performing some transitions."""
        srv, user = _make_server_and_user(superuser=True)
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        ap.transition_to(ActionPlanStatus.TO_DEFINE, user)
        ap.transition_to(ActionPlanStatus.TO_VALIDATE, user)

        result = _call_tool(srv, user, "action_plan_transitions", {
            "action_plan_id": str(ap.pk),
        })
        assert "error" not in result, f"Got JSON-RPC error: {result}"
        content = json.loads(result["result"]["content"][0]["text"])
        assert isinstance(content, list)
        assert len(content) == 2
        # Most recent first
        assert content[0]["from_status"] == "to_define"
        assert content[0]["to_status"] == "to_validate"
        assert content[1]["from_status"] == "new"
        assert content[1]["to_status"] == "to_define"

    def test_transitions_history_not_found(self):
        """Test getting transitions for a non-existent action plan."""
        srv, user = _make_server_and_user(superuser=True)
        result = _call_tool(srv, user, "action_plan_transitions", {
            "action_plan_id": "00000000-0000-0000-0000-000000000000",
        })
        content = json.loads(result["result"]["content"][0]["text"])
        assert "error" in content

    def test_transitions_history_permission_denied(self):
        """Test permission check on transitions history."""
        srv, user = _make_server_and_user()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        result = _call_tool(srv, user, "action_plan_transitions", {
            "action_plan_id": str(ap.pk),
        })
        content = json.loads(result["result"]["content"][0]["text"])
        assert "error" in content
        assert "Permission denied" in content["error"]


class TestActionPlanTransitionPerform:
    """Test the action_plan_transition MCP tool (perform transition)."""

    def test_transition_forward(self):
        srv, user = _make_server_and_user(superuser=True)
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        result = _call_tool(srv, user, "action_plan_transition", {
            "action_plan_id": str(ap.pk),
            "target_status": "to_define",
        })
        assert "error" not in result, f"Got JSON-RPC error: {result}"
        content = json.loads(result["result"]["content"][0]["text"])
        assert content["status"] == "to_define"

    def test_transition_validate_requires_permission(self):
        """Transition to_validate -> to_implement requires compliance.action_plan.validate."""
        srv, user = _make_server_and_user(["compliance.action_plan.read"])
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        result = _call_tool(srv, user, "action_plan_transition", {
            "action_plan_id": str(ap.pk),
            "target_status": "to_implement",
        })
        content = json.loads(result["result"]["content"][0]["text"])
        assert "error" in content
        assert "compliance.action_plan.validate" in content["error"]

    def test_transition_cancel_requires_permission(self):
        """Cancellation requires compliance.action_plan.cancel."""
        srv, user = _make_server_and_user(["compliance.action_plan.read"])
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        result = _call_tool(srv, user, "action_plan_transition", {
            "action_plan_id": str(ap.pk),
            "target_status": "cancelled",
        })
        content = json.loads(result["result"]["content"][0]["text"])
        assert "error" in content
        assert "compliance.action_plan.cancel" in content["error"]


class TestActionPlanAllowedTransitions:
    """Test the action_plan_allowed_transitions MCP tool."""

    def test_allowed_transitions_new(self):
        srv, user = _make_server_and_user(superuser=True)
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        result = _call_tool(srv, user, "action_plan_allowed_transitions", {
            "action_plan_id": str(ap.pk),
        })
        assert "error" not in result, f"Got JSON-RPC error: {result}"
        content = json.loads(result["result"]["content"][0]["text"])
        assert content["current_status"] == "new"
        targets = [t["target_status"] for t in content["allowed_transitions"]]
        assert "to_define" in targets
        assert "cancelled" in targets
