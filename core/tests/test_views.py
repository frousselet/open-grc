import json
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.constants import ActionPlanStatus
from compliance.tests.factories import ComplianceActionPlanFactory
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


# ── Helper ──────────────────────────────────────────────────


def _superuser_client():
    """Return (client, user) where user is a logged-in superuser."""
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


def _authenticated_client():
    """Return (client, user) where user is a regular logged-in user."""
    user = UserFactory()
    client = Client()
    client.force_login(user)
    return client, user


# ── Anonymous access redirects ──────────────────────────────


class TestAnonymousRedirects:
    """All views behind LoginRequiredMixin must redirect anonymous users."""

    def test_dashboard_redirects_anonymous(self):
        resp = Client().get(reverse("home"))
        assert resp.status_code == 302
        assert "/accounts/" in resp.url or "/login" in resp.url.lower()

    def test_calendar_redirects_anonymous(self):
        resp = Client().get(reverse("calendar"))
        assert resp.status_code == 302

    def test_calendar_subscribe_get_redirects_anonymous(self):
        resp = Client().get(reverse("calendar-subscribe"))
        assert resp.status_code == 302

    def test_calendar_subscribe_post_redirects_anonymous(self):
        resp = Client().post(reverse("calendar-subscribe"), {"action": "create"})
        assert resp.status_code == 302

    def test_calendar_events_redirects_anonymous(self):
        resp = Client().get(reverse("calendar-events"))
        assert resp.status_code == 302

    def test_global_search_redirects_anonymous(self):
        resp = Client().get(reverse("global-search"), {"q": "test"})
        assert resp.status_code == 302


# ── Dashboard ───────────────────────────────────────────────


class TestGeneralDashboardView:
    def test_dashboard_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.status_code == 200

    def test_dashboard_contains_key_context_variables(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        ctx = resp.context
        # Governance context
        assert "scope_count" in ctx
        assert "issue_count" in ctx
        assert "stakeholder_count" in ctx
        assert "objective_count" in ctx
        assert "role_count" in ctx
        assert "site_count" in ctx
        # Assets context
        assert "essential_count" in ctx
        assert "support_count" in ctx
        # Risk context
        assert "risk_assessment_count" in ctx
        assert "risk_count" in ctx
        assert "threat_count" in ctx
        assert "vulnerability_count" in ctx
        # Compliance context
        assert "framework_count" in ctx
        assert "assessment_count" in ctx
        assert "action_plan_count" in ctx
        # Today's actions
        assert "today_action_groups" in ctx
        assert "today_action_count" in ctx
        # Risk matrices
        assert "matrix_current" in ctx
        assert "matrix_residual" in ctx

    def test_dashboard_works_for_regular_user(self):
        client, user = _authenticated_client()
        # Regular users can access the dashboard; scope filtering
        # is handled internally via Group.allowed_scopes.
        resp = client.get(reverse("home"))
        assert resp.status_code == 200

    def test_dashboard_zero_counts_when_empty(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        ctx = resp.context
        assert ctx["scope_count"] == 0
        assert ctx["risk_count"] == 0
        assert ctx["framework_count"] == 0
        assert ctx["essential_count"] == 0

    def test_dashboard_overall_compliance_zero_when_no_frameworks(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["overall_compliance"] == 0

    def test_dashboard_default_risk_matrices_present(self):
        """When no RiskCriteria exist, default 5x5 matrices should be built."""
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        matrix = resp.context["matrix_current"]
        assert matrix is not None
        assert "rows" in matrix
        assert len(matrix["rows"]) == 5  # 5x5 default


# ── Dashboard Indicators Partial ────────────────────────────


class TestDashboardIndicatorsPartialView:
    def test_loads_200(self):
        client, _ = _superuser_client()
        resp = client.get(reverse("dashboard-indicators-partial"))
        assert resp.status_code == 200

    def test_anonymous_redirect(self):
        resp = Client().get(reverse("dashboard-indicators-partial"))
        assert resp.status_code == 302


# ── Calendar ────────────────────────────────────────────────


class TestCalendarView:
    def test_calendar_loads_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("calendar"))
        assert resp.status_code == 200

    def test_calendar_uses_correct_template(self):
        client, user = _superuser_client()
        resp = client.get(reverse("calendar"))
        templates = [t.name for t in resp.templates]
        assert "calendar.html" in templates


# ── Calendar Events API ─────────────────────────────────────


class TestCalendarEventsView:
    def test_returns_json(self):
        client, user = _superuser_client()
        resp = client.get(reverse("calendar-events"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"

    def test_returns_list(self):
        client, user = _superuser_client()
        resp = client.get(reverse("calendar-events"))
        data = json.loads(resp.content)
        assert isinstance(data, list)

    def test_empty_when_no_data(self):
        client, user = _superuser_client()
        resp = client.get(reverse("calendar-events"))
        data = json.loads(resp.content)
        assert data == []

    def test_accepts_date_range_params(self):
        client, user = _superuser_client()
        resp = client.get(
            reverse("calendar-events"),
            {"start": "2025-01-01", "end": "2025-12-31"},
        )
        assert resp.status_code == 200

    def test_accepts_categories_param(self):
        client, user = _superuser_client()
        resp = client.get(
            reverse("calendar-events"),
            {"categories": ["scope", "risk_assessment"]},
        )
        assert resp.status_code == 200


# ── Calendar Upcoming API ───────────────────────────────────


class TestCalendarUpcomingView:
    """Upcoming-deadlines feed: next-milestone dates, never negative day counts.

    Regression tests for issue #112: the old client-side list used the
    range start of in-progress plans and showed "in -131 days".
    """

    def _items(self, client, **params):
        resp = client.get(reverse("calendar-upcoming"), params)
        assert resp.status_code == 200
        return json.loads(resp.content)["items"]

    def test_empty_without_data(self):
        client, user = _superuser_client()
        assert self._items(client) == []

    def test_in_progress_range_shows_target_not_start(self):
        """A plan started 131 days ago shows its target date as the milestone."""
        today = timezone.now().date()
        ComplianceActionPlanFactory(
            start_date=today - timedelta(days=131),
            target_date=today + timedelta(days=10),
            status=ActionPlanStatus.TO_IMPLEMENT,
        )
        client, user = _superuser_client()
        items = self._items(client)
        assert len(items) == 1
        assert items[0]["due"] == (today + timedelta(days=10)).isoformat()
        assert items[0]["days_left"] == 10
        assert items[0]["overdue"] is False

    def test_not_started_range_shows_start(self):
        today = timezone.now().date()
        ComplianceActionPlanFactory(
            start_date=today + timedelta(days=5),
            target_date=today + timedelta(days=25),
            status=ActionPlanStatus.TO_IMPLEMENT,
        )
        client, user = _superuser_client()
        items = self._items(client)
        assert len(items) == 1
        assert items[0]["due"] == (today + timedelta(days=5)).isoformat()
        assert items[0]["days_left"] == 5

    def test_past_due_plan_flagged_overdue(self):
        today = timezone.now().date()
        ComplianceActionPlanFactory(
            start_date=today - timedelta(days=72),
            target_date=today - timedelta(days=5),
            status=ActionPlanStatus.TO_IMPLEMENT,
        )
        client, user = _superuser_client()
        items = self._items(client)
        assert len(items) == 1
        assert items[0]["overdue"] is True
        assert items[0]["due"] == (today - timedelta(days=5)).isoformat()

    def test_never_a_negative_day_count_without_overdue_flag(self):
        today = timezone.now().date()
        for delta_start, delta_target in [(-131, 10), (-88, 2), (-72, -5), (3, 20)]:
            ComplianceActionPlanFactory(
                start_date=today + timedelta(days=delta_start),
                target_date=today + timedelta(days=delta_target),
                status=ActionPlanStatus.TO_IMPLEMENT,
            )
        client, user = _superuser_client()
        items = self._items(client)
        assert len(items) == 4
        for item in items:
            assert item["overdue"] or item["days_left"] >= 0

    def test_sorted_by_milestone_date(self):
        today = timezone.now().date()
        # Created in reverse milestone order: started long ago but due in
        # 20 days, vs starting in 2 days. Sorting on the raw range start
        # would rank the first one on top.
        ComplianceActionPlanFactory(
            start_date=today - timedelta(days=131),
            target_date=today + timedelta(days=20),
            status=ActionPlanStatus.TO_IMPLEMENT,
        )
        ComplianceActionPlanFactory(
            start_date=today + timedelta(days=2),
            target_date=today + timedelta(days=25),
            status=ActionPlanStatus.TO_IMPLEMENT,
        )
        client, user = _superuser_client()
        items = self._items(client)
        assert [i["days_left"] for i in items] == [2, 20]

    def test_concluded_items_excluded(self):
        today = timezone.now().date()
        ComplianceActionPlanFactory(
            start_date=today - timedelta(days=60),
            target_date=today - timedelta(days=5),
            status=ActionPlanStatus.CLOSED,
        )
        client, user = _superuser_client()
        assert self._items(client) == []

    def test_respects_categories_filter(self):
        today = timezone.now().date()
        ComplianceActionPlanFactory(
            start_date=today - timedelta(days=10),
            target_date=today + timedelta(days=10),
            status=ActionPlanStatus.TO_IMPLEMENT,
        )
        client, user = _superuser_client()
        assert len(self._items(client, categories="action_plan")) == 1
        assert self._items(client, categories="scope") == []


# ── Calendar Subscribe ──────────────────────────────────────


class TestCalendarSubscribeView:
    def test_get_returns_200(self):
        client, user = _superuser_client()
        resp = client.get(reverse("calendar-subscribe"))
        assert resp.status_code == 200

    def test_create_token(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("calendar-subscribe"),
            {"action": "create", "name": "My Subscription"},
        )
        assert resp.status_code == 200
        assert user.calendar_tokens.count() == 1
        token = user.calendar_tokens.first()
        assert token.name == "My Subscription"

    def test_create_token_default_name(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("calendar-subscribe"),
            {"action": "create", "name": ""},
        )
        assert resp.status_code == 200
        assert user.calendar_tokens.count() == 1

    def test_revoke_token(self):
        client, user = _superuser_client()
        # First create a token
        client.post(
            reverse("calendar-subscribe"),
            {"action": "create", "name": "To Revoke"},
        )
        token = user.calendar_tokens.first()
        # Now revoke it
        resp = client.post(
            reverse("calendar-subscribe"),
            {"action": "revoke", "token_id": str(token.pk)},
        )
        assert resp.status_code == 200
        assert user.calendar_tokens.count() == 0

    def test_context_contains_new_token_on_create(self):
        client, user = _superuser_client()
        resp = client.post(
            reverse("calendar-subscribe"),
            {"action": "create", "name": "Test Token"},
        )
        assert "new_token" in resp.context
        assert resp.context["new_token"] is not None


# ── iCal Feed ───────────────────────────────────────────────


class TestICalFeedView:
    def test_returns_401_without_auth(self):
        resp = Client().get(reverse("calendar-ical"))
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp

    def test_returns_401_with_invalid_basic_auth(self):
        import base64

        creds = base64.b64encode(b"bad@email.com:not-a-uuid").decode()
        resp = Client().get(
            reverse("calendar-ical"),
            HTTP_AUTHORIZATION=f"Basic {creds}",
        )
        assert resp.status_code == 401


# ── Global Search ───────────────────────────────────────────


class TestGlobalSearchView:
    def test_returns_json(self):
        client, user = _superuser_client()
        resp = client.get(reverse("global-search"), {"q": "test"})
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"

    def test_returns_results_key(self):
        client, user = _superuser_client()
        resp = client.get(reverse("global-search"), {"q": "test"})
        data = json.loads(resp.content)
        assert "results" in data

    def test_short_query_returns_navigation_and_actions(self):
        """Queries shorter than 2 characters fall back to navigation + actions."""
        client, user = _superuser_client()
        resp = client.get(reverse("global-search"), {"q": "a"})
        data = json.loads(resp.content)
        labels = {g["label"] for g in data["results"]}
        assert "Navigation" in labels
        # Actions group is gated by per-entry permissions, superuser sees them all
        assert "Actions" in labels

    def test_empty_query_returns_navigation_and_actions(self):
        client, user = _superuser_client()
        resp = client.get(reverse("global-search"), {"q": ""})
        data = json.loads(resp.content)
        labels = {g["label"] for g in data["results"]}
        assert "Navigation" in labels
        assert "Actions" in labels

    def test_no_query_param_returns_navigation_and_actions(self):
        client, user = _superuser_client()
        resp = client.get(reverse("global-search"))
        data = json.loads(resp.content)
        labels = {g["label"] for g in data["results"]}
        assert "Navigation" in labels
        assert "Actions" in labels

    def test_actions_filtered_by_permissions_for_regular_user(self):
        """A regular user without create perms only sees the styleguide action."""
        client, user = _authenticated_client()
        resp = client.get(reverse("global-search"))
        data = json.loads(resp.content)
        actions = next((g for g in data["results"] if g["label"] == "Actions"), None)
        assert actions is not None
        titles = {item["title"] for item in actions["items"]}
        # Styleguide is permission-free, the create actions require permissions
        assert "Open styleguide" in titles
        for create_label in ["Create a risk", "Create an action plan"]:
            assert create_label not in titles

    def test_navigation_labels_follow_request_language(self):
        """Navigation entries are lazy: a French request gets French labels.

        Regression test: NAVIGATION_ENTRIES is a class attribute, so plain
        gettext would freeze the import-time language forever.
        """
        client, user = _superuser_client()
        resp = client.get(reverse("global-search"), {"q": ""}, headers={"accept-language": "fr"})
        data = json.loads(resp.content)
        nav = next(g for g in data["results"] if g["label"] == "Navigation")
        titles = {item["title"] for item in nav["items"]}
        assert "Tableau de bord" in titles
        # And an English request still gets English labels.
        resp = client.get(reverse("global-search"), {"q": ""}, headers={"accept-language": "en"})
        data = json.loads(resp.content)
        nav = next(g for g in data["results"] if g["label"] == "Navigation")
        titles = {item["title"] for item in nav["items"]}
        assert "Dashboard" in titles

    def test_search_finds_scope(self):
        client, user = _superuser_client()
        scope = ScopeFactory(name="UniqueSearchTerm")
        resp = client.get(reverse("global-search"), {"q": "UniqueSearchTerm"})
        data = json.loads(resp.content)
        assert len(data["results"]) > 0
        # Find the scopes category
        scope_results = [
            g for g in data["results"]
            if any("UniqueSearchTerm" in item["title"] for item in g["items"])
        ]
        assert len(scope_results) > 0

    def test_search_returns_grouped_results(self):
        """Results should be grouped by category with label, icon, items."""
        client, user = _superuser_client()
        ScopeFactory(name="SearchableScope")
        resp = client.get(reverse("global-search"), {"q": "SearchableScope"})
        data = json.loads(resp.content)
        for group in data["results"]:
            assert "label" in group
            assert "icon" in group
            assert "items" in group
            for item in group["items"]:
                assert "title" in item
                assert "url" in item
                assert "icon" in item

    def test_search_respects_max_per_category(self):
        """Each category should return at most MAX_PER_CATEGORY results."""
        client, user = _superuser_client()
        for i in range(10):
            ScopeFactory(name=f"BulkScope{i}")
        resp = client.get(reverse("global-search"), {"q": "BulkScope"})
        data = json.loads(resp.content)
        for group in data["results"]:
            assert len(group["items"]) <= 5
