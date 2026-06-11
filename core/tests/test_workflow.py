"""Unit tests for the workflow framework (core/workflow.py).

Pure-Python tests: the framework has no model or database dependency, so these
need no ``@pytest.mark.django_db``. Assertions avoid exact label text so they do
not depend on the active locale.
"""

import pytest

from core.workflow import (
    DEFAULT_WORKFLOW,
    DEFAULT_WORKFLOW_NAME,
    WORKFLOW_REGISTRY,
    CommentRequiredError,
    Effect,
    IllegalTransitionError,
    PermAction,
    PermissionDeniedError,
    State,
    Transition,
    UnknownStateError,
    Workflow,
    WorkflowError,
    allowed_transitions,
    apply_transition,
    default_workflow,
    deletable_states,
    find_transition,
    get_workflow,
    linkable_states,
    permission_codename,
    register_workflow,
    reportable_states,
    resolve_workflow,
    validate_transition,
)


class FakeInstance:
    """Stand-in for a model instance carrying a ``workflow_state`` attribute."""

    def __init__(self, state=None):
        self.workflow_state = state


def _two_state_workflow(requires_comment=False):
    """A minimal valid workflow ``a -> b`` for transition-logic tests."""
    return Workflow(
        "test_wf",
        [
            State("a", "A", is_initial=True),
            State("b", "B", is_terminal=True),
        ],
        [Transition("a", "b", "Go", action=PermAction.APPROVE, requires_comment=requires_comment)],
    )


# --- Default workflow -------------------------------------------------------


def test_default_workflow_registered():
    assert DEFAULT_WORKFLOW_NAME in WORKFLOW_REGISTRY
    assert default_workflow() is DEFAULT_WORKFLOW
    assert get_workflow(DEFAULT_WORKFLOW_NAME) is DEFAULT_WORKFLOW


def test_default_workflow_states():
    codes = [s.code for s in DEFAULT_WORKFLOW.states]
    assert codes == ["draft", "pending", "validated", "archived"]
    assert DEFAULT_WORKFLOW.initial_state.code == "draft"
    assert [s.code for s in DEFAULT_WORKFLOW.states if s.is_terminal] == ["archived"]


def test_default_workflow_governance_flags():
    assert reportable_states(DEFAULT_WORKFLOW) == {"validated"}
    assert linkable_states(DEFAULT_WORKFLOW) == {"validated"}
    assert deletable_states(DEFAULT_WORKFLOW) == {"draft"}


def test_default_workflow_transitions_and_effects():
    submit = find_transition(DEFAULT_WORKFLOW, "draft", "pending")
    assert submit.action == PermAction.UPDATE
    assert Effect.NOTIFY_OWNER in submit.effects

    validate = find_transition(DEFAULT_WORKFLOW, "pending", "validated")
    assert validate.action == PermAction.APPROVE
    assert Effect.STAMP_VALIDATION in validate.effects

    # Archiving reuses the approve action (no dedicated .archive action yet).
    archive = find_transition(DEFAULT_WORKFLOW, "validated", "archived")
    assert archive.action == PermAction.APPROVE

    # Pending can be sent back to draft.
    assert find_transition(DEFAULT_WORKFLOW, "pending", "draft") is not None


def test_default_workflow_outgoing():
    assert [t.target for t in DEFAULT_WORKFLOW.outgoing("draft")] == ["pending"]
    assert {t.target for t in DEFAULT_WORKFLOW.outgoing("pending")} == {"draft", "validated"}
    assert DEFAULT_WORKFLOW.outgoing("archived") == ()


# --- Resolution and helpers -------------------------------------------------


def test_resolve_workflow_defaults_to_default():
    # Any model or label resolves to the default workflow until DB assignment.
    assert resolve_workflow("context.scope") is DEFAULT_WORKFLOW
    assert resolve_workflow(object) is DEFAULT_WORKFLOW
    # A workflow passed through is returned unchanged.
    assert resolve_workflow(DEFAULT_WORKFLOW) is DEFAULT_WORKFLOW


def test_module_helpers_accept_labels():
    assert reportable_states("context.scope") == {"validated"}
    assert deletable_states("assets.supportasset") == {"draft"}


def test_permission_codename():
    assert permission_codename("context.scope", PermAction.APPROVE) == "context.scope.approve"
    assert permission_codename("compliance.action_plan", "update") == "compliance.action_plan.update"


def test_state_equality_ignores_label_and_tone():
    assert State("x", "Label A", deletable=True) == State("x", "Label B", deletable=True, tone="info")
    assert State("x", "L", deletable=True) != State("x", "L", deletable=False)


# --- allowed_transitions ----------------------------------------------------


def test_allowed_transitions_without_permission_check():
    targets = {t.target for t in allowed_transitions(DEFAULT_WORKFLOW, "pending")}
    assert targets == {"draft", "validated"}


def test_allowed_transitions_filtered_by_permission():
    granted = {"context.scope.update"}
    has_perm = lambda codename: codename in granted  # noqa: E731

    # From pending: Send back (update) is allowed, Validate (approve) is filtered out.
    targets = {
        t.target
        for t in allowed_transitions(
            DEFAULT_WORKFLOW, "pending", has_perm=has_perm, perm_namespace="context.scope"
        )
    }
    assert targets == {"draft"}

    granted.add("context.scope.approve")
    targets = {
        t.target
        for t in allowed_transitions(
            DEFAULT_WORKFLOW, "pending", has_perm=has_perm, perm_namespace="context.scope"
        )
    }
    assert targets == {"draft", "validated"}


# --- validate_transition ----------------------------------------------------


def test_validate_transition_happy_path():
    transition = validate_transition(DEFAULT_WORKFLOW, "draft", "pending")
    assert transition.target == "pending"


def test_validate_transition_unknown_state():
    with pytest.raises(UnknownStateError):
        validate_transition(DEFAULT_WORKFLOW, "nope", "pending")
    with pytest.raises(UnknownStateError):
        validate_transition(DEFAULT_WORKFLOW, "draft", "nope")


def test_validate_transition_illegal():
    with pytest.raises(IllegalTransitionError):
        validate_transition(DEFAULT_WORKFLOW, "draft", "validated")


def test_validate_transition_permission_denied():
    has_perm = lambda codename: False  # noqa: E731
    with pytest.raises(PermissionDeniedError):
        validate_transition(
            DEFAULT_WORKFLOW, "pending", "validated",
            has_perm=has_perm, perm_namespace="context.scope",
        )


def test_validate_transition_comment_required():
    wf = _two_state_workflow(requires_comment=True)
    with pytest.raises(CommentRequiredError):
        validate_transition(wf, "a", "b")
    with pytest.raises(CommentRequiredError):
        validate_transition(wf, "a", "b", comment="   ")
    # A non-empty comment passes.
    assert validate_transition(wf, "a", "b", comment="because").target == "b"


# --- apply_transition -------------------------------------------------------


def test_apply_transition_mutates_state_and_returns_transition():
    instance = FakeInstance("draft")
    transition = apply_transition(instance, "pending")
    assert instance.workflow_state == "pending"
    assert transition.target == "pending"


def test_apply_transition_uses_initial_when_state_unset():
    instance = FakeInstance(None)  # current falls back to the initial state (draft)
    apply_transition(instance, "pending")
    assert instance.workflow_state == "pending"


def test_apply_transition_rejects_illegal():
    instance = FakeInstance("draft")
    with pytest.raises(IllegalTransitionError):
        apply_transition(instance, "validated")
    assert instance.workflow_state == "draft"  # unchanged on failure


# --- Workflow invariants ----------------------------------------------------


def test_workflow_requires_states():
    with pytest.raises(WorkflowError):
        Workflow("empty", [], [])


def test_workflow_rejects_duplicate_codes():
    with pytest.raises(WorkflowError):
        Workflow(
            "dup",
            [State("a", "A", is_initial=True), State("a", "A2", is_terminal=True)],
            [],
        )


def test_workflow_requires_exactly_one_initial():
    with pytest.raises(WorkflowError):
        Workflow("no_initial", [State("a", "A", is_terminal=True)], [])
    with pytest.raises(WorkflowError):
        Workflow(
            "two_initial",
            [
                State("a", "A", is_initial=True),
                State("b", "B", is_initial=True, is_terminal=True),
            ],
            [],
        )


def test_workflow_requires_a_terminal():
    with pytest.raises(WorkflowError):
        Workflow("no_terminal", [State("a", "A", is_initial=True)], [])


def test_workflow_rejects_transition_to_unknown_state():
    with pytest.raises(WorkflowError):
        Workflow(
            "bad_target",
            [State("a", "A", is_initial=True), State("b", "B", is_terminal=True)],
            [Transition("a", "ghost", "Go")],
        )


def test_workflow_rejects_transition_from_terminal():
    with pytest.raises(WorkflowError):
        Workflow(
            "leaves_terminal",
            [State("a", "A", is_initial=True), State("b", "B", is_terminal=True)],
            [Transition("b", "a", "Back")],
        )


# --- Registry ---------------------------------------------------------------


def test_register_duplicate_raises():
    wf = _two_state_workflow()
    register_workflow(Workflow("unique_wf_name", wf.states, wf.transitions))
    with pytest.raises(WorkflowError):
        register_workflow(Workflow("unique_wf_name", wf.states, wf.transitions))


def test_get_unknown_workflow_raises():
    with pytest.raises(WorkflowError):
        get_workflow("does_not_exist")
