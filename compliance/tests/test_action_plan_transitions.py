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

    def test_nouveau_to_a_definir(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NOUVEAU)
        ap.transition_to(ActionPlanStatus.A_DEFINIR, user)
        assert ap.status == ActionPlanStatus.A_DEFINIR

    def test_a_definir_to_a_valider(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_DEFINIR)
        ap.transition_to(ActionPlanStatus.A_VALIDER, user)
        assert ap.status == ActionPlanStatus.A_VALIDER

    def test_a_valider_to_a_implementer(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_VALIDER)
        ap.transition_to(ActionPlanStatus.A_IMPLEMENTER, user)
        assert ap.status == ActionPlanStatus.A_IMPLEMENTER

    def test_a_implementer_to_implementation_a_valider(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_IMPLEMENTER)
        ap.transition_to(ActionPlanStatus.IMPLEMENTATION_A_VALIDER, user)
        assert ap.status == ActionPlanStatus.IMPLEMENTATION_A_VALIDER

    def test_implementation_a_valider_to_valide(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(
            status=ActionPlanStatus.IMPLEMENTATION_A_VALIDER
        )
        ap.transition_to(ActionPlanStatus.VALIDE, user)
        assert ap.status == ActionPlanStatus.VALIDE

    def test_valide_to_cloture(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.VALIDE)
        ap.transition_to(ActionPlanStatus.CLOTURE, user)
        assert ap.status == ActionPlanStatus.CLOTURE
        assert ap.completion_date == timezone.now().date()
        assert ap.progress_percentage == 100

    def test_full_forward_workflow(self):
        """Test the complete happy path from Nouveau to Clôturé."""
        user = UserFactory()
        ap = ComplianceActionPlanFactory()
        statuses = [
            ActionPlanStatus.A_DEFINIR,
            ActionPlanStatus.A_VALIDER,
            ActionPlanStatus.A_IMPLEMENTER,
            ActionPlanStatus.IMPLEMENTATION_A_VALIDER,
            ActionPlanStatus.VALIDE,
            ActionPlanStatus.CLOTURE,
        ]
        for status in statuses:
            ap.transition_to(status, user)
        assert ap.status == ActionPlanStatus.CLOTURE
        assert ap.transitions.count() == 6

    def test_invalid_transition_raises(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NOUVEAU)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.CLOTURE, user)

    def test_invalid_skip_transition(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NOUVEAU)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.A_VALIDER, user)


class TestRefusalTransitions:
    """Test backward (refusal) transitions."""

    def test_refusal_a_valider_to_a_definir_with_comment(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_VALIDER)
        ap.transition_to(ActionPlanStatus.A_DEFINIR, user, "Needs more detail")
        assert ap.status == ActionPlanStatus.A_DEFINIR
        t = ap.transitions.first()
        assert t.is_refusal is True
        assert t.comment == "Needs more detail"

    def test_refusal_implementation_a_valider_to_a_implementer(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(
            status=ActionPlanStatus.IMPLEMENTATION_A_VALIDER
        )
        ap.transition_to(
            ActionPlanStatus.A_IMPLEMENTER, user, "Implementation incomplete"
        )
        assert ap.status == ActionPlanStatus.A_IMPLEMENTER
        t = ap.transitions.first()
        assert t.is_refusal is True

    def test_refusal_without_comment_raises(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_VALIDER)
        with pytest.raises(ValueError, match="comment is required"):
            ap.transition_to(ActionPlanStatus.A_DEFINIR, user, "")

    def test_refusal_with_whitespace_only_raises(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_VALIDER)
        with pytest.raises(ValueError, match="comment is required"):
            ap.transition_to(ActionPlanStatus.A_DEFINIR, user, "   ")


class TestCancellation:
    """Test cancellation from any non-terminal state."""

    @pytest.mark.parametrize(
        "initial_status",
        [
            ActionPlanStatus.NOUVEAU,
            ActionPlanStatus.A_DEFINIR,
            ActionPlanStatus.A_VALIDER,
            ActionPlanStatus.A_IMPLEMENTER,
            ActionPlanStatus.IMPLEMENTATION_A_VALIDER,
            ActionPlanStatus.VALIDE,
        ],
    )
    def test_cancellation_from_any_state(self, initial_status):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=initial_status)
        ap.transition_to(ActionPlanStatus.ANNULE, user)
        assert ap.status == ActionPlanStatus.ANNULE

    def test_cannot_cancel_from_cloture(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CLOTURE)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.ANNULE, user)

    def test_cannot_cancel_from_annule(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.ANNULE)
        with pytest.raises(ValueError, match="Cannot transition"):
            ap.transition_to(ActionPlanStatus.ANNULE, user)


class TestTransitionAuditTrail:
    """Test that transitions create proper audit records."""

    def test_transition_creates_record(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory()
        ap.transition_to(ActionPlanStatus.A_DEFINIR, user)
        assert ActionPlanTransition.objects.count() == 1
        t = ActionPlanTransition.objects.first()
        assert t.from_status == ActionPlanStatus.NOUVEAU
        assert t.to_status == ActionPlanStatus.A_DEFINIR
        assert t.performed_by == user
        assert t.is_refusal is False

    def test_transition_records_ordered_by_date(self):
        user = UserFactory()
        ap = ComplianceActionPlanFactory()
        ap.transition_to(ActionPlanStatus.A_DEFINIR, user)
        ap.transition_to(ActionPlanStatus.A_VALIDER, user)
        transitions = list(ap.transitions.all())
        assert transitions[0].to_status == ActionPlanStatus.A_VALIDER
        assert transitions[1].to_status == ActionPlanStatus.A_DEFINIR


class TestGetAllowedTransitions:
    """Test get_allowed_transitions method."""

    def test_nouveau_allowed(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.NOUVEAU)
        allowed = ap.get_allowed_transitions()
        assert ActionPlanStatus.A_DEFINIR in allowed
        assert ActionPlanStatus.ANNULE in allowed

    def test_cloture_has_no_transitions(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.CLOTURE)
        assert ap.get_allowed_transitions() == []

    def test_annule_has_no_transitions(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.ANNULE)
        assert ap.get_allowed_transitions() == []

    def test_a_valider_includes_refusal(self):
        ap = ComplianceActionPlanFactory(status=ActionPlanStatus.A_VALIDER)
        allowed = ap.get_allowed_transitions()
        assert ActionPlanStatus.A_IMPLEMENTER in allowed
        assert ActionPlanStatus.A_DEFINIR in allowed
        assert ActionPlanStatus.ANNULE in allowed
