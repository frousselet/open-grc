"""Workflow framework: declarative state machines for element lifecycles.

A :class:`Workflow` is an ordered set of :class:`State` objects plus the allowed
:class:`Transition` objects between them. Governance is metadata carried by each
state (``counts_in_reports``, ``linkable``, ``deletable``), so the cross-cutting
rules (report / KPI / calendar inclusion, linking, deletion) read state flags
instead of checking a hardcoded status value.

Workflows are declared in code and registered in :data:`WORKFLOW_REGISTRY`. Each
model is assigned a workflow by name; a model with no explicit assignment uses the
default workflow. Per-model DB assignment is wired in a later phase
(:func:`workflow_name_for` is the single extension point).

This module is intentionally free of model / database imports so it can be unit
tested in isolation and reused by every layer (views, DRF, MCP, reports). Applying
a transition only mutates ``instance.workflow_state`` and returns the matched
transition; executing its side effects (notifications, validation stamping) and
persisting the instance are the caller's responsibility in later phases.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from django.utils.translation import gettext_lazy as _


# --- Permission actions and side effects ------------------------------------


class PermAction:
    """Permission action suffixes (matching ``accounts.constants`` vocabulary).

    A full codename is ``<namespace>.<action>`` where ``<namespace>`` is the
    permission feature path (e.g. ``context.scope`` or ``compliance.action_plan``).
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"


class Effect:
    """Declarative side effects a transition may carry.

    Phase 1 only declares them; execution is wired in later phases (notifications
    in the notification phase, validation stamping when the model field exists).
    """

    NOTIFY_OWNER = "notify_owner"
    STAMP_VALIDATION = "stamp_validation"


# --- Declarative structures -------------------------------------------------


@dataclass(frozen=True)
class State:
    """A single state in a workflow, carrying its governance metadata.

    ``label`` and ``tone`` are excluded from equality so that two states are equal
    iff they share the same code and the same governance flags. ``tone`` is a UI
    badge category (mapped to a semantic colour in the templates).
    """

    code: str
    label: object = field(compare=False)
    counts_in_reports: bool = False
    linkable: bool = False
    deletable: bool = False
    is_initial: bool = False
    is_terminal: bool = False
    tone: str = field(default="neutral", compare=False)


@dataclass(frozen=True)
class Transition:
    """A permitted move from one state to another.

    ``action`` is the permission action suffix required to perform the transition.
    ``requires_comment`` forces a non-empty comment (refusals, cancellations).
    ``effects`` is a tuple of :class:`Effect` values run by the caller after apply.
    """

    source: str
    target: str
    verb: object = field(compare=False)
    action: str = PermAction.UPDATE
    requires_comment: bool = False
    effects: tuple = ()


# --- Errors -----------------------------------------------------------------


class WorkflowError(Exception):
    """Base error for an invalid workflow definition or an invalid transition."""


class UnknownStateError(WorkflowError):
    """A state code does not belong to the workflow."""


class IllegalTransitionError(WorkflowError):
    """No transition exists between the two states."""


class PermissionDeniedError(WorkflowError):
    """The user lacks the permission required by the transition."""


class CommentRequiredError(WorkflowError):
    """The transition requires a comment but none was provided."""


class LifecycleProtectedError(Exception):
    """Raised when deleting an element whose current state is not deletable."""


# --- Workflow ---------------------------------------------------------------


class Workflow:
    """An ordered set of states and the allowed transitions between them.

    Invariants (checked at construction): unique state codes, exactly one initial
    state, at least one terminal state, every transition references declared states,
    and no transition leaves a terminal state.
    """

    def __init__(self, name: str, states, transitions) -> None:
        self.name = name
        self.states = tuple(states)
        self.transitions = tuple(transitions)
        self._by_code = {s.code: s for s in self.states}
        self._validate()

    def _validate(self) -> None:
        if not self.states:
            raise WorkflowError(f"Workflow '{self.name}' has no states.")
        codes = [s.code for s in self.states]
        if len(codes) != len(set(codes)):
            raise WorkflowError(f"Workflow '{self.name}' has duplicate state codes.")
        initials = [s for s in self.states if s.is_initial]
        if len(initials) != 1:
            raise WorkflowError(
                f"Workflow '{self.name}' must have exactly one initial state "
                f"(found {len(initials)})."
            )
        if not any(s.is_terminal for s in self.states):
            raise WorkflowError(
                f"Workflow '{self.name}' must have at least one terminal state."
            )
        for t in self.transitions:
            if t.source not in self._by_code:
                raise WorkflowError(
                    f"Transition source '{t.source}' is not a state of '{self.name}'."
                )
            if t.target not in self._by_code:
                raise WorkflowError(
                    f"Transition target '{t.target}' is not a state of '{self.name}'."
                )
            if self._by_code[t.source].is_terminal:
                raise WorkflowError(
                    f"Transition leaves terminal state '{t.source}' in '{self.name}'."
                )

    @property
    def initial_state(self) -> State:
        return next(s for s in self.states if s.is_initial)

    def state(self, code: str) -> State:
        try:
            return self._by_code[code]
        except KeyError:
            raise UnknownStateError(
                f"'{code}' is not a state of workflow '{self.name}'."
            ) from None

    def has_state(self, code: str) -> bool:
        return code in self._by_code

    def outgoing(self, code: str) -> tuple:
        """Return every transition leaving ``code`` (validates the state exists)."""
        self.state(code)
        return tuple(t for t in self.transitions if t.source == code)

    def _codes_where(self, attr: str) -> frozenset:
        return frozenset(s.code for s in self.states if getattr(s, attr))

    @property
    def reportable_state_codes(self) -> frozenset:
        return self._codes_where("counts_in_reports")

    @property
    def linkable_state_codes(self) -> frozenset:
        return self._codes_where("linkable")

    @property
    def deletable_state_codes(self) -> frozenset:
        return self._codes_where("deletable")


# --- Registry ---------------------------------------------------------------

DEFAULT_WORKFLOW_NAME = "default_lifecycle"

WORKFLOW_REGISTRY: dict[str, Workflow] = {}


def register_workflow(workflow: Workflow) -> Workflow:
    """Register a workflow under its name; raise if the name is already taken."""
    if workflow.name in WORKFLOW_REGISTRY:
        raise WorkflowError(f"Workflow '{workflow.name}' is already registered.")
    WORKFLOW_REGISTRY[workflow.name] = workflow
    return workflow


def get_workflow(name: str) -> Workflow:
    try:
        return WORKFLOW_REGISTRY[name]
    except KeyError:
        raise WorkflowError(f"No workflow named '{name}'.") from None


def default_workflow() -> Workflow:
    return WORKFLOW_REGISTRY[DEFAULT_WORKFLOW_NAME]


def _resolve_model(model_or_label):
    """Return a model class from a class or an ``app_label.model_name`` label."""
    if isinstance(model_or_label, str):
        try:
            from django.apps import apps

            return apps.get_model(model_or_label)
        except Exception:
            return None
    if isinstance(model_or_label, type):
        return model_or_label
    return None


def workflow_name_for(model_or_label) -> str:
    """Resolve the workflow name assigned to a model.

    Reads the per-model assignment from ``VersioningConfig.workflow_name``. An
    unset, unknown or unreadable assignment (including contexts with no database)
    falls back to the default workflow, so callers never branch on assignment
    logic themselves.
    """
    model = _resolve_model(model_or_label)
    if model is not None:
        try:
            from core.models import VersioningConfig

            name = VersioningConfig.get_workflow_name(model)
        except Exception:
            name = None
        if name and name in WORKFLOW_REGISTRY:
            return name
    return DEFAULT_WORKFLOW_NAME


def resolve_workflow(model_or_label) -> Workflow:
    """Return the :class:`Workflow` a model runs (default until DB assignment)."""
    if isinstance(model_or_label, Workflow):
        return model_or_label
    return get_workflow(workflow_name_for(model_or_label))


# --- Permission helpers -----------------------------------------------------


def permission_codename(namespace: str, action: str) -> str:
    """Build a ``<namespace>.<action>`` permission codename.

    ``namespace`` is the permission feature path (e.g. ``context.scope``), which is
    not always the model name (e.g. ``compliance.action_plan``), so it is supplied
    explicitly rather than derived here.
    """
    return f"{namespace}.{action}"


# --- Transition logic -------------------------------------------------------


def find_transition(workflow: Workflow, source: str, target: str):
    """Return the transition ``source -> target`` or ``None`` if none exists."""
    for t in workflow.transitions:
        if t.source == source and t.target == target:
            return t
    return None


def allowed_transitions(
    workflow: Workflow,
    current_code: str,
    *,
    has_perm: Callable[[str], bool] | None = None,
    perm_namespace: str | None = None,
) -> tuple:
    """Transitions leaving ``current_code`` the user may perform.

    When ``has_perm`` and ``perm_namespace`` are both given, transitions whose
    required permission the user lacks are filtered out; otherwise permissions are
    not checked.
    """
    result = []
    for t in workflow.outgoing(current_code):
        if has_perm is not None and perm_namespace is not None:
            if not has_perm(permission_codename(perm_namespace, t.action)):
                continue
        result.append(t)
    return tuple(result)


def validate_transition(
    workflow: Workflow,
    current_code: str,
    target_code: str,
    *,
    has_perm: Callable[[str], bool] | None = None,
    perm_namespace: str | None = None,
    comment: str | None = None,
) -> Transition:
    """Validate ``current_code -> target_code`` and return the matched transition.

    Raises a :class:`WorkflowError` subclass: :class:`UnknownStateError`,
    :class:`IllegalTransitionError`, :class:`PermissionDeniedError` or
    :class:`CommentRequiredError`.
    """
    if not workflow.has_state(current_code):
        raise UnknownStateError(
            f"'{current_code}' is not a state of workflow '{workflow.name}'."
        )
    if not workflow.has_state(target_code):
        raise UnknownStateError(
            f"'{target_code}' is not a state of workflow '{workflow.name}'."
        )
    transition = find_transition(workflow, current_code, target_code)
    if transition is None:
        raise IllegalTransitionError(
            f"No transition '{current_code}' -> '{target_code}' in '{workflow.name}'."
        )
    if has_perm is not None and perm_namespace is not None:
        codename = permission_codename(perm_namespace, transition.action)
        if not has_perm(codename):
            raise PermissionDeniedError(f"Permission '{codename}' is required.")
    if transition.requires_comment and not (comment and comment.strip()):
        raise CommentRequiredError(
            f"Transition '{current_code}' -> '{target_code}' requires a comment."
        )
    return transition


def apply_transition(
    instance,
    target_code: str,
    *,
    workflow: Workflow | None = None,
    has_perm: Callable[[str], bool] | None = None,
    perm_namespace: str | None = None,
    comment: str | None = None,
) -> Transition:
    """Validate then apply a transition by setting ``instance.workflow_state``.

    Returns the matched transition; the caller runs its ``effects`` and persists
    the instance. The current state is read from ``instance.workflow_state``,
    falling back to the workflow's initial state when unset.
    """
    if workflow is None:
        workflow = resolve_workflow(type(instance))
    current_code = getattr(instance, "workflow_state", None) or workflow.initial_state.code
    transition = validate_transition(
        workflow,
        current_code,
        target_code,
        has_perm=has_perm,
        perm_namespace=perm_namespace,
        comment=comment,
    )
    instance.workflow_state = target_code
    return transition


# --- Module-level governance helpers (accept a model, label or workflow) ----


def reportable_states(model_or_label) -> frozenset:
    return resolve_workflow(model_or_label).reportable_state_codes


def linkable_states(model_or_label) -> frozenset:
    return resolve_workflow(model_or_label).linkable_state_codes


def deletable_states(model_or_label) -> frozenset:
    return resolve_workflow(model_or_label).deletable_state_codes


def reportable(queryset):
    """Restrict a queryset to elements whose state counts in reports / KPIs / calendar."""
    return queryset.filter(workflow_state__in=reportable_states(queryset.model))


def linkable(queryset):
    """Restrict a queryset to elements that may currently be linked."""
    return queryset.filter(workflow_state__in=linkable_states(queryset.model))


# --- Default workflow -------------------------------------------------------
#
# The 4-state lifecycle applied to every model that is not assigned a specific
# workflow. Only "validated" counts in reports and is linkable; only "draft" can
# be deleted; "archived" is terminal. "Archive" reuses the "approve" action for
# now (a dedicated ".archive" action is an open question in issue #105).

DEFAULT_WORKFLOW = register_workflow(
    Workflow(
        name=DEFAULT_WORKFLOW_NAME,
        states=[
            State("draft", _("Draft"), deletable=True, is_initial=True, tone="neutral"),
            State("pending", _("Pending validation"), tone="info"),
            State(
                "validated",
                _("Validated"),
                counts_in_reports=True,
                linkable=True,
                tone="success",
            ),
            State("archived", _("Archived"), is_terminal=True, tone="muted"),
        ],
        transitions=[
            Transition(
                "draft",
                "pending",
                _("Submit"),
                action=PermAction.UPDATE,
                effects=(Effect.NOTIFY_OWNER,),
            ),
            Transition("pending", "draft", _("Send back to draft"), action=PermAction.UPDATE),
            Transition(
                "pending",
                "validated",
                _("Validate"),
                action=PermAction.APPROVE,
                effects=(Effect.STAMP_VALIDATION,),
            ),
            Transition("validated", "archived", _("Archive"), action=PermAction.APPROVE),
        ],
    )
)
