import base64
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import CalendarToken
from accounts.tests.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def token(user):
    return CalendarToken.objects.create(user=user, name="Test")


class TestDeactivationRevocation:
    def test_tokens_deleted_on_deactivation(self, user, token):
        CalendarToken.objects.create(user=user, name="Test 2")
        assert CalendarToken.objects.filter(user=user).count() == 2
        user.is_active = False
        user.save()
        assert CalendarToken.objects.filter(user=user).count() == 0

    def test_tokens_kept_on_reactivation(self, user, token):
        user.is_active = False
        user.save()
        user.is_active = True
        user.save()
        ct = CalendarToken.objects.create(user=user, name="New")
        assert CalendarToken.objects.filter(user=user).count() == 1


class TestInactivityRevocation:
    def test_inactive_token_revoked(self, user, token, rf):
        CalendarToken.objects.filter(pk=token.pk).update(
            last_used_at=timezone.now() - timedelta(days=31)
        )
        from core.views import ICalFeedView
        creds = base64.b64encode(f"{user.email}:{token.token}".encode()).decode()
        request = rf.get("/calendar.ics", HTTP_AUTHORIZATION=f"Basic {creds}")
        result = ICalFeedView()._authenticate(request)
        assert result is None
        assert not CalendarToken.objects.filter(pk=token.pk).exists()

    def test_recently_created_token_works(self, user, token, rf):
        from core.views import ICalFeedView
        creds = base64.b64encode(f"{user.email}:{token.token}".encode()).decode()
        request = rf.get("/calendar.ics", HTTP_AUTHORIZATION=f"Basic {creds}")
        result = ICalFeedView()._authenticate(request)
        assert result == user
        assert CalendarToken.objects.filter(pk=token.pk).exists()

    def test_recently_used_token_works(self, user, token, rf):
        CalendarToken.objects.filter(pk=token.pk).update(
            last_used_at=timezone.now() - timedelta(days=10)
        )
        from core.views import ICalFeedView
        creds = base64.b64encode(f"{user.email}:{token.token}".encode()).decode()
        request = rf.get("/calendar.ics", HTTP_AUTHORIZATION=f"Basic {creds}")
        result = ICalFeedView()._authenticate(request)
        assert result == user
