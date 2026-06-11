"""Tests for the BaseModel lifecycle API and the is_approved <-> workflow_state sync.

Exercised through a concrete model (context.Scope, on the default workflow).
"""

import pytest

from accounts.tests.factories import UserFactory
from context.models import Scope
from context.tests.factories import ScopeFactory
from core.models import VersioningConfig
from core.workflow import (
    DEFAULT_WORKFLOW,
    WORKFLOW_REGISTRY,
    IllegalTransitionError,
    LifecycleProtectedError,
    State,
    Transition,
    Workflow,
    register_workflow,
)

# A throwaway workflow registered once, used by the assignment test below.
_ASSIGN_WF = "test_assignment_workflow"
if _ASSIGN_WF not in WORKFLOW_REGISTRY:
    register_workflow(
        Workflow(
            _ASSIGN_WF,
            [
                State("open", "Open", is_initial=True),
                State("done", "Done", is_terminal=True, counts_in_reports=True),
            ],
            [Transition("open", "done", "Finish")],
        )
    )


@pytest.mark.django_db
class TestLifecycleDefaults:
    def test_new_object_is_draft(self):
        scope = ScopeFactory()
        assert scope.workflow_state == "draft"
        assert scope.counts_in_reports is False
        assert scope.is_linkable is False
        assert scope.is_deletable is True

    def test_get_workflow_is_default(self):
        assert ScopeFactory().get_workflow() is DEFAULT_WORKFLOW


@pytest.mark.django_db
class TestApprovalSync:
    def test_creating_approved_syncs_to_validated(self):
        scope = ScopeFactory(is_approved=True)
        assert scope.workflow_state == "validated"
        assert scope.counts_in_reports is True
        assert scope.is_linkable is True
        assert scope.is_deletable is False

    def test_legacy_approve_promotes_state(self):
        scope = ScopeFactory()
        assert scope.workflow_state == "draft"
        scope.is_approved = True
        scope.save()
        assert scope.workflow_state == "validated"

    def test_legacy_unapprove_resets_state(self):
        scope = ScopeFactory(is_approved=True)
        assert scope.workflow_state == "validated"
        scope.is_approved = False
        scope.save()
        assert scope.workflow_state == "draft"

    def test_update_fields_save_persists_state_sync(self):
        scope = ScopeFactory()
        scope.is_approved = True
        scope.save(update_fields=["is_approved", "approved_at"])
        scope.refresh_from_db()
        assert scope.workflow_state == "validated"


@pytest.mark.django_db
class TestTransitions:
    def test_submit_moves_to_pending(self):
        user = UserFactory()
        scope = ScopeFactory()
        scope.transition_to("pending", user)
        assert scope.workflow_state == "pending"
        assert scope.is_approved is False  # pending does not count in reports

    def test_pending_is_not_clobbered_by_sync(self):
        user = UserFactory()
        scope = ScopeFactory()
        scope.transition_to("pending", user)
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_validate_stamps_approval(self):
        user = UserFactory()
        scope = ScopeFactory()
        scope.transition_to("pending", user)
        scope.transition_to("validated", user)
        assert scope.workflow_state == "validated"
        assert scope.is_approved is True
        assert scope.approved_by == user
        assert scope.approved_at is not None

    def test_archive_clears_approval(self):
        user = UserFactory()
        scope = ScopeFactory()
        scope.transition_to("pending", user)
        scope.transition_to("validated", user)
        scope.transition_to("archived", user)
        assert scope.workflow_state == "archived"
        assert scope.is_approved is False  # archived no longer counts in reports

    def test_illegal_transition_raises_and_keeps_state(self):
        scope = ScopeFactory()
        with pytest.raises(IllegalTransitionError):
            scope.transition_to("validated")
        assert scope.workflow_state == "draft"

    def test_available_transitions_lists_outgoing(self):
        scope = ScopeFactory()
        assert {t.target for t in scope.available_transitions()} == {"pending"}
        scope.transition_to("pending")
        assert {t.target for t in scope.available_transitions()} == {"draft", "validated"}


@pytest.mark.django_db
class TestWorkflowAssignment:
    def setup_method(self):
        VersioningConfig.clear_cache()

    def teardown_method(self):
        VersioningConfig.clear_cache()

    def test_blank_assignment_uses_default(self):
        VersioningConfig.objects.create(model_name="context.scope", workflow_name="")
        assert ScopeFactory().get_workflow() is DEFAULT_WORKFLOW

    def test_unknown_assignment_falls_back_to_default(self):
        VersioningConfig.objects.create(model_name="context.scope", workflow_name="nope")
        assert ScopeFactory().get_workflow() is DEFAULT_WORKFLOW

    def test_assigned_workflow_is_resolved(self):
        VersioningConfig.objects.create(model_name="context.scope", workflow_name=_ASSIGN_WF)
        assert ScopeFactory().get_workflow().name == _ASSIGN_WF


@pytest.mark.django_db
def test_reportable_and_linkable_queryset_helpers():
    from core.workflow import linkable, reportable

    ScopeFactory()  # draft
    ScopeFactory(is_approved=True)  # validated
    assert reportable(Scope.objects.all()).count() == 1
    assert linkable(Scope.objects.all()).count() == 1


@pytest.mark.django_db
class TestDeletionGuard:
    def test_draft_object_can_be_deleted(self):
        scope = ScopeFactory()  # draft, deletable
        pk = scope.pk
        scope.delete()
        assert not Scope.objects.filter(pk=pk).exists()

    def test_validated_object_cannot_be_deleted(self):
        scope = ScopeFactory(is_approved=True)  # validated, not deletable
        with pytest.raises(LifecycleProtectedError):
            scope.delete()
        assert Scope.objects.filter(pk=scope.pk).exists()

    def test_pending_object_cannot_be_deleted(self):
        scope = ScopeFactory()
        scope.transition_to("pending")
        with pytest.raises(LifecycleProtectedError):
            scope.delete()
        assert Scope.objects.filter(pk=scope.pk).exists()
