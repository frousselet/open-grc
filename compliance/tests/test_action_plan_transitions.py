import pytest
from django.utils import timezone

from accounts.tests.factories import UserFactory
from compliance.constants import (
    ACTION_PLAN_TRANSITIONS,
    ActionPlanStatus,
)
from compliance.models import ActionPlanTransition, ComplianceActionPlan
from compliance.tests.factories import ComplianceActionPlanFactory

pytestmark = pytest.mark.django_db


class TestActionPlanTransitions:
    """Test the action plan state machine."""

    def test_new_to_to_define(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        ap.transition_to(ActionPlanStatus.TO_DEFINE, user)
        assert ap.status == ActionPlanStatus.TO_DEFINE

    def test_to_define_to_to_validate(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_DEFINE)
        ap.transition_to(ActionPlanStatus.TO_VALIDATE, user)
        assert ap.status == ActionPlanStatus.TO_VALIDATE

    def test_to_validate_to_to_implement(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        ap.transition_to(ActionPlanStatus.TO_IMPLEMENT, user)
        assert ap.status == ActionPlanStatus.TO_IMPLEMENT

    def test_to_implement_to_implementation_to_validate(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_IMPLEMENT)
        ap.transition_to(ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE, user)
        assert ap.status == ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE

    def test_implementation_to_validate_to_validated(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(
            status=ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE
        )
        ap.transition_to(ActionPlanStatus.VALIDATED, user)
        assert ap.status == ActionPlanStatus.VALIDATED

    def test_validated_to_closed(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.VALIDATED)
        ap.transition_to(ActionPlanStatus.CLOSED, user)
        assert ap.status == ActionPlanStatus.CLOSED
        assert ap.completion_date == timezone.now().date()
        assert ap.progress_percentage == 100

    def test_full_forward_workflow(self):
        """Test the complete happy path from New to Closed."""
        user = UserFactory()
        ap = ComplianceActionPlanFactory()
        statuses = [
            ActionPlanStatus.TO_DEFINE,
            ActionPlanStatus.TO_VALIDATE,
            ActionPlanStatus.TO_IMPLEMENT,
            ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE,
            ActionPlanStatus.VALIDATED,
            ActionPlanStatus.CLOSED,
        ]
        for status in statuses:
            ap.transition_to(status, user)
        assert ap.status == ActionPlanStatus.CLOSED
        assert ap.transitions.count() == 6

    def test_invalid_transition_raises(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.CLOSED, user)

    def test_invalid_skip_transition(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.TO_VALIDATE, user)


class TestRefusalTransitions:
    """Test backward (refusal) transitions."""

    def test_refusal_to_validate_to_to_define_with_comment(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        ap.transition_to(ActionPlanStatus.TO_DEFINE, user, "Needs more detail")
        assert ap.status == ActionPlanStatus.TO_DEFINE
        t = ap.transitions.first()
        assert t.is_refusal is True
        assert t.comment == "Needs more detail"

    def test_refusal_implementation_to_validate_to_to_implement(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(
            status=ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE
        )
        ap.transition_to(
            ActionPlanStatus.TO_IMPLEMENT, user, "Implementation incomplete"
        )
        assert ap.status == ActionPlanStatus.TO_IMPLEMENT
        t = ap.transitions.first()
        assert t.is_refusal is True

    def test_refusal_without_comment_raises(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        with pytest.raises(ValueError, match="comment is required"):
            ap.transition_to(ActionPlanStatus.TO_DEFINE, user, "")

    def test_refusal_with_whitespace_only_raises(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        with pytest.raises(ValueError, match="comment is required"):
            ap.transition_to(ActionPlanStatus.TO_DEFINE, user, "   ")


class TestCancellation:
    """Test cancellation from any non-terminal state."""

    @pytest.mark.parametrize(
        "initial_status",
        [
            ActionPlanStatus.NEW,
            ActionPlanStatus.TO_DEFINE,
            ActionPlanStatus.TO_VALIDATE,
            ActionPlanStatus.TO_IMPLEMENT,
            ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE,
            ActionPlanStatus.VALIDATED,
        ],
    )
    def test_cancellation_from_any_state(self, initial_status):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=initial_status)
        ap.transition_to(ActionPlanStatus.CANCELLED, user)
        assert ap.status == ActionPlanStatus.CANCELLED

    def test_cannot_cancel_from_closed(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CLOSED)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.CANCELLED, user)

    def test_cannot_cancel_from_cancelled(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CANCELLED)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.CANCELLED, user)


class TestTransitionAuditTrail:
    """Test that transitions create proper audit records."""

    def test_transition_creates_record(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory()
        ap.transition_to(ActionPlanStatus.TO_DEFINE, user)
        assert ActionPlanTransition.objects.count() == 1
        t = ActionPlanTransition.objects.first()
        assert t.from_status == ActionPlanStatus.NEW
        assert t.to_status == ActionPlanStatus.TO_DEFINE
        assert t.performed_by == user
        assert t.is_refusal is False

    def test_transition_records_ordered_by_date(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory()
        ap.transition_to(ActionPlanStatus.TO_DEFINE, user)
        ap.transition_to(ActionPlanStatus.TO_VALIDATE, user)
        transitions = list(ap.transitions.all())
        assert transitions[0].to_status == ActionPlanStatus.TO_VALIDATE
        assert transitions[1].to_status == ActionPlanStatus.TO_DEFINE


class TestGetAllowedTransitions:
    """Test get_allowed_transitions method."""

    def test_new_allowed(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NEW)
        allowed = ap.get_allowed_transitions()
        assert ActionPlanStatus.TO_DEFINE in allowed
        assert ActionPlanStatus.CANCELLED in allowed

    def test_closed_has_no_transitions(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CLOSED)
        assert ap.get_allowed_transitions() == []

    def test_cancelled_has_no_transitions(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CANCELLED)
        assert ap.get_allowed_transitions() == []

    def test_to_validate_includes_refusal(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        allowed = ap.get_allowed_transitions()
        assert ActionPlanStatus.TO_IMPLEMENT in allowed
        assert ActionPlanStatus.TO_DEFINE in allowed
        assert ActionPlanStatus.CANCELLED in allowed
