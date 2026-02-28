import pytest

from accounts.backends import EmailAuthBackend, GroupPermissionBackend
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


class TestEmailAuthBackend:
    def setup_method(self):
        self.backend = EmailAuthBackend()

    def test_authenticate_valid(self):
        user = UserFactory(password="secret123")
        result = self.backend.authenticate(None, username=user.email, password="secret123")
        assert result == user

    def test_authenticate_wrong_password(self):
        user = UserFactory(password="secret123")
        result = self.backend.authenticate(None, username=user.email, password="wrong")
        assert result is None

    def test_authenticate_nonexistent_email(self):
        result = self.backend.authenticate(None, username="noone@test.com", password="x")
        assert result is None

    def test_authenticate_inactive_user(self):
        user = UserFactory(password="secret123", is_active=False)
        result = self.backend.authenticate(None, username=user.email, password="secret123")
        assert result is None

    def test_authenticate_locked_user(self):
        user = UserFactory(password="secret123")
        user.lock_account()
        result = self.backend.authenticate(None, username=user.email, password="secret123")
        assert result is None

    def test_authenticate_case_insensitive_email(self):
        user = UserFactory(email="Alice@Example.COM", password="secret123")
        result = self.backend.authenticate(None, username="alice@example.com", password="secret123")
        assert result == user


class TestGroupPermissionBackend:
    def setup_method(self):
        self.backend = GroupPermissionBackend()

    def test_has_perm_via_group(self):
        user = UserFactory()
        perm = PermissionFactory(codename="context.scope.read")
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(user)
        assert self.backend.has_perm(user, "context.scope.read") is True

    def test_no_perm_without_group(self):
        user = UserFactory()
        PermissionFactory(codename="context.scope.read")
        assert self.backend.has_perm(user, "context.scope.read") is False

    def test_inactive_user_has_no_perm(self):
        user = UserFactory(is_active=False)
        perm = PermissionFactory(codename="context.scope.read")
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(user)
        assert self.backend.has_perm(user, "context.scope.read") is False

    def test_has_module_perms(self):
        user = UserFactory()
        perm = PermissionFactory(codename="assets.group.create")
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(user)
        assert self.backend.has_module_perms(user, "assets") is True
        assert self.backend.has_module_perms(user, "context") is False


class TestScopeRestriction:
    def test_superuser_unrestricted(self):
        user = UserFactory(is_superuser=True)
        assert GroupPermissionBackend.get_allowed_scope_ids(user) is None

    def test_group_with_no_scopes_is_unrestricted(self):
        user = UserFactory()
        group = GroupFactory()
        group.users.add(user)
        # group has no allowed_scopes → unrestricted
        assert GroupPermissionBackend.get_allowed_scope_ids(user) is None

    def test_group_with_scopes_restricts(self):
        user = UserFactory()
        scope = ScopeFactory()
        group = GroupFactory()
        group.users.add(user)
        group.allowed_scopes.add(scope)
        result = GroupPermissionBackend.get_allowed_scope_ids(user)
        assert result == {scope.pk}

    def test_inactive_user_gets_empty_set(self):
        user = UserFactory(is_active=False)
        result = GroupPermissionBackend.get_allowed_scope_ids(user)
        assert result == set()
