import pytest
from rest_framework.test import APIClient

from accounts.models import AccessLog, CompanySettings, Group, Permission
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory

pytestmark = pytest.mark.django_db


def _data(response):
    """Extract response payload, handling the StandardJSONRenderer wrapper.

    The renderer wraps responses in {"status": "success", "data": ...}
    UNLESS the serializer output already contains a "status" key
    (e.g. model status field), in which case it's returned as-is.
    """
    body = response.json()
    # Wrapped response from renderer or pagination
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    # Wrapped error
    if isinstance(body, dict) and body.get("status") == "error" and "error" in body:
        return body["error"]
    # Raw serializer output (model has 'status' field so renderer didn't wrap)
    return body


# ── Auth endpoints ──────────────────────────────────────────


class TestLoginAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(email="login@example.com", password="Str0ng!Pass99")

    def test_login_success(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "Str0ng!Pass99"},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "wrongpass"},
            format="json",
        )
        assert response.status_code == 401
        assert response.json()["status"] == "error"
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_login_nonexistent_user(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "nonexistent@example.com", "password": "whatever"},
            format="json",
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    def test_login_locked_account(self):
        from datetime import timedelta

        from django.utils import timezone

        self.user.locked_until = timezone.now() + timedelta(minutes=15)
        self.user.save()
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "Str0ng!Pass99"},
            format="json",
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"

    def test_login_missing_fields(self):
        response = self.client.post(
            "/api/v1/auth/login/", {}, format="json"
        )
        assert response.status_code == 400


class TestLogoutAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()

    def test_logout_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/auth/logout/", format="json")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_logout_with_refresh_token(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh_token": "invalid-token"},
            format="json",
        )
        assert response.status_code == 200

    def test_logout_unauthenticated(self):
        response = self.client.post("/api/v1/auth/logout/", format="json")
        assert response.status_code in (401, 403)


class TestMeAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(first_name="Jane", last_name="Doe")
        self.client.force_authenticate(user=self.user)

    def test_get_me(self):
        response = self.client.get("/api/v1/auth/me/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == self.user.email
        assert data["first_name"] == "Jane"

    def test_patch_me(self):
        response = self.client.patch(
            "/api/v1/auth/me/",
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["first_name"] == "Updated"

    def test_me_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/auth/me/")
        assert response.status_code in (401, 403)


class TestTokenRefreshAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(email="refresh@example.com", password="Str0ng!Pass99")

    def test_refresh_missing_token(self):
        response = self.client.post(
            "/api/v1/auth/refresh/", {}, format="json"
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "MISSING_TOKEN"

    def test_refresh_invalid_token(self):
        response = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh_token": "invalid"},
            format="json",
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_TOKEN"

    def test_refresh_valid_token(self):
        login_resp = self.client.post(
            "/api/v1/auth/login/",
            {"email": "refresh@example.com", "password": "Str0ng!Pass99"},
            format="json",
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]
        response = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh_token": refresh_token},
            format="json",
        )
        assert response.status_code == 200
        assert "access_token" in response.json()["data"]
        assert "refresh_token" in response.json()["data"]


# ── User ViewSet ────────────────────────────────────────────


class TestUserViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_users(self):
        UserFactory.create_batch(3)
        response = self.client.get("/api/v1/users/")
        assert response.status_code == 200
        assert len(_data(response)) >= 3

    def test_retrieve_user(self):
        target = UserFactory(first_name="Alice")
        response = self.client.get(f"/api/v1/users/{target.pk}/")
        assert response.status_code == 200
        assert _data(response)["first_name"] == "Alice"

    def test_create_user(self):
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "Str0ng!Pass99",
            },
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["email"] == "new@example.com"

    def test_update_user(self):
        target = UserFactory()
        response = self.client.patch(
            f"/api/v1/users/{target.pk}/",
            {"first_name": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["first_name"] == "Updated"

    def test_delete_user(self):
        target = UserFactory()
        response = self.client.delete(f"/api/v1/users/{target.pk}/")
        assert response.status_code == 204

    def test_user_groups_action(self):
        target = UserFactory()
        group = GroupFactory()
        group.users.add(target)
        response = self.client.get(f"/api/v1/users/{target.pk}/groups/")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]) == 1

    def test_user_permissions_action(self):
        target = UserFactory()
        response = self.client.get(f"/api/v1/users/{target.pk}/permissions/")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_unauthenticated_access(self):
        client = APIClient()
        response = client.get("/api/v1/users/")
        assert response.status_code in (401, 403)


# ── Group ViewSet ───────────────────────────────────────────


class TestGroupViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_groups(self):
        GroupFactory.create_batch(2)
        response = self.client.get("/api/v1/groups/")
        assert response.status_code == 200

    def test_retrieve_group(self):
        group = GroupFactory(name="TestGroup")
        response = self.client.get(f"/api/v1/groups/{group.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "TestGroup"

    def test_create_group(self):
        response = self.client.post(
            "/api/v1/groups/",
            {"name": "New Group"},
            format="json",
        )
        assert response.status_code == 201
        assert _data(response)["name"] == "New Group"

    def test_update_group(self):
        group = GroupFactory()
        response = self.client.patch(
            f"/api/v1/groups/{group.pk}/",
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated"

    def test_delete_group(self):
        group = GroupFactory()
        response = self.client.delete(f"/api/v1/groups/{group.pk}/")
        assert response.status_code == 204

    def test_delete_system_group_rejected(self):
        group = GroupFactory(is_system=True)
        response = self.client.delete(f"/api/v1/groups/{group.pk}/")
        assert response.status_code == 400

    def test_delete_group_with_users_rejected(self):
        group = GroupFactory()
        group.users.add(UserFactory())
        response = self.client.delete(f"/api/v1/groups/{group.pk}/")
        assert response.status_code == 400

    def test_group_permissions_get(self):
        group = GroupFactory()
        perm = PermissionFactory()
        group.permissions.add(perm)
        response = self.client.get(f"/api/v1/groups/{group.pk}/permissions/")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]) == 1

    def test_group_permissions_post(self):
        group = GroupFactory()
        perm = PermissionFactory(codename="system.test.read")
        response = self.client.post(
            f"/api/v1/groups/{group.pk}/permissions/",
            {"permissions": [perm.codename]},
            format="json",
        )
        assert response.status_code == 200
        assert perm in group.permissions.all()

    def test_group_users_get(self):
        group = GroupFactory()
        u = UserFactory()
        group.users.add(u)
        response = self.client.get(f"/api/v1/groups/{group.pk}/users/")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]) == 1

    def test_group_users_post(self):
        group = GroupFactory()
        u = UserFactory()
        response = self.client.post(
            f"/api/v1/groups/{group.pk}/users/",
            {"users": [str(u.pk)]},
            format="json",
        )
        assert response.status_code == 200
        assert u in group.users.all()

    def test_unauthenticated_access(self):
        client = APIClient()
        response = client.get("/api/v1/groups/")
        assert response.status_code in (401, 403)


# ── Permission ViewSet ──────────────────────────────────────


class TestPermissionViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_permissions(self):
        PermissionFactory.create_batch(3)
        response = self.client.get("/api/v1/permissions/")
        assert response.status_code == 200

    def test_retrieve_permission(self):
        perm = PermissionFactory()
        response = self.client.get(f"/api/v1/permissions/{perm.pk}/")
        assert response.status_code == 200
        assert _data(response)["codename"] == perm.codename

    def test_by_module_action(self):
        PermissionFactory(codename="context.scope.read")
        response = self.client.get("/api/v1/permissions/by_module/")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_unauthenticated_access(self):
        client = APIClient()
        response = client.get("/api/v1/permissions/")
        assert response.status_code in (401, 403)


# ── AccessLog ViewSet ───────────────────────────────────────


class TestAccessLogViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list_access_logs(self):
        AccessLog.objects.create(
            user=self.user,
            email_attempted=self.user.email,
            event_type="login_success",
            ip_address="127.0.0.1",
        )
        response = self.client.get("/api/v1/access-logs/")
        assert response.status_code == 200
        assert len(_data(response)) >= 1

    def test_retrieve_access_log(self):
        log = AccessLog.objects.create(
            user=self.user,
            email_attempted=self.user.email,
            event_type="login_success",
            ip_address="127.0.0.1",
        )
        response = self.client.get(f"/api/v1/access-logs/{log.pk}/")
        assert response.status_code == 200

    def test_unauthenticated_access(self):
        client = APIClient()
        response = client.get("/api/v1/access-logs/")
        assert response.status_code in (401, 403)


# ── CompanySettings API ─────────────────────────────────────


class TestCompanySettingsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_get_settings(self):
        response = self.client.get("/api/v1/company-settings/")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_patch_settings(self):
        response = self.client.patch(
            "/api/v1/company-settings/",
            {"name": "ACME Corp"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "ACME Corp"

    def test_unauthenticated_access(self):
        client = APIClient()
        response = client.get("/api/v1/company-settings/")
        assert response.status_code in (401, 403)


# ── ModulePermission (RBAC) ────────────────────────────────


class TestModulePermission:
    """Test that non-superuser access is governed by RBAC permissions."""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=False)
        self.client.force_authenticate(user=self.user)

    def test_no_permission_denied(self):
        response = self.client.get("/api/v1/users/")
        assert response.status_code == 403

    def test_with_permission_allowed(self):
        group = GroupFactory()
        perm = PermissionFactory(codename="system.users.read")
        group.permissions.add(perm)
        group.users.add(self.user)
        response = self.client.get("/api/v1/users/")
        assert response.status_code == 200

    def test_create_without_permission_denied(self):
        group = GroupFactory()
        perm = PermissionFactory(codename="system.users.read")
        group.permissions.add(perm)
        group.users.add(self.user)
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "new2@example.com",
                "first_name": "X",
                "last_name": "Y",
                "password": "Str0ng!Pass99",
            },
            format="json",
        )
        assert response.status_code == 403


# ── ScopeFilterAPIMixin ─────────────────────────────────────


class TestScopeFilterAPIMixin:
    """Test scope-based filtering for non-superusers."""

    def setup_method(self):
        from context.tests.factories import ScopeFactory

        self.client = APIClient()
        self.user = UserFactory(is_superuser=False)
        self.client.force_authenticate(user=self.user)
        group = GroupFactory()
        perm = PermissionFactory(codename="context.scope.read")
        group.permissions.add(perm)
        group.users.add(self.user)
        self.scope1 = ScopeFactory(name="Scope A")
        self.scope2 = ScopeFactory(name="Scope B")
        group.allowed_scopes.add(self.scope1)

    def test_scope_filtering(self):
        response = self.client.get("/api/v1/context/scopes/")
        assert response.status_code == 200
        ids = [r["id"] for r in _data(response)]
        assert str(self.scope1.pk) in ids
        assert str(self.scope2.pk) not in ids


# ── ApprovableAPIMixin ──────────────────────────────────────


class TestApprovableAPIMixin:
    def setup_method(self):
        from context.tests.factories import ScopeFactory

        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.scope = ScopeFactory(name="Approvable Scope")

    def test_approve_action(self):
        response = self.client.post(
            f"/api/v1/context/scopes/{self.scope.pk}/approve/"
        )
        assert response.status_code == 200
        assert _data(response)["is_approved"] is True

    def test_reject_action(self):
        self.scope.is_approved = True
        self.scope.save()
        response = self.client.post(
            f"/api/v1/context/scopes/{self.scope.pk}/reject/"
        )
        assert response.status_code == 200
        assert _data(response)["is_approved"] is False

    def test_approve_without_permission(self):
        user = UserFactory(is_superuser=False)
        client = APIClient()
        client.force_authenticate(user=user)
        group = GroupFactory()
        for action in ["read", "update"]:
            perm = PermissionFactory(codename=f"context.scope.{action}")
            group.permissions.add(perm)
        group.users.add(user)
        response = client.post(
            f"/api/v1/context/scopes/{self.scope.pk}/approve/"
        )
        assert response.status_code == 403


# ── HistoryAPIMixin ─────────────────────────────────────────


class TestHistoryAPIMixin:
    def setup_method(self):
        from context.tests.factories import ScopeFactory

        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.scope = ScopeFactory(name="History Scope")

    def test_history_action(self):
        self.scope.name = "Updated Scope"
        self.scope.save()
        response = self.client.get(
            f"/api/v1/context/scopes/{self.scope.pk}/history/"
        )
        assert response.status_code == 200
        # history returns a list wrapped in data
        history_data = _data(response)
        assert isinstance(history_data, list)
        assert len(history_data) >= 1
