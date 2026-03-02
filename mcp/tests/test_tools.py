"""Tests for MCP tools (permission checking, CRUD operations)."""

import json

import pytest

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from mcp.models import OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_secret
from mcp.server import McpServer
from mcp.tools import register_all_tools

pytestmark = pytest.mark.django_db


class TestToolPermissions:
    def _make_server_and_user(self, permissions=None):
        srv = McpServer()
        register_all_tools(srv)
        user = UserFactory()
        if permissions:
            group = GroupFactory()
            for codename in permissions:
                perm = PermissionFactory(codename=codename)
                group.permissions.add(perm)
            group.users.add(user)
        return srv, user

    def test_list_scopes_without_permission(self):
        srv, user = self._make_server_and_user()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "list_scopes", "arguments": {}},
        }), user)
        content = json.loads(result["result"]["content"][0]["text"])
        assert "error" in content
        assert "Permission denied" in content["error"]

    def test_list_scopes_with_permission(self):
        srv, user = self._make_server_and_user(["context.scope.read"])
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "list_scopes", "arguments": {}},
        }), user)
        content = json.loads(result["result"]["content"][0]["text"])
        assert "total" in content
        assert "items" in content

    def test_get_me_no_special_permission(self):
        """get_me should work for any authenticated user."""
        srv, user = self._make_server_and_user()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_me", "arguments": {}},
        }), user)
        content = json.loads(result["result"]["content"][0]["text"])
        assert content["email"] == user.email

    def test_superuser_bypasses_permissions(self):
        srv = McpServer()
        register_all_tools(srv)
        user = UserFactory(is_superuser=True)
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "list_scopes", "arguments": {}},
        }), user)
        content = json.loads(result["result"]["content"][0]["text"])
        assert "total" in content


class TestToolsRegistered:
    def test_all_modules_have_tools(self):
        srv = McpServer()
        register_all_tools(srv)
        tool_names = set(srv._tools.keys())

        # Context module tools
        assert "list_scopes" in tool_names
        assert "list_issues" in tool_names
        assert "list_stakeholders" in tool_names
        assert "list_objectives" in tool_names
        assert "list_swot_analysiss" in tool_names
        assert "list_roles" in tool_names
        assert "list_activitys" in tool_names
        assert "list_sites" in tool_names

        # Assets module tools
        assert "list_essential_assets" in tool_names
        assert "list_support_assets" in tool_names
        assert "list_asset_dependencys" in tool_names
        assert "list_asset_groups" in tool_names
        assert "list_suppliers" in tool_names

        # Compliance module tools
        assert "list_frameworks" in tool_names
        assert "list_sections" in tool_names
        assert "list_requirements" in tool_names
        assert "list_compliance_assessments" in tool_names
        assert "list_action_plans" in tool_names
        assert "get_framework_compliance_summary" in tool_names

        # Risks module tools
        assert "list_risk_assessments" in tool_names
        assert "list_risks" in tool_names
        assert "list_risk_treatment_plans" in tool_names
        assert "list_threats" in tool_names
        assert "list_vulnerabilitys" in tool_names

        # Accounts module tools
        assert "list_users" in tool_names
        assert "get_user" in tool_names
        assert "get_me" in tool_names
        assert "list_groups" in tool_names
        assert "list_permissions" in tool_names
        assert "list_access_logs" in tool_names

    def test_tools_have_schemas(self):
        srv = McpServer()
        register_all_tools(srv)
        for name, tool_def in srv._tools.items():
            assert "inputSchema" in tool_def, f"Tool {name} missing inputSchema"
            assert "description" in tool_def, f"Tool {name} missing description"
            assert "handler" in tool_def, f"Tool {name} missing handler"
            assert callable(tool_def["handler"]), f"Tool {name} handler not callable"
