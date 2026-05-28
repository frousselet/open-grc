"""Tests for the management commands that drive the risks lifecycle:

- expire_risk_acceptances : flip ACTIVE acceptances past valid_until to EXPIRED
- mark_overdue_treatment_plans : flip in-flight plans past target_date to OVERDUE
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from risks.constants import AcceptanceStatus, TreatmentPlanStatus
from risks.models import RiskAcceptance, RiskTreatmentPlan
from risks.tests.factories import (
    RiskAcceptanceFactory,
    RiskFactory,
    RiskTreatmentPlanFactory,
)


pytestmark = pytest.mark.django_db


# ── expire_risk_acceptances ───────────────────────────────────


class TestExpireRiskAcceptances:
    def test_expires_past_active_acceptances(self):
        today = timezone.localdate()
        risk = RiskFactory()
        past = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.ACTIVE,
            valid_until=today - timedelta(days=1),
        )
        out = StringIO()
        call_command("expire_risk_acceptances", stdout=out)
        past.refresh_from_db()
        assert past.status == AcceptanceStatus.EXPIRED
        assert "Expired 1 acceptance" in out.getvalue()

    def test_leaves_future_acceptances_active(self):
        today = timezone.localdate()
        risk = RiskFactory()
        future = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.ACTIVE,
            valid_until=today + timedelta(days=10),
        )
        call_command("expire_risk_acceptances", stdout=StringIO())
        future.refresh_from_db()
        assert future.status == AcceptanceStatus.ACTIVE

    def test_does_not_touch_already_revoked_or_renewed(self):
        today = timezone.localdate()
        risk = RiskFactory()
        revoked = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.REVOKED,
            valid_until=today - timedelta(days=5),
        )
        renewed = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.RENEWED,
            valid_until=today - timedelta(days=5),
        )
        call_command("expire_risk_acceptances", stdout=StringIO())
        revoked.refresh_from_db()
        renewed.refresh_from_db()
        assert revoked.status == AcceptanceStatus.REVOKED
        assert renewed.status == AcceptanceStatus.RENEWED

    def test_ignores_acceptances_without_valid_until(self):
        risk = RiskFactory()
        perpetual = RiskAcceptanceFactory(
            risk=risk, status=AcceptanceStatus.ACTIVE, valid_until=None,
        )
        call_command("expire_risk_acceptances", stdout=StringIO())
        perpetual.refresh_from_db()
        assert perpetual.status == AcceptanceStatus.ACTIVE

    def test_lists_upcoming_expirations(self):
        today = timezone.localdate()
        risk = RiskFactory()
        soon = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.ACTIVE,
            valid_until=today + timedelta(days=5),
        )
        far = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.ACTIVE,
            valid_until=today + timedelta(days=60),
        )
        out = StringIO()
        call_command(
            "expire_risk_acceptances", "--reminder-days", "30", stdout=out,
        )
        output = out.getvalue()
        assert soon.reference in output
        assert far.reference not in output

    def test_dry_run_does_not_write(self):
        today = timezone.localdate()
        risk = RiskFactory()
        past = RiskAcceptanceFactory(
            risk=risk,
            status=AcceptanceStatus.ACTIVE,
            valid_until=today - timedelta(days=1),
        )
        out = StringIO()
        call_command("expire_risk_acceptances", "--dry-run", stdout=out)
        past.refresh_from_db()
        assert past.status == AcceptanceStatus.ACTIVE
        assert "Would expire" in out.getvalue()


# ── mark_overdue_treatment_plans ──────────────────────────────


class TestMarkOverdueTreatmentPlans:
    def test_marks_past_target_as_overdue(self):
        today = timezone.localdate()
        plan = RiskTreatmentPlanFactory(
            target_date=today - timedelta(days=1),
            status=TreatmentPlanStatus.IN_PROGRESS,
        )
        out = StringIO()
        call_command("mark_overdue_treatment_plans", stdout=out)
        plan.refresh_from_db()
        assert plan.status == TreatmentPlanStatus.OVERDUE
        assert "Marked 1 treatment plan" in out.getvalue()

    def test_leaves_future_target_alone(self):
        today = timezone.localdate()
        plan = RiskTreatmentPlanFactory(
            target_date=today + timedelta(days=10),
            status=TreatmentPlanStatus.PLANNED,
        )
        call_command("mark_overdue_treatment_plans", stdout=StringIO())
        plan.refresh_from_db()
        assert plan.status == TreatmentPlanStatus.PLANNED

    def test_does_not_touch_completed_or_cancelled(self):
        today = timezone.localdate()
        done = RiskTreatmentPlanFactory(
            target_date=today - timedelta(days=5),
            status=TreatmentPlanStatus.COMPLETED,
        )
        cancelled = RiskTreatmentPlanFactory(
            target_date=today - timedelta(days=5),
            status=TreatmentPlanStatus.CANCELLED,
        )
        call_command("mark_overdue_treatment_plans", stdout=StringIO())
        done.refresh_from_db()
        cancelled.refresh_from_db()
        assert done.status == TreatmentPlanStatus.COMPLETED
        assert cancelled.status == TreatmentPlanStatus.CANCELLED

    def test_is_idempotent(self):
        today = timezone.localdate()
        plan = RiskTreatmentPlanFactory(
            target_date=today - timedelta(days=2),
            status=TreatmentPlanStatus.PLANNED,
        )
        call_command("mark_overdue_treatment_plans", stdout=StringIO())
        plan.refresh_from_db()
        first_updated_at = plan.updated_at
        out = StringIO()
        call_command("mark_overdue_treatment_plans", stdout=out)
        plan.refresh_from_db()
        assert plan.status == TreatmentPlanStatus.OVERDUE
        assert plan.updated_at == first_updated_at
        assert "Marked 0 treatment plan" in out.getvalue()

    def test_ignores_plans_without_target_date(self):
        plan = RiskTreatmentPlanFactory(
            target_date=None,
            status=TreatmentPlanStatus.PLANNED,
        )
        call_command("mark_overdue_treatment_plans", stdout=StringIO())
        plan.refresh_from_db()
        assert plan.status == TreatmentPlanStatus.PLANNED

    def test_dry_run_does_not_write(self):
        today = timezone.localdate()
        plan = RiskTreatmentPlanFactory(
            target_date=today - timedelta(days=1),
            status=TreatmentPlanStatus.IN_PROGRESS,
        )
        out = StringIO()
        call_command("mark_overdue_treatment_plans", "--dry-run", stdout=out)
        plan.refresh_from_db()
        assert plan.status == TreatmentPlanStatus.IN_PROGRESS
        assert "Would mark" in out.getvalue()
