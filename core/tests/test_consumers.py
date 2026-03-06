"""Tests for the dashboard WebSocket consumer and signal handlers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from accounts.tests.factories import UserFactory
from core.consumers import DashboardConsumer
from core.signals import _notify_dashboard


@pytest.fixture
def user(db):
    return UserFactory(is_superuser=True)


class TestBuildDashboardData:
    """Test the synchronous data builder directly."""

    @pytest.mark.django_db
    def test_returns_all_keys(self, user):
        """The data dict contains all expected dashboard keys."""
        # Call the inner sync function directly (unwrap database_sync_to_async)
        data = DashboardConsumer._build_dashboard_data.__wrapped__(
            DashboardConsumer(), user
        )
        expected_keys = {
            "scope_count", "issue_count", "stakeholder_count", "objective_count",
            "role_count", "site_count", "mandatory_roles_no_user",
            "swot_count", "activity_count", "critical_activities_no_owner",
            "essential_count", "support_count", "dependency_count", "spof_count",
            "eol_count", "personal_data_count", "supplier_count",
            "expired_contract_count", "supplier_dep_count", "supplier_spof_count",
            "supplier_type_count", "group_count",
            "risk_assessment_count", "risk_count", "treatment_plan_count",
            "treatment_in_progress_count", "critical_risk_count",
            "acceptance_count", "expiring_acceptance_count",
            "threat_count", "vulnerability_count",
            "framework_count", "overall_compliance", "requirement_count",
            "non_compliant_count", "assessment_count", "action_plan_count",
            "overdue_plan_count", "mapping_count",
            "alert_count",
        }
        assert set(data.keys()) == expected_keys

    @pytest.mark.django_db
    def test_values_are_integers(self, user):
        """All values are integers (JSON-serialisable)."""
        data = DashboardConsumer._build_dashboard_data.__wrapped__(
            DashboardConsumer(), user
        )
        for key, value in data.items():
            assert isinstance(value, int), f"{key} should be int, got {type(value)}"

    @pytest.mark.django_db
    def test_empty_database_zero_counts(self, user):
        """With an empty database all counts should be zero."""
        data = DashboardConsumer._build_dashboard_data.__wrapped__(
            DashboardConsumer(), user
        )
        for key, value in data.items():
            assert value == 0, f"{key} should be 0 on empty DB, got {value}"


class TestDashboardConsumerConnect:
    """Test WebSocket connect/disconnect logic."""

    @pytest.mark.django_db
    def test_anonymous_user_rejected(self):
        """Anonymous users should be rejected on connect."""
        from django.contrib.auth.models import AnonymousUser

        consumer = DashboardConsumer()
        consumer.scope = {"user": AnonymousUser()}
        consumer.channel_layer = MagicMock()
        consumer.channel_name = "test-channel"

        # Mock close and accept
        close_called = False

        async def mock_close():
            nonlocal close_called
            close_called = True

        consumer.close = mock_close
        consumer.accept = MagicMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(consumer.connect())
        assert close_called

    @pytest.mark.django_db
    def test_authenticated_user_accepted(self, user):
        """Authenticated users should be accepted."""
        consumer = DashboardConsumer()
        consumer.scope = {"user": user}
        consumer.channel_name = "test-channel"

        accepted = False
        sent_messages = []

        async def mock_accept():
            nonlocal accepted
            accepted = True

        async def mock_send(text_data=None, bytes_data=None):
            if text_data:
                sent_messages.append(json.loads(text_data))

        mock_layer = MagicMock()
        mock_layer.group_add = MagicMock(return_value=_async_noop())
        consumer.channel_layer = mock_layer
        consumer.accept = mock_accept
        consumer.send = mock_send

        import asyncio
        asyncio.get_event_loop().run_until_complete(consumer.connect())
        assert accepted
        assert len(sent_messages) == 1
        assert sent_messages[0]["type"] == "dashboard.update"
        assert "data" in sent_messages[0]


class TestNotifyDashboard:
    """Test the signal handler notification function."""

    @patch("core.signals.get_channel_layer")
    def test_notify_sends_group_message(self, mock_get_layer):
        """_notify_dashboard sends a dashboard.refresh to the group."""
        mock_layer = MagicMock()
        mock_layer.group_send = MagicMock(return_value=_async_noop())
        mock_get_layer.return_value = mock_layer

        _notify_dashboard()

        mock_layer.group_send.assert_called_once()
        args = mock_layer.group_send.call_args
        assert args[0][0] == "dashboard"
        assert args[0][1]["type"] == "dashboard.refresh"

    @patch("core.signals.get_channel_layer")
    def test_notify_handles_no_channel_layer(self, mock_get_layer):
        """_notify_dashboard is a no-op when channel layer is unavailable."""
        mock_get_layer.return_value = None
        # Should not raise
        _notify_dashboard()


class TestSignalIntegration:
    """Test that model saves trigger dashboard notifications."""

    @pytest.mark.django_db
    @patch("core.signals._notify_dashboard")
    def test_scope_save_triggers_notify(self, mock_notify):
        """Saving a Scope model should trigger a dashboard refresh."""
        from context.tests.factories import ScopeFactory

        ScopeFactory()
        assert mock_notify.called

    @pytest.mark.django_db
    @patch("core.signals._notify_dashboard")
    def test_non_dashboard_model_no_notify(self, mock_notify):
        """Saving a non-dashboard model should NOT trigger a refresh."""
        # UserFactory creates a User, which is not in _DASHBOARD_MODELS
        UserFactory()
        assert not mock_notify.called


async def _async_noop(*args, **kwargs):
    """Awaitable no-op helper for mocking async methods."""
    pass
