import pytest
from django.test import Client
from django.urls import reverse

from accounts.constants import AccessEventType
from accounts.middleware import IMPERSONATION_SESSION_KEY
from accounts.models import AccessLog
from accounts.tests.factories import UserFactory, GroupFactory, PermissionFactory

pytestmark = pytest.mark.django_db


def _admin_with_impersonate_perm():
    """Create an admin user with the impersonate permission."""
    user = UserFactory(is_superuser=True)
    return user


def _user_with_perm():
    """Create a non-superuser with impersonate permission via a group."""
    perm = PermissionFactory(
        codename="system.users.impersonate",
        module="system",
        feature="users",
        action="impersonate",
    )
    group = GroupFactory()
    group.permissions.add(perm)
    user = UserFactory()
    group.users.add(user)
    return user


class TestImpersonateStart:
    def test_requires_permission(self):
        user = UserFactory()
        target = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.post(reverse("accounts:impersonate-start", args=[target.pk]))
        assert resp.status_code == 302
        assert resp.url == "/"  # redirected by PermissionRequiredMixin

    def test_success(self):
        admin = _admin_with_impersonate_perm()
        target = UserFactory()
        client = Client()
        client.force_login(admin)
        resp = client.post(reverse("accounts:impersonate-start", args=[target.pk]))
        assert resp.status_code == 302
        assert resp.url == "/"
        # Session has impersonation key
        assert client.session.get(IMPERSONATION_SESSION_KEY) == str(admin.pk)
        # Access log recorded
        log = AccessLog.objects.filter(event_type=AccessEventType.IMPERSONATION_START).first()
        assert log is not None
        assert log.user == admin
        assert log.metadata["impersonated_email"] == target.email

    def test_cannot_impersonate_self(self):
        admin = _admin_with_impersonate_perm()
        client = Client()
        client.force_login(admin)
        resp = client.post(reverse("accounts:impersonate-start", args=[admin.pk]))
        assert resp.status_code == 302
        assert IMPERSONATION_SESSION_KEY not in client.session

    def test_cannot_impersonate_inactive(self):
        admin = _admin_with_impersonate_perm()
        target = UserFactory(is_active=False)
        client = Client()
        client.force_login(admin)
        resp = client.post(reverse("accounts:impersonate-start", args=[target.pk]))
        assert resp.status_code == 302
        assert IMPERSONATION_SESSION_KEY not in client.session

    def test_cannot_nest_impersonation(self):
        admin = _admin_with_impersonate_perm()
        target1 = UserFactory()
        target2 = UserFactory()
        client = Client()
        client.force_login(admin)
        # Start first impersonation
        client.post(reverse("accounts:impersonate-start", args=[target1.pk]))
        # Try to start second impersonation (session key set, but user is target1 now)
        # The PermissionRequiredMixin will block because target1 is not superuser
        # and doesn't have impersonate permission
        resp = client.post(reverse("accounts:impersonate-start", args=[target2.pk]))
        assert resp.status_code == 302

    def test_non_superuser_with_perm(self):
        admin = _user_with_perm()
        target = UserFactory()
        client = Client()
        client.force_login(admin)
        resp = client.post(reverse("accounts:impersonate-start", args=[target.pk]))
        assert resp.status_code == 302
        assert resp.url == "/"
        assert client.session.get(IMPERSONATION_SESSION_KEY) == str(admin.pk)


class TestImpersonateStop:
    def test_stop_restores_original_user(self):
        admin = _admin_with_impersonate_perm()
        target = UserFactory()
        client = Client()
        client.force_login(admin)
        client.post(reverse("accounts:impersonate-start", args=[target.pk]))
        # Now stop
        resp = client.post(reverse("accounts:impersonate-stop"))
        assert resp.status_code == 302
        assert resp.url == "/"
        assert IMPERSONATION_SESSION_KEY not in client.session
        # Access log recorded
        log = AccessLog.objects.filter(event_type=AccessEventType.IMPERSONATION_STOP).first()
        assert log is not None
        assert log.user == admin

    def test_stop_without_impersonation(self):
        admin = _admin_with_impersonate_perm()
        client = Client()
        client.force_login(admin)
        resp = client.post(reverse("accounts:impersonate-stop"))
        assert resp.status_code == 302
        assert resp.url == "/"


class TestImpersonationMiddleware:
    def test_impersonator_set_on_request(self):
        admin = _admin_with_impersonate_perm()
        target = UserFactory()
        client = Client()
        client.force_login(admin)
        client.post(reverse("accounts:impersonate-start", args=[target.pk]))
        # Access a page and check the banner is present
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"impersonation-banner" in resp.content

    def test_no_banner_when_not_impersonating(self):
        admin = _admin_with_impersonate_perm()
        client = Client()
        client.force_login(admin)
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"impersonation-banner" not in resp.content
