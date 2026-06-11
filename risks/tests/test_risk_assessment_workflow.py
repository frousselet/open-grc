"""Tests for the risk assessment specific workflow (issue #105, phase 6g)."""

import pytest

from accounts.tests.factories import UserFactory
from core.workflow import (
    IllegalTransitionError,
    LifecycleProtectedError,
    deletable_states,
    find_transition,
    reportable_states,
    resolve_workflow,
)
from risks.constants import AssessmentStatus
from risks.models import RiskAssessment
from risks.tests.factories import RiskAssessmentFactory

pytestmark = pytest.mark.django_db


class TestRiskAssessmentWorkflow:
    def test_resolution_and_shape(self):
        workflow = resolve_workflow(RiskAssessment)
        assert workflow.name == "risk_assessment"
        assert workflow.initial_state.code == "draft"
        assert {s.code for s in workflow.states} == {s.value for s in AssessmentStatus}
        # Explicit opt-out despite the draft / validated state names.
        assert workflow.subsumes_approval is False

    def test_governance_flags(self):
        assert deletable_states(RiskAssessment) == {"draft"}
        assert reportable_states(RiskAssessment) == {
            "in_progress", "completed", "validated",
        }

    def test_validation_and_archiving_carry_approve(self):
        workflow = resolve_workflow(RiskAssessment)
        assert find_transition(workflow, "completed", "validated").action == "approve"
        assert find_transition(workflow, "validated", "archived").action == "approve"
        assert find_transition(workflow, "draft", "in_progress").action == "update"

    def test_campaign_path_with_rework(self):
        user = UserFactory()
        assessment = RiskAssessmentFactory()
        assessment.transition_to(AssessmentStatus.IN_PROGRESS, user)
        assessment.transition_to(AssessmentStatus.COMPLETED, user)
        # Rework loop.
        assessment.transition_to(AssessmentStatus.IN_PROGRESS, user)
        assessment.transition_to(AssessmentStatus.COMPLETED, user)
        assessment.transition_to(AssessmentStatus.VALIDATED, user)
        assessment.transition_to(AssessmentStatus.ARCHIVED, user)
        assessment.refresh_from_db()
        assert assessment.status == "archived"
        assert assessment.workflow_state == "archived"
        with pytest.raises(IllegalTransitionError):
            assessment.transition_to(AssessmentStatus.DRAFT, user)

    def test_approval_stays_independent(self):
        assessment = RiskAssessmentFactory(is_approved=True)
        assessment.refresh_from_db()
        # The approval flag does not move the machine (explicit opt-out).
        assert assessment.workflow_state == "draft"
        assert assessment.is_approved is True

    def test_only_draft_deletable(self):
        live = RiskAssessmentFactory(status=AssessmentStatus.IN_PROGRESS)
        with pytest.raises(LifecycleProtectedError):
            live.delete()
        draft = RiskAssessmentFactory()
        pk = draft.pk
        draft.delete()
        assert not RiskAssessment.objects.filter(pk=pk).exists()

    def test_state_sync_both_ways(self):
        assessment = RiskAssessmentFactory()
        assessment.status = AssessmentStatus.IN_PROGRESS
        assessment.save()
        assessment.refresh_from_db()
        assert assessment.workflow_state == "in_progress"

        assessment.workflow_state = "completed"
        assessment.save()
        assessment.refresh_from_db()
        assert assessment.status == "completed"
