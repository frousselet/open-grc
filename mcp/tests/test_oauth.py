"""Tests for OAuth models and token endpoint."""

import json

import pytest
from django.test import TestCase, RequestFactory

from accounts.models import Group, Permission
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from mcp.models import OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_id, _generate_client_secret

pytestmark = pytest.mark.django_db


class TestOAuthApplication:
    def test_create_application(self):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test App", user=user)
        app.set_secret(raw_secret)
        app.save()
        assert app.client_id.startswith("ogrc_")
        assert app.verify_secret(raw_secret)
        assert not app.verify_secret("wrong_secret")

    def test_client_id_generation(self):
        cid = _generate_client_id()
        assert cid.startswith("ogrc_")
        assert len(cid) > 10

    def test_hash_secret_deterministic(self):
        secret = "test_secret_123"
        h1 = OAuthApplication.hash_secret(secret)
        h2 = OAuthApplication.hash_secret(secret)
        assert h1 == h2

    def test_different_secrets_different_hashes(self):
        h1 = OAuthApplication.hash_secret("secret1")
        h2 = OAuthApplication.hash_secret("secret2")
        assert h1 != h2


class TestOAuthAccessToken:
    def test_create_token(self):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, raw_token = OAuthAccessToken.create_token(app)
        assert raw_token
        assert not token_obj.is_expired
        assert token_obj.application == app

    def test_token_hash_lookup(self):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, raw_token = OAuthAccessToken.create_token(app)
        token_hash = OAuthAccessToken.hash_token(raw_token)
        found = OAuthAccessToken.objects.get(token_hash=token_hash)
        assert found.pk == token_obj.pk

    def test_token_never_expires(self):
        """MCP tokens never expire; they remain valid until revoked."""
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        token_obj, _ = OAuthAccessToken.create_token(app)
        assert not token_obj.is_expired


class TestOAuthTokenEndpoint:
    def _setup_user_with_mcp_access(self):
        user = UserFactory()
        perm = PermissionFactory(codename="system.mcp.access")
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(user)
        return user

    def test_token_endpoint_success(self, client):
        user = self._setup_user_with_mcp_access()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": raw_secret,
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert "expires_in" not in data

    def test_token_endpoint_invalid_grant_type(self, client):
        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({"grant_type": "password"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_token_endpoint_invalid_client(self, client):
        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": "fake_id",
                "client_secret": "fake_secret",
            }),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_token_endpoint_wrong_secret(self, client):
        user = self._setup_user_with_mcp_access()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": "wrong_secret",
            }),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_token_endpoint_no_mcp_permission(self, client):
        user = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": raw_secret,
            }),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_token_endpoint_inactive_app(self, client):
        user = self._setup_user_with_mcp_access()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user, is_active=False)
        app.set_secret(raw_secret)
        app.save()

        response = client.post(
            "/api/v1/oauth/token/",
            data=json.dumps({
                "grant_type": "client_credentials",
                "client_id": app.client_id,
                "client_secret": raw_secret,
            }),
            content_type="application/json",
        )
        assert response.status_code == 401


class TestOAuthApplicationManagement:
    def _setup_user_with_oauth_perms(self):
        user = UserFactory()
        perms = [
            PermissionFactory(codename="system.oauth.create"),
            PermissionFactory(codename="system.oauth.read"),
            PermissionFactory(codename="system.oauth.delete"),
        ]
        group = GroupFactory()
        group.permissions.add(*perms)
        group.users.add(user)
        return user

    def test_create_application(self, client):
        user = self._setup_user_with_oauth_perms()
        client.force_login(user)
        response = client.post(
            "/api/v1/oauth/applications/",
            data=json.dumps({"name": "My App"}),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "client_id" in data["data"]
        assert "client_secret" in data["data"]

    def test_list_applications(self, client):
        user = self._setup_user_with_oauth_perms()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        client.force_login(user)
        response = client.get("/api/v1/oauth/applications/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # client_secret should NOT be in list response
        assert "client_secret" not in data["data"][0]

    def test_delete_application(self, client):
        user = self._setup_user_with_oauth_perms()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Test", user=user)
        app.set_secret(raw_secret)
        app.save()

        client.force_login(user)
        response = client.delete(f"/api/v1/oauth/applications/{app.id}/")
        assert response.status_code == 204
        assert not OAuthApplication.objects.filter(pk=app.pk).exists()

    def test_cannot_see_other_users_apps(self, client):
        user1 = self._setup_user_with_oauth_perms()
        user2 = UserFactory()
        raw_secret = _generate_client_secret()
        app = OAuthApplication(name="Other User App", user=user2)
        app.set_secret(raw_secret)
        app.save()

        client.force_login(user1)
        response = client.get("/api/v1/oauth/applications/")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 0

    def test_no_permission_blocked(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.post(
            "/api/v1/oauth/applications/",
            data=json.dumps({"name": "Test"}),
            content_type="application/json",
        )
        assert response.status_code == 403
