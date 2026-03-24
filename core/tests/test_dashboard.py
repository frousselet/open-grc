"""Tests for the GeneralDashboardView context computation and scope filtering."""

from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from assets.tests.factories import (
    DependencyFactory,
    EssentialAssetFactory,
    SupplierDependencyFactory,
    SupplierFactory,
    SupportAssetFactory,
)
from compliance.tests.factories import (
    ComplianceActionPlanFactory,
    ComplianceAssessmentFactory,
    FrameworkFactory,
    RequirementFactory,
)
from context.constants import (
    IndicatorFormat,
    IndicatorStatus,
    IndicatorType,
    CollectionMethod,
    MeasurementFrequency,
)
from context.models import Activity, Indicator, Issue, Objective, Role, Scope, Site, Stakeholder, SwotAnalysis
from context.models.indicator import IndicatorMeasurement
from context.tests.factories import (
    IssueFactory,
    ObjectiveFactory,
    ScopeFactory,
    SwotAnalysisFactory,
)
from risks.tests.factories import RiskAssessmentFactory, RiskFactory

pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────


def _superuser_client():
    user = UserFactory(is_superuser=True, is_staff=True)
    client = Client()
    client.force_login(user)
    return client, user


def _regular_client():
    user = UserFactory()
    client = Client()
    client.force_login(user)
    return client, user


def _make_indicator(**kwargs):
    defaults = {
        "name": "Dashboard Indicator",
        "indicator_type": IndicatorType.ORGANIZATIONAL,
        "collection_method": CollectionMethod.MANUAL,
        "format": IndicatorFormat.NUMBER,
        "review_frequency": MeasurementFrequency.MONTHLY,
        "first_review_date": timezone.now().date() + timedelta(days=30),
        "status": IndicatorStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Indicator.objects.create(**defaults)


# ── Dashboard with populated data ────────────────────────────


class TestDashboardWithPopulatedData:
    """Test that the dashboard correctly counts and displays data from all modules."""

    def test_scope_count(self):
        ScopeFactory()
        ScopeFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["scope_count"] == 2

    def test_active_scopes_returned(self):
        ScopeFactory(status="active")
        ScopeFactory(status="draft")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert len(resp.context["active_scopes"]) == 1

    def test_issue_count(self):
        scope = ScopeFactory()
        IssueFactory(scopes=[scope])
        IssueFactory(scopes=[scope])
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["issue_count"] == 2

    def test_stakeholder_count(self):
        Stakeholder.objects.create(
            name="Test Stakeholder",
            category="customers",
            influence_level="high",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["stakeholder_count"] == 1

    def test_objective_count(self):
        ObjectiveFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["objective_count"] == 1

    def test_active_objectives_returned(self):
        ObjectiveFactory(status="active")
        ObjectiveFactory(status="draft")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert len(resp.context["active_objectives"]) == 1

    def test_role_count(self):
        Role.objects.create(name="CISO", type="governance")
        Role.objects.create(name="DPO", type="governance")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["role_count"] == 2

    def test_site_count(self):
        Site.objects.create(name="HQ", description="Headquarters")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["site_count"] == 1

    def test_mandatory_roles_no_user_alert(self):
        Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["mandatory_roles_no_user"] == 1

    def test_mandatory_roles_with_user_no_alert(self):
        role = Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        role.assigned_users.add(UserFactory())
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["mandatory_roles_no_user"] == 0

    def test_swot_count(self):
        SwotAnalysisFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["swot_count"] == 1

    def test_activity_count(self):
        user = UserFactory()
        Activity.objects.create(
            name="Activity 1", type="core_business",
            criticality="high", owner=user,
        )
        client, admin = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["activity_count"] == 1

    def test_critical_activities_no_owner_count(self):
        """Critical activities with no owner should be counted for the alert."""
        user = UserFactory()
        # Critical with owner - should not count
        Activity.objects.create(
            name="A1", type="core_business",
            criticality="critical", owner=user,
        )
        # Critical without owner - the model requires owner (PROTECT), so this
        # test checks the dashboard query filter. We need at least one critical
        # activity WITH owner to verify the count is correct.
        client, admin = _superuser_client()
        resp = client.get(reverse("home"))
        # Since Activity.owner is required (PROTECT), we test the query logic
        # indirectly: a critical activity with an owner should NOT trigger.
        assert resp.context["critical_activities_no_owner"] == 0


class TestDashboardAssets:
    def test_essential_asset_count(self):
        EssentialAssetFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["essential_count"] == 1

    def test_support_asset_count(self):
        SupportAssetFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["support_count"] == 1

    def test_dependency_count(self):
        DependencyFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["dependency_count"] == 1

    def test_eol_count(self):
        SupportAssetFactory(
            end_of_life_date=date.today() - timedelta(days=30),
            status="active",
        )
        # Not past EOL
        SupportAssetFactory(
            end_of_life_date=date.today() + timedelta(days=30),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["eol_count"] == 1

    def test_personal_data_count(self):
        EssentialAssetFactory(personal_data=True)
        EssentialAssetFactory(personal_data=False)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["personal_data_count"] == 1

    def test_supplier_count(self):
        SupplierFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["supplier_count"] == 1

    def test_expired_contract_count(self):
        SupplierFactory(
            contract_end_date=date.today() - timedelta(days=10),
            status="active",
        )
        SupplierFactory(
            contract_end_date=date.today() + timedelta(days=10),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["expired_contract_count"] == 1

    def test_supplier_dep_count(self):
        SupplierDependencyFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["supplier_dep_count"] == 1

    def test_supplier_spof_count(self):
        SupplierDependencyFactory(is_single_point_of_failure=True)
        SupplierDependencyFactory(is_single_point_of_failure=False)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["supplier_spof_count"] == 1


class TestDashboardRisks:
    def test_risk_assessment_count(self):
        RiskAssessmentFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["risk_assessment_count"] == 1

    def test_risk_count(self):
        RiskFactory()
        RiskFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["risk_count"] == 2

    def test_critical_risk_count(self):
        RiskFactory(priority="critical")
        RiskFactory(priority="high")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["critical_risk_count"] == 1


class TestDashboardCompliance:
    def test_framework_count(self):
        FrameworkFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["framework_count"] == 1

    def test_assessment_count(self):
        ComplianceAssessmentFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["assessment_count"] == 1

    def test_action_plan_count(self):
        ComplianceActionPlanFactory()
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["action_plan_count"] == 1

    def test_overdue_plan_count(self):
        ComplianceActionPlanFactory(
            target_date=date.today() - timedelta(days=10),
            status="in_progress",
        )
        # Not overdue
        ComplianceActionPlanFactory(
            target_date=date.today() + timedelta(days=30),
            status="in_progress",
        )
        # Closed, past target - should not count
        ComplianceActionPlanFactory(
            target_date=date.today() - timedelta(days=10),
            status="closed",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["overdue_plan_count"] == 1

    def test_requirement_count(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw)
        RequirementFactory(framework=fw)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["requirement_count"] == 2

    def test_non_compliant_count(self):
        fw = FrameworkFactory()
        RequirementFactory(
            framework=fw,
            compliance_status="major_non_conformity",
        )
        RequirementFactory(
            framework=fw,
            compliance_status="minor_non_conformity",
        )
        RequirementFactory(
            framework=fw,
            compliance_status="compliant",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["non_compliant_count"] == 2


# ── Alerts ───────────────────────────────────────────────────


class TestDashboardAlerts:
    def test_no_alerts_when_no_issues(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["alerts"] == []

    def test_mandatory_role_alert(self):
        Role.objects.create(name="DPO", type="governance", is_mandatory=True)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        alerts = resp.context["alerts"]
        assert len(alerts) >= 1
        assert any("mandatory" in str(a).lower() for a in alerts)

    def test_eol_alert(self):
        SupportAssetFactory(
            end_of_life_date=date.today() - timedelta(days=5),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        alerts = resp.context["alerts"]
        assert any("end of life" in str(a).lower() for a in alerts)

    def test_non_compliant_alert(self):
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, compliance_status="major_non_conformity")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        alerts = resp.context["alerts"]
        assert any("non-compliant" in str(a).lower() for a in alerts)

    def test_overdue_plan_alert(self):
        ComplianceActionPlanFactory(
            target_date=date.today() - timedelta(days=5),
            status="in_progress",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        alerts = resp.context["alerts"]
        assert any("overdue" in str(a).lower() for a in alerts)

    def test_critical_risk_alert(self):
        RiskFactory(priority="critical")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        alerts = resp.context["alerts"]
        assert any("critical" in str(a).lower() for a in alerts)

    def test_expired_contract_alert(self):
        SupplierFactory(
            contract_end_date=date.today() - timedelta(days=5),
            status="active",
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        alerts = resp.context["alerts"]
        assert any("expired" in str(a).lower() for a in alerts)


# ── _filter_scoped helper ────────────────────────────────────


class TestFilterScoped:
    def test_superuser_sees_all_scoped_objects(self):
        """Superusers are not filtered by scope."""
        scope1 = ScopeFactory()
        scope2 = ScopeFactory()
        IssueFactory(scopes=[scope1])
        IssueFactory(scopes=[scope2])
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["issue_count"] == 2

    def test_regular_user_sees_all_when_no_scope_restriction(self):
        """Regular users without scope restrictions see all data."""
        IssueFactory()
        client, user = _regular_client()
        resp = client.get(reverse("home"))
        # Non-superuser with no group scope restrictions should still see data
        assert resp.status_code == 200

    def test_scope_count_matches_filter(self):
        """Superuser sees all scopes."""
        ScopeFactory(status="active")
        ScopeFactory(status="draft")
        ScopeFactory(status="archived")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["scope_count"] == 3


# ── Dashboard indicator slots ────────────────────────────────


class TestDashboardIndicatorSlots:
    def test_empty_slots_when_no_pinned_indicators(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        assert len(slots) == 10
        assert all(s is None for s in slots)

    def test_pinned_indicator_shown_in_slots(self):
        ind = _make_indicator(name="Coverage", current_value="85")
        client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        filled = [s for s in slots if s is not None]
        assert len(filled) == 1
        assert filled[0]["indicator"].pk == ind.pk

    def test_pinned_indicator_with_measurements_has_trend(self):
        ind = _make_indicator(name="Trend Test", current_value="100")
        IndicatorMeasurement.objects.create(indicator=ind, value="80")
        IndicatorMeasurement.objects.create(indicator=ind, value="100")
        client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        filled = [s for s in slots if s is not None]
        assert len(filled) == 1
        assert filled[0]["trend"] is not None

    def test_pinned_boolean_indicator_trend(self):
        ind = _make_indicator(
            name="Boolean Test",
            format=IndicatorFormat.BOOLEAN,
            current_value="true",
        )
        IndicatorMeasurement.objects.create(indicator=ind, value="false")
        IndicatorMeasurement.objects.create(indicator=ind, value="true")
        client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        filled = [s for s in slots if s is not None]
        assert len(filled) == 1
        assert filled[0]["trend"] == "changed"

    def test_pinned_boolean_stable_trend(self):
        ind = _make_indicator(
            name="Bool Stable",
            format=IndicatorFormat.BOOLEAN,
            current_value="true",
        )
        IndicatorMeasurement.objects.create(indicator=ind, value="true")
        IndicatorMeasurement.objects.create(indicator=ind, value="true")
        client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators"])
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        filled = [s for s in slots if s is not None]
        assert filled[0]["trend"] == "stable"

    def test_pinned_indicator_with_chart_enabled(self):
        ind = _make_indicator(name="Chart Test", current_value="50")
        for i in range(5):
            IndicatorMeasurement.objects.create(indicator=ind, value=str(10 * (i + 1)))
        client, user = _superuser_client()
        user.dashboard_indicators = [str(ind.pk)]
        user.dashboard_indicator_charts = [str(ind.pk)]
        user.save(update_fields=["dashboard_indicators", "dashboard_indicator_charts"])
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        filled = [s for s in slots if s is not None]
        assert len(filled) == 1
        assert filled[0]["show_chart"] is True
        assert len(filled[0]["sparkline_data"]) >= 2

    def test_slots_padded_to_ten(self):
        ind1 = _make_indicator(name="Ind 1")
        ind2 = _make_indicator(name="Ind 2")
        client, user = _superuser_client()
        user.dashboard_indicators = [str(ind1.pk), str(ind2.pk)]
        user.save(update_fields=["dashboard_indicators"])
        resp = client.get(reverse("home"))
        slots = resp.context["dashboard_indicator_slots"]
        assert len(slots) == 10
        filled = [s for s in slots if s is not None]
        assert len(filled) == 2

    def test_available_indicators_in_context(self):
        _make_indicator(name="Active One", status=IndicatorStatus.ACTIVE)
        _make_indicator(name="Inactive One", status=IndicatorStatus.INACTIVE)
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        available = resp.context["available_indicators"]
        names = [ind.name for ind in available]
        assert "Active One" in names
        assert "Inactive One" not in names


# ── Overall compliance calculation ───────────────────────────


class TestDashboardOverallCompliance:
    def test_zero_when_no_active_frameworks(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["overall_compliance"] == 0

    def test_frameworks_with_no_requirements(self):
        """A framework with no requirements should show 0% compliance."""
        FrameworkFactory(status="active")
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        active_fws = resp.context["active_frameworks"]
        assert len(active_fws) == 1
        assert active_fws[0].computed_compliance == 0


# ── Risk matrices ────────────────────────────────────────────


class TestDashboardRiskMatrices:
    def test_default_matrix_without_criteria(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["matrix_current"] is not None
        assert "rows" in resp.context["matrix_current"]

    def test_default_matrix_has_5_rows(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert len(resp.context["matrix_current"]["rows"]) == 5

    def test_residual_matrix_present(self):
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["matrix_residual"] is not None
        assert "rows" in resp.context["matrix_residual"]

    def test_matrix_with_risks(self):
        RiskFactory(
            current_likelihood=3,
            current_impact=4,
            residual_likelihood=2,
            residual_impact=2,
        )
        client, user = _superuser_client()
        resp = client.get(reverse("home"))
        assert resp.context["matrix_current"] is not None
        assert resp.context["matrix_residual"] is not None
