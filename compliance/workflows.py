"""Specific lifecycle workflows for the compliance module.

The workflows are generated from the existing transition constants so each
state machine keeps a single source of truth. Governance flags per state
follow the spec in issue #105: drafting states are deletable, working states
count in reports, implementation states are linkable, and the closed /
cancelled states are terminal.

Imported from ``ComplianceConfig.ready()`` so registration happens at startup.
"""

from compliance.constants import (
    ACTION_PLAN_CANCELLABLE_STATUSES,
    ACTION_PLAN_REFUSAL_TRANSITIONS,
    ACTION_PLAN_TRANSITION_PERMISSIONS,
    ACTION_PLAN_TRANSITIONS,
    ASSESSMENT_STATUS_TRANSITIONS,
    ActionPlanStatus,
    AssessmentStatus,
)
from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)

ACTION_PLAN_WORKFLOW_NAME = "action_plan"
ASSESSMENT_WORKFLOW_NAME = "compliance_assessment"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_ACTION_PLAN_STATE_FLAGS = {
    ActionPlanStatus.NEW: (False, False, True, True, False, "secondary"),
    ActionPlanStatus.TO_DEFINE: (False, False, True, False, False, "info"),
    ActionPlanStatus.TO_VALIDATE: (True, False, False, False, False, "warning"),
    ActionPlanStatus.TO_IMPLEMENT: (True, True, False, False, False, "primary"),
    ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE: (True, True, False, False, False, "warning"),
    ActionPlanStatus.VALIDATED: (True, True, False, False, False, "success"),
    ActionPlanStatus.CLOSED: (True, False, False, False, True, "dark"),
    ActionPlanStatus.CANCELLED: (False, False, False, False, True, "danger"),
}


def _build_action_plan_workflow():
    states = []
    for status in ActionPlanStatus:
        counts, linkable, deletable, initial, terminal, tone = _ACTION_PLAN_STATE_FLAGS[status]
        states.append(
            State(
                str(status.value),
                status.label,
                counts_in_reports=counts,
                linkable=linkable,
                deletable=deletable,
                is_initial=initial,
                is_terminal=terminal,
                tone=tone,
                branch=status == ActionPlanStatus.CANCELLED,
            )
        )

    transitions = []
    for source, targets in ACTION_PLAN_TRANSITIONS.items():
        for target in targets:
            codename = ACTION_PLAN_TRANSITION_PERMISSIONS.get((source, target), "")
            action = codename.rsplit(".", 1)[1] if codename else "update"
            is_refusal = ACTION_PLAN_REFUSAL_TRANSITIONS.get(source) == target
            transitions.append(
                Transition(
                    str(source.value),
                    str(target.value),
                    ActionPlanStatus(target).label,
                    action=action,
                    requires_comment=is_refusal,
                )
            )
    for source in ACTION_PLAN_CANCELLABLE_STATUSES:
        transitions.append(
            Transition(
                str(source.value),
                str(ActionPlanStatus.CANCELLED.value),
                ActionPlanStatus.CANCELLED.label,
                action="cancel",
            )
        )

    return Workflow(ACTION_PLAN_WORKFLOW_NAME, states, transitions)


# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
# Cancelled assessments leave reports / the calendar; a draft is a private
# working copy. Nothing links *to* an assessment via the linking surfaces
# (risks belong to it, frameworks are operational references), so no state is
# linkable.
_ASSESSMENT_STATE_FLAGS = {
    AssessmentStatus.DRAFT: (False, False, True, True, False, "secondary"),
    AssessmentStatus.PLANNED: (True, False, False, False, False, "info"),
    AssessmentStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    AssessmentStatus.COMPLETED: (True, False, False, False, False, "success"),
    AssessmentStatus.CLOSED: (True, False, False, False, True, "dark"),
    AssessmentStatus.CANCELLED: (False, False, False, False, True, "danger"),
}


def _build_assessment_workflow():
    states = []
    for status in AssessmentStatus:
        counts, linkable, deletable, initial, terminal, tone = _ASSESSMENT_STATE_FLAGS[status]
        states.append(
            State(
                str(status.value),
                status.label,
                counts_in_reports=counts,
                linkable=linkable,
                deletable=deletable,
                is_initial=initial,
                is_terminal=terminal,
                tone=tone,
                branch=status == AssessmentStatus.CANCELLED,
            )
        )

    # The legacy machine has no per-step permissions or mandatory comments:
    # every transition is an assessment update.
    transitions = [
        Transition(
            str(source.value),
            str(target.value),
            AssessmentStatus(target).label,
            action="update",
        )
        for source, targets in ASSESSMENT_STATUS_TRANSITIONS.items()
        for target in targets
    ]

    return Workflow(ASSESSMENT_WORKFLOW_NAME, states, transitions)


if ACTION_PLAN_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    ACTION_PLAN_WORKFLOW = register_workflow(_build_action_plan_workflow())
else:
    ACTION_PLAN_WORKFLOW = WORKFLOW_REGISTRY[ACTION_PLAN_WORKFLOW_NAME]

if ASSESSMENT_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    ASSESSMENT_WORKFLOW = register_workflow(_build_assessment_workflow())
else:
    ASSESSMENT_WORKFLOW = WORKFLOW_REGISTRY[ASSESSMENT_WORKFLOW_NAME]
