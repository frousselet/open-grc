"""Tests for the persistent management review workflow (ISO 27001:2022 9.3)."""

from datetime import date, datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.models import ComplianceActionPlan
from context.models import Indicator, IndicatorMeasurement
from reports.constants import ManagementReviewStatus
from reports.management_review import _compute_indicator_trend
from reports.models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewDecision,
)

from .factories import (
    IsmsChangeFactory,
    ManagementReviewDecisionFactory,
    ManagementReviewFactory,
    ManagementReviewParticipantFactory,
)


pytestmark = pytest.mark.django_db


# ─── Model tests ────────────────────────────────────────────────────


class TestManagementReviewModel:

    def test_reference_auto_generated(self):
        review = ManagementReviewFactory()
        assert review.reference.startswith("MRVW-")

    def test_get_allowed_transitions_from_planned(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        allowed = review.get_allowed_transitions()
        assert ManagementReviewStatus.IN_PREPARATION in allowed
        assert ManagementReviewStatus.CANCELLED in allowed

    def test_get_allowed_transitions_from_closed(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.CLOSED)
        assert review.get_allowed_transitions() == []

    def test_transition_forward(self):
        user = UserFactory()
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        review.transition_to(
            ManagementReviewStatus.IN_PREPARATION, user,
        )
        assert review.status == ManagementReviewStatus.IN_PREPARATION
        assert review.transitions.count() == 1

    def test_transition_invalid_raises(self):
        user = UserFactory()
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        with pytest.raises(ValueError):
            review.transition_to(ManagementReviewStatus.CLOSED, user)

    def test_cancellation_requires_comment(self):
        user = UserFactory()
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        with pytest.raises(ValueError):
            review.transition_to(
                ManagementReviewStatus.CANCELLED, user, comment="",
            )

    def test_held_sets_held_date(self):
        user = UserFactory()
        review = ManagementReviewFactory(
            status=ManagementReviewStatus.IN_PREPARATION,
            held_date=None,
        )
        review.transition_to(ManagementReviewStatus.HELD, user)
        assert review.held_date == date.today()

    def test_closure_requires_complete_decisions(self):
        user = UserFactory()
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(
            review=review, owner=None, due_date=None,
        )
        ok, reasons = review.can_close()
        assert not ok
        assert len(reasons) >= 1

    def test_closure_ok_when_decisions_complete(self):
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(review=review)
        ok, reasons = review.can_close()
        assert ok
        assert reasons == []

    def test_close_blocked_on_incomplete_decision(self):
        user = UserFactory()
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(
            review=review, owner=None, due_date=None,
        )
        with pytest.raises(ValueError):
            review.transition_to(ManagementReviewStatus.CLOSED, user)

    def test_snapshot_stores_json(self):
        review = ManagementReviewFactory()
        review.take_snapshot({"foo": "bar", "x": 1})
        review.refresh_from_db()
        assert review.snapshot_data == {"foo": "bar", "x": 1}
        assert review.snapshot_taken_at is not None
        assert review.has_snapshot


class TestDecisionModel:

    def test_reference_auto_generated(self):
        d = ManagementReviewDecisionFactory()
        assert d.reference.startswith("DECS-")

    def test_reference_sequential(self):
        d1 = ManagementReviewDecisionFactory()
        d2 = ManagementReviewDecisionFactory()
        n1 = int(d1.reference.split("-")[1])
        n2 = int(d2.reference.split("-")[1])
        assert n2 == n1 + 1


class TestIsmsChangeModel:

    def test_reference_auto_generated(self):
        c = IsmsChangeFactory()
        assert c.reference.startswith("ICHG-")


class TestParticipantModel:

    def test_internal_user_participant_valid(self):
        p = ManagementReviewParticipantFactory()
        assert p.user is not None
        assert p.display_name == str(p.user)

    def test_external_participant_requires_name(self):
        review = ManagementReviewFactory()
        from reports.models import ManagementReviewParticipant
        # Constraint check: user=None AND external_name="" should fail
        with pytest.raises(Exception):
            ManagementReviewParticipant.objects.create(
                review=review, user=None, external_name="",
            )


# ─── View tests ─────────────────────────────────────────────────────


class TestManagementReviewViews:

    def _user_with_perms(self, client, *perms):
        from accounts.tests.factories import GroupFactory, PermissionFactory
        user = UserFactory()
        group = GroupFactory()
        for p in perms:
            perm = PermissionFactory(codename=p)
            group.permissions.add(perm)
        group.users.add(user)
        client.force_login(user)
        return user

    def test_list_view_requires_perm(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.get(reverse("reports:management-review-list"))
        # No permission: should redirect (403 page) or 403
        assert response.status_code in (302, 403)

    def test_list_view_with_perm(self, client):
        self._user_with_perms(client, "reports.management_review.read")
        ManagementReviewFactory.create_batch(3)
        response = client.get(reverse("reports:management-review-list"))
        assert response.status_code == 200

    def test_detail_view(self, client):
        self._user_with_perms(client, "reports.management_review.read")
        review = ManagementReviewFactory()
        response = client.get(
            reverse("reports:management-review-detail", args=[review.pk]),
        )
        assert response.status_code == 200
        assert review.title.encode() in response.content

    def test_transition_view(self, client):
        user = self._user_with_perms(
            client,
            "reports.management_review.read",
            "reports.management_review.update",
        )
        review = ManagementReviewFactory(status=ManagementReviewStatus.PLANNED)
        response = client.post(
            reverse("reports:management-review-transition", args=[review.pk]),
            {"target_status": ManagementReviewStatus.IN_PREPARATION},
        )
        assert response.status_code == 302
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.IN_PREPARATION

    def test_closure_blocked_without_approve_perm(self, client):
        self._user_with_perms(
            client,
            "reports.management_review.read",
            "reports.management_review.update",
        )
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(review=review)
        response = client.post(
            reverse("reports:management-review-transition", args=[review.pk]),
            {"target_status": ManagementReviewStatus.CLOSED},
        )
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.HELD

    def test_closure_creates_snapshot(self, client):
        self._user_with_perms(
            client,
            "reports.management_review.read",
            "reports.management_review.update",
            "reports.management_review.approve",
        )
        review = ManagementReviewFactory(status=ManagementReviewStatus.HELD)
        ManagementReviewDecisionFactory(review=review)
        client.post(
            reverse("reports:management-review-transition", args=[review.pk]),
            {"target_status": ManagementReviewStatus.CLOSED},
        )
        review.refresh_from_db()
        assert review.status == ManagementReviewStatus.CLOSED
        assert review.has_snapshot
        assert review.snapshot_taken_at is not None


class TestDecisionPromote:

    def _user_with_perms(self, client, *perms):
        from accounts.tests.factories import GroupFactory, PermissionFactory
        user = UserFactory()
        group = GroupFactory()
        for p in perms:
            perm = PermissionFactory(codename=p)
            group.permissions.add(perm)
        group.users.add(user)
        client.force_login(user)
        return user

    def test_promote_creates_action_plan(self, client):
        user = self._user_with_perms(
            client,
            "reports.management_review.update",
            "compliance.action_plan.create",
        )
        review = ManagementReviewFactory()
        decision = ManagementReviewDecisionFactory(review=review)

        response = client.post(
            reverse("reports:decision-promote", args=[decision.pk]),
            {
                "name": "Promoted plan",
                "priority": "medium",
                "target_date": (date.today() + timedelta(days=30)).isoformat(),
                "gap_description": "Gap",
                "remediation_plan": "Plan",
                "owner": user.pk,
            },
        )
        assert response.status_code in (302, 200)
        plan = ComplianceActionPlan.objects.first()
        assert plan is not None
        assert plan.originating_review == review
        decision.refresh_from_db()
        assert decision.linked_action_plan == plan


# ─── Indicator trend ────────────────────────────────────────────────


def _build_indicator(**overrides):
    """Helper: build an Indicator directly (no factory available)."""
    from context.tests.factories import ScopeFactory
    defaults = {
        "name": "Test indicator",
        "indicator_type": "organizational",
        "format": "number",
        "review_frequency": "monthly",
        "first_review_date": date.today() + timedelta(days=1),
        "status": "active",
    }
    defaults.update(overrides)
    indicator = Indicator.objects.create(**defaults)
    indicator.scopes.add(ScopeFactory())
    return indicator


def _add_measurement(indicator, value, recorded_at):
    """Create a measurement and force its recorded_at timestamp."""
    m = IndicatorMeasurement.objects.create(indicator=indicator, value=str(value))
    IndicatorMeasurement.objects.filter(pk=m.pk).update(recorded_at=recorded_at)
    m.refresh_from_db()
    return m


class TestIndicatorTrend:

    def test_insufficient_data_returns_default(self):
        indicator = _build_indicator()
        result = _compute_indicator_trend(
            indicator,
            date.today() - timedelta(days=30),
            date.today(),
        )
        assert result["label"] == "insufficient_data"
        assert result["symbol"] == "-"

    def test_improving_trend(self):
        indicator = _build_indicator()
        today = date.today()
        period_start = today - timedelta(days=30)
        # Previous period (days -60 to -31): measurements at value=10
        prev_ts = timezone.make_aware(datetime.combine(today - timedelta(days=45), datetime.min.time()))
        _add_measurement(indicator, 10, prev_ts)
        # Current period (days -30 to 0): measurements at value=20
        cur_ts = timezone.make_aware(datetime.combine(today - timedelta(days=10), datetime.min.time()))
        _add_measurement(indicator, 20, cur_ts)

        result = _compute_indicator_trend(indicator, period_start, today)
        assert result["label"] == "improving"
        assert result["symbol"] == "^"
        assert result["previous_value"] == "10.00"

    def test_degrading_trend(self):
        indicator = _build_indicator()
        today = date.today()
        period_start = today - timedelta(days=30)
        prev_ts = timezone.make_aware(datetime.combine(today - timedelta(days=45), datetime.min.time()))
        _add_measurement(indicator, 100, prev_ts)
        cur_ts = timezone.make_aware(datetime.combine(today - timedelta(days=10), datetime.min.time()))
        _add_measurement(indicator, 50, cur_ts)

        result = _compute_indicator_trend(indicator, period_start, today)
        assert result["label"] == "degrading"
        assert result["symbol"] == "v"

    def test_stable_trend_within_threshold(self):
        indicator = _build_indicator()
        today = date.today()
        period_start = today - timedelta(days=30)
        prev_ts = timezone.make_aware(datetime.combine(today - timedelta(days=45), datetime.min.time()))
        _add_measurement(indicator, 100, prev_ts)
        cur_ts = timezone.make_aware(datetime.combine(today - timedelta(days=10), datetime.min.time()))
        # 102 is within 5% of 100
        _add_measurement(indicator, 102, cur_ts)

        result = _compute_indicator_trend(indicator, period_start, today)
        assert result["label"] == "stable"
        assert result["symbol"] == "="

    def test_measurement_compliance_ratio(self):
        indicator = _build_indicator(review_frequency="weekly")
        today = date.today()
        period_start = today - timedelta(days=30)
        # Expected ~ 4 weekly measurements, we record 2
        for days_ago in (5, 20):
            ts = timezone.make_aware(datetime.combine(today - timedelta(days=days_ago), datetime.min.time()))
            _add_measurement(indicator, 1, ts)
        # Add one previous period measurement so the label isn't insufficient_data
        prev_ts = timezone.make_aware(datetime.combine(today - timedelta(days=45), datetime.min.time()))
        _add_measurement(indicator, 1, prev_ts)

        result = _compute_indicator_trend(indicator, period_start, today)
        # Compliance "recorded/expected" should read "2/4"
        assert result["measurement_compliance"] == "2/4"
