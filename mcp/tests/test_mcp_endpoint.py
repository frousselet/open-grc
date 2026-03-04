"""Tests for the MCP Streamable HTTP endpoint."""

import json

import pytest

from accounts.models import Group, Permission
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from mcp.models import OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_secret

pytestmark = pytest.mark.django_db


class TestMcpEndpoint:
    def _create_authenticated_token(self):
        """Create a user with MCP access and return (user, raw_token)."""
        user = UserFactory()
        perm = PermissionFactory(codename="system.mcp.access")
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(user)

        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test MCP", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, raw_token = OAuthAccessToken.create_token(app)
        return user, raw_token

    def test_mcp_requires_auth(self, client):
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_mcp_invalid_token(self, client):
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer invalid_token_here",
        )
        assert response.status_code == 401

    def test_mcp_ping(self, client):
        user, token = self._create_authenticated_token()
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == {}

    def test_mcp_initialize(self, client):
        user, token = self._create_authenticated_token()
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["protocolVersion"] == "2025-03-26"
        assert "tools" in data["result"]["capabilities"]
        assert data["result"]["serverInfo"]["name"] == "Open GRC MCP Server"

    def test_mcp_tools_list(self, client):
        user, token = self._create_authenticated_token()
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        tools = data["result"]["tools"]
        # Should have many tools registered
        assert len(tools) > 50

        # Check for key tools
        tool_names = {t["name"] for t in tools}
        assert "list_scopes" in tool_names
        assert "get_scope" in tool_names
        assert "create_scope" in tool_names
        assert "update_scope" in tool_names
        assert "delete_scope" in tool_names
        assert "approve_scope" in tool_names
        assert "list_frameworks" in tool_names
        assert "list_risks" in tool_names
        assert "list_essential_assets" in tool_names
        assert "list_users" in tool_names
        assert "get_me" in tool_names

    def test_mcp_tools_call_get_me(self, client):
        user, token = self._create_authenticated_token()
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_me",
                    "arguments": {},
                },
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["isError"] is False
        content = json.loads(data["result"]["content"][0]["text"])
        assert content["email"] == user.email

    def test_mcp_no_permission_blocked(self, client):
        # User without system.mcp.access
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="No Access", user=user)
        app.set_secret(raw_secret)
        app.save()

        # Manually create a token (bypassing the permission check in token endpoint)
        token_obj, raw_token = OAuthAccessToken.create_token(app)

        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        assert response.status_code == 403

    def test_mcp_notification_returns_202(self, client):
        user, token = self._create_authenticated_token()
        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "initialized",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 202

    def test_mcp_get_sse_stream(self, client):
        user, token = self._create_authenticated_token()
        response = client.get(
            "/api/v1/mcp",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"

    def test_mcp_delete_session(self, client):
        user, token = self._create_authenticated_token()
        response = client.delete(
            "/api/v1/mcp",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200

        # Token should be revoked after session termination
        response2 = client.post(
            "/api/v1/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response2.status_code == 401

    def test_mcp_delete_session_without_token(self, client):
        """DELETE should succeed even without a Bearer token (e.g. expired)."""
        response = client.delete("/api/v1/mcp")
        assert response.status_code == 200

    def test_mcp_delete_session_with_old_token(self, client):
        """DELETE should succeed even with an old token (tokens never expire)."""
        user, token = self._create_authenticated_token()

        response = client.delete(
            "/api/v1/mcp",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200

    def test_mcp_metadata_endpoint(self, client):
        response = client.get("/api/v1/mcp/.well-known/oauth-protected-resource")
        # This endpoint is public (separate view, no auth required)
        assert response.status_code == 200
        data = response.json()
        assert "resource" in data
        assert "authorization_servers" in data

    def test_superuser_bypasses_mcp_permission(self, client):
        user = UserFactory(is_superuser=True)
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Superuser App", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, raw_token = OAuthAccessToken.create_token(app)

        response = client.post(
            "/api/v1/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        assert response.status_code == 200
