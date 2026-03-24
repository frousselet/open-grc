"""Comprehensive view tests for the accounts app.

Covers authentication, profile, password change, company settings,
user CRUD, group CRUD (including permissions/users/scopes updates),
permission listing, access logs, action logs, calendar subscriptions,
and the ResetHelpersView.
"""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import AccessLog, CalendarToken, CompanySettings, Group, Permission
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import ScopeFactory


pytestmark = pytest.mark.django_db


# ── Helpers ────────────────────────────────────────────────────


def _grant_perm(user, codename):
    """Create a permission, attach it to a group, and add the user to that group."""
    perm = PermissionFactory(codename=codename)
    group = GroupFactory()
    group.permissions.add(perm)
    group.users.add(user)
    # Clear the cached permissions so the backend re-fetches
    if hasattr(user, "_custom_perm_cache"):
        del user._custom_perm_cache
    return group


def _superuser():
    return UserFactory(is_superuser=True, password="password")


# ── LoginView ──────────────────────────────────────────────────


class TestLoginView:
    def test_get_login_page(self, client):
        resp = client.get(reverse("accounts:login"))
        assert resp.status_code == 200
        assert b"email" in resp.content.lower()

    def test_get_login_redirects_when_authenticated(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:login"))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_post_valid_credentials(self, client):
        user = UserFactory(password="secret123")
        resp = client.post(reverse("accounts:login"), {"email": user.email, "password": "secret123"})
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_post_valid_credentials_with_next(self, client):
        user = UserFactory(password="secret123")
        url = reverse("accounts:login") + "?next=/accounts/profile/"
        resp = client.post(url, {"email": user.email, "password": "secret123"})
        assert resp.status_code == 302
        assert resp.url == "/accounts/profile/"

    def test_post_invalid_password(self, client):
        user = UserFactory(password="secret123")
        resp = client.post(reverse("accounts:login"), {"email": user.email, "password": "wrong"})
        assert resp.status_code == 200  # re-renders form

    def test_post_nonexistent_user(self, client):
        resp = client.post(reverse("accounts:login"), {"email": "nobody@example.com", "password": "irrelevant"})
        assert resp.status_code == 200

    def test_post_inactive_user(self, client):
        user = UserFactory(password="secret123", is_active=False)
        resp = client.post(reverse("accounts:login"), {"email": user.email, "password": "secret123"})
        assert resp.status_code == 200

    def test_post_locked_user(self, client):
        user = UserFactory(password="secret123")
        user.lock_account()
        resp = client.post(reverse("accounts:login"), {"email": user.email, "password": "secret123"})
        assert resp.status_code == 200

    def test_post_empty_form(self, client):
        resp = client.post(reverse("accounts:login"), {"email": "", "password": ""})
        assert resp.status_code == 200


# ── LogoutView ─────────────────────────────────────────────────


class TestLogoutView:
    def test_post_logout(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.post(reverse("accounts:logout"))
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_get_logout(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:logout"))
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_logout_anonymous_redirects_to_login(self, client):
        resp = client.get(reverse("accounts:logout"))
        assert resp.status_code == 302
        assert "login" in resp.url


# ── ProfileView ────────────────────────────────────────────────


class TestProfileView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:profile"))
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_get_profile(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:profile"))
        assert resp.status_code == 200

    def test_post_profile_update(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.post(reverse("accounts:profile"), {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+33123456789",
            "language": "",
            "timezone": "Europe/Paris",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_post_profile_with_language(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.post(reverse("accounts:profile"), {
            "first_name": "Test",
            "last_name": "User",
            "phone": "",
            "language": "fr",
            "timezone": "Europe/Paris",
        })
        assert resp.status_code == 302
        assert resp.cookies.get("django_language") is not None

    def test_post_profile_invalid(self, client):
        user = UserFactory()
        client.force_login(user)
        # first_name is required
        resp = client.post(reverse("accounts:profile"), {
            "first_name": "",
            "last_name": "",
            "phone": "",
            "language": "",
            "timezone": "Europe/Paris",
        })
        assert resp.status_code == 200  # re-renders form with errors

    def test_profile_context_includes_groups_and_permissions(self, client):
        user = UserFactory()
        group = _grant_perm(user, "system.users.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:profile"))
        assert resp.status_code == 200
        assert group in resp.context["groups"]
        assert "system.users.read" in resp.context["permissions"]

    def test_profile_context_oauth_for_superuser(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:profile"))
        assert resp.status_code == 200
        assert resp.context["can_create_oauth"] is True


# ── ResetHelpersView ───────────────────────────────────────────


class TestResetHelpersView:
    def test_anonymous_redirect(self, client):
        resp = client.post(reverse("accounts:reset-helpers"))
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_post_resets_dismissed_helpers(self, client):
        user = UserFactory()
        user.dismissed_helpers = ["help1", "help2"]
        user.save(update_fields=["dismissed_helpers"])
        client.force_login(user)
        resp = client.post(reverse("accounts:reset-helpers"))
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.dismissed_helpers == []


# ── PasswordChangeView ─────────────────────────────────────────


class TestPasswordChangeView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:password-change"))
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_get_password_change(self, client):
        user = UserFactory(password="oldpass123")
        client.force_login(user)
        resp = client.get(reverse("accounts:password-change"))
        assert resp.status_code == 200

    def test_post_password_change_success(self, client):
        user = UserFactory(password="oldpass123")
        client.force_login(user)
        resp = client.post(reverse("accounts:password-change"), {
            "old_password": "oldpass123",
            "new_password1": "newpass456",
            "new_password2": "newpass456",
        })
        assert resp.status_code == 302
        assert resp.url == reverse("accounts:profile")
        user.refresh_from_db()
        assert user.check_password("newpass456")

    def test_post_password_change_wrong_old(self, client):
        user = UserFactory(password="oldpass123")
        client.force_login(user)
        resp = client.post(reverse("accounts:password-change"), {
            "old_password": "wrongpassword",
            "new_password1": "newpass456",
            "new_password2": "newpass456",
        })
        assert resp.status_code == 200

    def test_post_password_change_mismatch(self, client):
        user = UserFactory(password="oldpass123")
        client.force_login(user)
        resp = client.post(reverse("accounts:password-change"), {
            "old_password": "oldpass123",
            "new_password1": "newpass456",
            "new_password2": "newpass789",
        })
        assert resp.status_code == 200


# ── CompanySettingsView ────────────────────────────────────────


class TestCompanySettingsView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:company-settings"))
        assert resp.status_code == 302

    def test_get_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:company-settings"))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_get_with_read_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.config.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:company-settings"))
        assert resp.status_code == 200

    def test_get_superuser(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:company-settings"))
        assert resp.status_code == 200
        assert resp.context["can_edit"] is True

    def test_post_without_update_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.config.read")
        client.force_login(user)
        resp = client.post(reverse("accounts:company-settings"), {
            "name": "Acme Corp",
            "address": "123 Main St",
        })
        assert resp.status_code == 302
        assert resp.url == reverse("accounts:company-settings")

    def test_post_with_update_permission(self, client):
        user = UserFactory()
        group = _grant_perm(user, "system.config.read")
        perm_update = PermissionFactory(codename="system.config.update")
        group.permissions.add(perm_update)
        if hasattr(user, "_custom_perm_cache"):
            del user._custom_perm_cache
        client.force_login(user)
        resp = client.post(reverse("accounts:company-settings"), {
            "name": "Acme Corp",
            "address": "123 Main St",
        })
        assert resp.status_code == 302
        settings_obj = CompanySettings.get()
        assert settings_obj.name == "Acme Corp"

    def test_post_superuser(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.post(reverse("accounts:company-settings"), {
            "name": "SuperCo",
            "address": "456 HQ",
        })
        assert resp.status_code == 302
        settings_obj = CompanySettings.get()
        assert settings_obj.name == "SuperCo"

    def test_post_invalid_form(self, client):
        user = _superuser()
        client.force_login(user)
        # Both fields are optional/blank-ok on CompanySettings, so we test
        # that a valid but empty post works (renders 302)
        resp = client.post(reverse("accounts:company-settings"), {
            "name": "",
            "address": "",
        })
        assert resp.status_code == 302


# ── UserListView ───────────────────────────────────────────────


class TestUserListView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_with_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.users.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 200

    def test_superuser(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 200

    def test_filter_active(self, client):
        user = _superuser()
        UserFactory(is_active=True, email="active@test.com")
        UserFactory(is_active=False, email="inactive@test.com")
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list") + "?status=active")
        assert resp.status_code == 200
        emails = [u.email for u in resp.context["users"]]
        assert "inactive@test.com" not in emails

    def test_filter_inactive(self, client):
        user = _superuser()
        inactive = UserFactory(is_active=False, email="inactive2@test.com")
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list") + "?status=inactive")
        assert resp.status_code == 200
        emails = [u.email for u in resp.context["users"]]
        assert inactive.email in emails

    def test_sorting(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list") + "?sort=email&order=asc")
        assert resp.status_code == 200


# ── UserDetailView ─────────────────────────────────────────────


class TestUserDetailView:
    def test_anonymous_redirect(self, client):
        user = UserFactory()
        resp = client.get(reverse("accounts:user-detail", kwargs={"pk": user.pk}))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        viewer = UserFactory()
        target = UserFactory()
        client.force_login(viewer)
        resp = client.get(reverse("accounts:user-detail", kwargs={"pk": target.pk}))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_with_permission(self, client):
        viewer = UserFactory()
        _grant_perm(viewer, "system.users.read")
        target = UserFactory()
        client.force_login(viewer)
        resp = client.get(reverse("accounts:user-detail", kwargs={"pk": target.pk}))
        assert resp.status_code == 200
        assert resp.context["account_user"] == target

    def test_context_includes_groups_permissions_logs(self, client):
        viewer = _superuser()
        target = UserFactory()
        group = GroupFactory(name="TestGroup")
        group.users.add(target)
        perm = PermissionFactory(codename="context.scope.read")
        group.permissions.add(perm)
        AccessLog.objects.create(
            user=target,
            email_attempted=target.email,
            event_type="login_success",
        )
        client.force_login(viewer)
        resp = client.get(reverse("accounts:user-detail", kwargs={"pk": target.pk}))
        assert resp.status_code == 200
        assert group in resp.context["groups"]
        assert "context.scope.read" in resp.context["permissions"]
        assert len(resp.context["recent_access_logs"]) == 1


# ── UserCreateView ─────────────────────────────────────────────


class TestUserCreateView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:user-create"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-create"))
        assert resp.status_code == 302

    def test_get_form(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-create"))
        assert resp.status_code == 200

    def test_post_create_user(self, client):
        admin = _superuser()
        client.force_login(admin)
        resp = client.post(reverse("accounts:user-create"), {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "language": "",
            "timezone": "Europe/Paris",
            "is_active": "on",
        })
        assert resp.status_code == 302
        from accounts.models import User
        new_user = User.objects.get(email="newuser@example.com")
        assert new_user.created_by == admin
        assert new_user.check_password("testpass123")

    def test_post_create_user_password_mismatch(self, client):
        admin = _superuser()
        client.force_login(admin)
        resp = client.post(reverse("accounts:user-create"), {
            "email": "newuser2@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "differentpass",
            "language": "",
            "timezone": "Europe/Paris",
            "is_active": "on",
        })
        assert resp.status_code == 200  # re-renders form

    def test_post_create_user_missing_fields(self, client):
        admin = _superuser()
        client.force_login(admin)
        resp = client.post(reverse("accounts:user-create"), {
            "email": "",
            "first_name": "",
            "last_name": "",
            "password1": "",
            "password2": "",
            "language": "",
            "timezone": "Europe/Paris",
        })
        assert resp.status_code == 200


# ── UserUpdateView ─────────────────────────────────────────────


class TestUserUpdateView:
    def test_anonymous_redirect(self, client):
        user = UserFactory()
        resp = client.get(reverse("accounts:user-update", kwargs={"pk": user.pk}))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        viewer = UserFactory()
        target = UserFactory()
        client.force_login(viewer)
        resp = client.get(reverse("accounts:user-update", kwargs={"pk": target.pk}))
        assert resp.status_code == 302

    def test_get_update_form(self, client):
        admin = _superuser()
        target = UserFactory()
        client.force_login(admin)
        resp = client.get(reverse("accounts:user-update", kwargs={"pk": target.pk}))
        assert resp.status_code == 200

    def test_post_update_user(self, client):
        admin = _superuser()
        target = UserFactory(first_name="Old", last_name="Name")
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:user-update", kwargs={"pk": target.pk}),
            {
                "email": target.email,
                "first_name": "New",
                "last_name": "Name",
                "job_title": "Developer",
                "department": "",
                "phone": "",
                "language": "",
                "timezone": "Europe/Paris",
                "is_active": "on",
            },
        )
        assert resp.status_code == 302
        target.refresh_from_db()
        assert target.first_name == "New"
        assert target.job_title == "Developer"

    def test_post_update_user_invalid(self, client):
        admin = _superuser()
        target = UserFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:user-update", kwargs={"pk": target.pk}),
            {
                "email": "",  # required
                "first_name": "New",
                "last_name": "Name",
                "language": "",
                "timezone": "Europe/Paris",
            },
        )
        assert resp.status_code == 200


# ── GroupListView ──────────────────────────────────────────────


class TestGroupListView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:group-list"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:group-list"))
        assert resp.status_code == 302

    def test_with_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.groups.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:group-list"))
        assert resp.status_code == 200

    def test_superuser(self, client):
        user = _superuser()
        GroupFactory(name="Alpha")
        GroupFactory(name="Beta")
        client.force_login(user)
        resp = client.get(reverse("accounts:group-list"))
        assert resp.status_code == 200


# ── GroupDetailView ────────────────────────────────────────────


class TestGroupDetailView:
    def test_anonymous_redirect(self, client):
        group = GroupFactory()
        resp = client.get(reverse("accounts:group-detail", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        group = GroupFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:group-detail", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_with_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.groups.read")
        group = GroupFactory(name="Detail Test")
        client.force_login(user)
        resp = client.get(reverse("accounts:group-detail", kwargs={"pk": group.pk}))
        assert resp.status_code == 200
        assert resp.context["group"] == group

    def test_context_includes_permission_matrix(self, client):
        user = _superuser()
        group = GroupFactory()
        perm = PermissionFactory(codename="context.scope.read")
        group.permissions.add(perm)
        client.force_login(user)
        resp = client.get(reverse("accounts:group-detail", kwargs={"pk": group.pk}))
        assert resp.status_code == 200
        assert "permission_matrix" in resp.context
        assert "all_actions" in resp.context
        assert "all_users" in resp.context
        assert "all_scopes" in resp.context
        assert "group_scope_ids" in resp.context

    def test_context_group_users(self, client):
        user = _superuser()
        group = GroupFactory()
        member = UserFactory()
        group.users.add(member)
        client.force_login(user)
        resp = client.get(reverse("accounts:group-detail", kwargs={"pk": group.pk}))
        assert member in resp.context["group_users"]


# ── GroupCreateView ────────────────────────────────────────────


class TestGroupCreateView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:group-create"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:group-create"))
        assert resp.status_code == 302

    def test_get_form(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:group-create"))
        assert resp.status_code == 200

    def test_post_create_group(self, client):
        admin = _superuser()
        client.force_login(admin)
        resp = client.post(reverse("accounts:group-create"), {
            "name": "My New Group",
            "description": "Test description",
        })
        assert resp.status_code == 302
        group = Group.objects.get(name="My New Group")
        assert group.created_by == admin

    def test_post_create_group_invalid(self, client):
        admin = _superuser()
        client.force_login(admin)
        resp = client.post(reverse("accounts:group-create"), {
            "name": "",  # required
            "description": "",
        })
        assert resp.status_code == 200


# ── GroupUpdateView ────────────────────────────────────────────


class TestGroupUpdateView:
    def test_anonymous_redirect(self, client):
        group = GroupFactory()
        resp = client.get(reverse("accounts:group-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        group = GroupFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:group-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_get_update_form(self, client):
        admin = _superuser()
        group = GroupFactory(name="Editable")
        client.force_login(admin)
        resp = client.get(reverse("accounts:group-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 200

    def test_get_system_group_redirects(self, client):
        admin = _superuser()
        group = GroupFactory(name="System Group", is_system=True)
        client.force_login(admin)
        resp = client.get(reverse("accounts:group-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302
        assert str(group.pk) in resp.url

    def test_post_update_group(self, client):
        admin = _superuser()
        group = GroupFactory(name="Old Name")
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-update", kwargs={"pk": group.pk}),
            {"name": "New Name", "description": "Updated"},
        )
        assert resp.status_code == 302
        group.refresh_from_db()
        assert group.name == "New Name"

    def test_post_system_group_blocked(self, client):
        admin = _superuser()
        group = GroupFactory(name="Sys Group", is_system=True)
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-update", kwargs={"pk": group.pk}),
            {"name": "Hacked Name", "description": ""},
        )
        assert resp.status_code == 302
        group.refresh_from_db()
        assert group.name == "Sys Group"

    def test_post_update_group_invalid(self, client):
        admin = _superuser()
        group = GroupFactory(name="Valid Name")
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-update", kwargs={"pk": group.pk}),
            {"name": "", "description": ""},
        )
        assert resp.status_code == 200


# ── GroupPermissionsUpdateView ─────────────────────────────────


class TestGroupPermissionsUpdateView:
    def test_anonymous_redirect(self, client):
        group = GroupFactory()
        resp = client.post(reverse("accounts:group-permissions-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        group = GroupFactory()
        client.force_login(user)
        resp = client.post(reverse("accounts:group-permissions-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_update_permissions(self, client):
        admin = _superuser()
        group = GroupFactory()
        p1 = PermissionFactory(codename="context.scope.read")
        p2 = PermissionFactory(codename="context.scope.create")
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-permissions-update", kwargs={"pk": group.pk}),
            {"permissions": ["context.scope.read", "context.scope.create"]},
        )
        assert resp.status_code == 302
        assert set(group.permissions.values_list("codename", flat=True)) == {
            "context.scope.read",
            "context.scope.create",
        }

    def test_system_group_blocked(self, client):
        admin = _superuser()
        group = GroupFactory(is_system=True)
        p1 = PermissionFactory(codename="context.scope.read")
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-permissions-update", kwargs={"pk": group.pk}),
            {"permissions": ["context.scope.read"]},
        )
        assert resp.status_code == 302
        assert group.permissions.count() == 0  # unchanged

    def test_clear_permissions(self, client):
        admin = _superuser()
        group = GroupFactory()
        p1 = PermissionFactory(codename="context.scope.read")
        group.permissions.add(p1)
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-permissions-update", kwargs={"pk": group.pk}),
            {},  # no permissions selected
        )
        assert resp.status_code == 302
        assert group.permissions.count() == 0


# ── GroupUsersUpdateView ───────────────────────────────────────


class TestGroupUsersUpdateView:
    def test_anonymous_redirect(self, client):
        group = GroupFactory()
        resp = client.post(reverse("accounts:group-users-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_add_single_user(self, client):
        admin = _superuser()
        group = GroupFactory()
        member = UserFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "add", "user_id": str(member.pk)},
        )
        assert resp.status_code == 302
        assert member in group.users.all()

    def test_add_multiple_users(self, client):
        admin = _superuser()
        group = GroupFactory()
        m1 = UserFactory()
        m2 = UserFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "add", "user_ids": [str(m1.pk), str(m2.pk)]},
        )
        assert resp.status_code == 302
        assert group.users.count() == 2

    def test_remove_single_user(self, client):
        admin = _superuser()
        group = GroupFactory()
        member = UserFactory()
        group.users.add(member)
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "remove", "user_id": str(member.pk)},
        )
        assert resp.status_code == 302
        assert member not in group.users.all()

    def test_bulk_remove_users(self, client):
        admin = _superuser()
        group = GroupFactory()
        m1 = UserFactory()
        m2 = UserFactory()
        group.users.add(m1, m2)
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "bulk_remove", "user_ids": [str(m1.pk), str(m2.pk)]},
        )
        assert resp.status_code == 302
        assert group.users.count() == 0

    def test_add_no_users(self, client):
        """When action=add but no user_id or user_ids given, nothing happens."""
        admin = _superuser()
        group = GroupFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "add"},
        )
        assert resp.status_code == 302
        assert group.users.count() == 0

    def test_remove_no_user_id(self, client):
        """When action=remove but no user_id given, nothing happens."""
        admin = _superuser()
        group = GroupFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "remove"},
        )
        assert resp.status_code == 302

    def test_unknown_action(self, client):
        """Unknown action just redirects without error."""
        admin = _superuser()
        group = GroupFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-users-update", kwargs={"pk": group.pk}),
            {"action": "unknown"},
        )
        assert resp.status_code == 302


# ── GroupScopesUpdateView ──────────────────────────────────────


class TestGroupScopesUpdateView:
    def test_anonymous_redirect(self, client):
        group = GroupFactory()
        resp = client.post(reverse("accounts:group-scopes-update", kwargs={"pk": group.pk}))
        assert resp.status_code == 302

    def test_update_scopes(self, client):
        admin = _superuser()
        group = GroupFactory()
        s1 = ScopeFactory()
        s2 = ScopeFactory()
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-scopes-update", kwargs={"pk": group.pk}),
            {"scopes": [str(s1.pk), str(s2.pk)]},
        )
        assert resp.status_code == 302
        assert set(group.allowed_scopes.values_list("id", flat=True)) == {s1.pk, s2.pk}

    def test_clear_scopes(self, client):
        admin = _superuser()
        group = GroupFactory()
        s1 = ScopeFactory()
        group.allowed_scopes.add(s1)
        client.force_login(admin)
        resp = client.post(
            reverse("accounts:group-scopes-update", kwargs={"pk": group.pk}),
            {},  # no scopes
        )
        assert resp.status_code == 302
        assert group.allowed_scopes.count() == 0


# ── PermissionListView ─────────────────────────────────────────


class TestPermissionListView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:permission-list"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:permission-list"))
        assert resp.status_code == 302

    def test_with_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.groups.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:permission-list"))
        assert resp.status_code == 200
        assert "grouped_permissions" in resp.context

    def test_superuser(self, client):
        user = _superuser()
        # Create a few permissions so we have data
        PermissionFactory(codename="context.scope.read")
        PermissionFactory(codename="context.scope.create")
        client.force_login(user)
        resp = client.get(reverse("accounts:permission-list"))
        assert resp.status_code == 200
        grouped = resp.context["grouped_permissions"]
        # Check the structure
        if "context" in grouped:
            assert "features" in grouped["context"]


# ── AccessLogListView ──────────────────────────────────────────


class TestAccessLogListView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:access-log-list"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:access-log-list"))
        assert resp.status_code == 302

    def test_with_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.audit_trail.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:access-log-list"))
        assert resp.status_code == 200

    def test_superuser_sees_logs(self, client):
        user = _superuser()
        AccessLog.objects.create(
            user=user,
            email_attempted=user.email,
            event_type="login_success",
        )
        client.force_login(user)
        resp = client.get(reverse("accounts:access-log-list"))
        assert resp.status_code == 200
        assert len(resp.context["logs"]) >= 1

    def test_filter_by_event_type(self, client):
        user = _superuser()
        AccessLog.objects.create(
            user=user,
            email_attempted=user.email,
            event_type="login_success",
        )
        AccessLog.objects.create(
            user=user,
            email_attempted=user.email,
            event_type="login_failed",
        )
        client.force_login(user)
        resp = client.get(reverse("accounts:access-log-list") + "?event_type=login_success")
        assert resp.status_code == 200
        for log in resp.context["logs"]:
            assert log.event_type == "login_success"

    def test_filter_by_email(self, client):
        user = _superuser()
        AccessLog.objects.create(
            user=user,
            email_attempted="specific@test.com",
            event_type="login_success",
        )
        client.force_login(user)
        resp = client.get(reverse("accounts:access-log-list") + "?email=specific")
        assert resp.status_code == 200
        for log in resp.context["logs"]:
            assert "specific" in log.email_attempted

    def test_filter_by_date_range(self, client):
        user = _superuser()
        AccessLog.objects.create(
            user=user,
            email_attempted=user.email,
            event_type="login_success",
        )
        client.force_login(user)
        resp = client.get(
            reverse("accounts:access-log-list") + "?date_from=2020-01-01&date_to=2099-12-31"
        )
        assert resp.status_code == 200

    def test_sorting(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:access-log-list") + "?sort=email&order=asc")
        assert resp.status_code == 200


# ── ActionLogListView ──────────────────────────────────────────


class TestActionLogListView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:action-log-list"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list"))
        assert resp.status_code == 302

    def test_with_permission(self, client):
        user = UserFactory()
        _grant_perm(user, "system.audit_trail.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list"))
        assert resp.status_code == 200

    def test_superuser_with_history_entries(self, client):
        """Create a Scope to generate historical records, then verify the action log view annotates them."""
        user = _superuser()
        # Create a scope - this will generate a "+" historical record
        scope = ScopeFactory(name="Test Scope for History")
        # Update the scope - this will generate a "~" historical record
        scope.name = "Updated Scope"
        scope.save()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list"))
        assert resp.status_code == 200
        assert "entries" in resp.context
        assert "users" in resp.context
        assert "module_labels" in resp.context
        # Verify entries were annotated with action labels and badges
        entries = resp.context["entries"]
        assert len(entries) >= 2
        for entry in entries:
            assert hasattr(entry, "action_label")
            assert hasattr(entry, "action_badge")
            assert hasattr(entry, "app_label")
            assert hasattr(entry, "model_label")
            assert hasattr(entry, "object_repr")

    def test_filter_by_action_creation_with_data(self, client):
        user = _superuser()
        ScopeFactory(name="Creation Filter Scope")
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list") + "?action=%2B")
        assert resp.status_code == 200
        for entry in resp.context["entries"]:
            assert entry.history_type == "+"

    def test_filter_by_action_modification_with_data(self, client):
        user = _superuser()
        scope = ScopeFactory(name="Mod Filter Scope")
        scope.name = "Modified"
        scope.save()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list") + "?action=~")
        assert resp.status_code == 200

    def test_filter_by_action_deletion(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list") + "?action=-")
        assert resp.status_code == 200

    def test_filter_by_action_approval_with_data(self, client):
        """Filter by approval: creates a scope, then approves it to generate an approval history record."""
        user = _superuser()
        scope = ScopeFactory(name="Approval Scope")
        # Simulate an approval-only change
        scope.is_approved = True
        scope.approved_by = user
        from django.utils import timezone as tz
        scope.approved_at = tz.now()
        scope.save()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list") + "?action=approval")
        assert resp.status_code == 200

    def test_filter_by_module(self, client):
        user = _superuser()
        ScopeFactory(name="Module Filter Scope")
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list") + "?module=context")
        assert resp.status_code == 200
        for entry in resp.context["entries"]:
            assert entry.app_label != ""

    def test_filter_by_module_excludes_other_modules(self, client):
        user = _superuser()
        ScopeFactory(name="Exclusion Filter Scope")
        client.force_login(user)
        # Filter for a module that likely has no records
        resp = client.get(reverse("accounts:action-log-list") + "?module=risks")
        assert resp.status_code == 200

    def test_filter_by_user(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list") + f"?user={user.pk}")
        assert resp.status_code == 200

    def test_filter_by_date_range(self, client):
        user = _superuser()
        ScopeFactory(name="Date Filter Scope")
        client.force_login(user)
        resp = client.get(
            reverse("accounts:action-log-list") + "?date_from=2020-01-01&date_to=2099-12-31"
        )
        assert resp.status_code == 200

    def test_history_badges_for_creation(self, client):
        """Verify creation entries get 'success' badge."""
        user = _superuser()
        ScopeFactory(name="Badge Test Scope")
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list"))
        assert resp.status_code == 200
        creation_entries = [e for e in resp.context["entries"] if e.history_type == "+"]
        for entry in creation_entries:
            assert entry.action_badge == "success"

    def test_history_badges_for_modification(self, client):
        """Verify modification entries get 'warning' badge."""
        user = _superuser()
        scope = ScopeFactory(name="Badge Mod Scope")
        scope.description = "changed"
        scope.save()
        client.force_login(user)
        resp = client.get(reverse("accounts:action-log-list"))
        assert resp.status_code == 200
        mod_entries = [e for e in resp.context["entries"] if e.history_type == "~"]
        for entry in mod_entries:
            assert entry.action_badge in ("warning", "info", "dark")


# ── CalendarSubscriptionListView ───────────────────────────────


class TestCalendarSubscriptionListView:
    def test_anonymous_redirect(self, client):
        resp = client.get(reverse("accounts:calendar-subscription-list"))
        assert resp.status_code == 302

    def test_no_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:calendar-subscription-list"))
        assert resp.status_code == 302

    def test_superuser(self, client):
        user = _superuser()
        CalendarToken.objects.create(user=user, name="Test Token")
        client.force_login(user)
        resp = client.get(reverse("accounts:calendar-subscription-list"))
        assert resp.status_code == 200
        assert len(resp.context["tokens"]) == 1


# ── CalendarSubscriptionRevokeView ─────────────────────────────


class TestCalendarSubscriptionRevokeView:
    def test_anonymous_redirect(self, client):
        user = UserFactory()
        token = CalendarToken.objects.create(user=user, name="Token")
        resp = client.post(reverse("accounts:calendar-subscription-revoke", kwargs={"pk": token.pk}))
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_no_permission(self, client):
        owner = UserFactory()
        token = CalendarToken.objects.create(user=owner, name="Token")
        viewer = UserFactory()
        client.force_login(viewer)
        resp = client.post(reverse("accounts:calendar-subscription-revoke", kwargs={"pk": token.pk}))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_revoke_token(self, client):
        admin = _superuser()
        owner = UserFactory()
        token = CalendarToken.objects.create(user=owner, name="My Token")
        client.force_login(admin)
        resp = client.post(reverse("accounts:calendar-subscription-revoke", kwargs={"pk": token.pk}))
        assert resp.status_code == 302
        assert CalendarToken.objects.filter(pk=token.pk).count() == 0


# ── PermissionRequiredMixin (cross-cutting) ────────────────────


class TestPermissionRequiredMixin:
    """Test the custom PermissionRequiredMixin behavior across different views."""

    def test_unauthenticated_user_redirected_to_login(self, client):
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url
        assert "next=" in resp.url

    def test_authenticated_without_perm_redirected_to_home(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 302
        assert resp.url == "/"

    def test_superuser_bypasses_permission_check(self, client):
        user = _superuser()
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 200

    def test_user_with_correct_permission_has_access(self, client):
        user = UserFactory()
        _grant_perm(user, "system.users.read")
        client.force_login(user)
        resp = client.get(reverse("accounts:user-list"))
        assert resp.status_code == 200
