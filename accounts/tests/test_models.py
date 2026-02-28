from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.constants import LOCKOUT_DURATION_MINUTES, MAX_FAILED_ATTEMPTS
from accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserLockout:
    """P0: account lockout logic."""

    def test_new_user_is_not_locked(self):
        user = UserFactory()
        assert user.is_locked is False

    def test_lock_account_sets_locked_until(self):
        user = UserFactory()
        user.lock_account()
        user.refresh_from_db()
        assert user.is_locked is True
        assert user.locked_until is not None

    def test_lock_expires_after_duration(self):
        user = UserFactory()
        user.locked_until = timezone.now() - timedelta(minutes=1)
        user.save(update_fields=["locked_until"])
        assert user.is_locked is False

    def test_increment_locks_at_max_attempts(self):
        user = UserFactory()
        for _ in range(MAX_FAILED_ATTEMPTS):
            user.increment_failed_attempts()
        user.refresh_from_db()
        assert user.is_locked is True

    def test_increment_does_not_lock_before_max(self):
        user = UserFactory()
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            user.increment_failed_attempts()
        user.refresh_from_db()
        assert user.is_locked is False

    def test_reset_failed_attempts_unlocks(self):
        user = UserFactory()
        user.lock_account()
        user.reset_failed_attempts()
        user.refresh_from_db()
        assert user.is_locked is False
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


class TestUserDisplayName:
    def test_display_name_full(self):
        user = UserFactory(first_name="Alice", last_name="Dupont")
        assert user.display_name == "Alice Dupont"

    def test_display_name_falls_back_to_email(self):
        user = UserFactory(first_name="", last_name="")
        assert user.display_name == user.email
