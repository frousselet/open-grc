"""Specific lifecycle workflow for the management review (ISO 27001 clause 9.3).

Generated from the existing transition constants so the state machine keeps a
single source of truth. Closure requires the ``approve`` permission (the rule
the API enforces explicitly), and cancellation keeps its mandatory comment.

Imported from ``ReportsConfig.ready()`` so registration happens at startup.
"""

from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)
from reports.constants import (
    MANAGEMENT_REVIEW_CANCELLABLE_STATUSES,
    MANAGEMENT_REVIEW_TRANSITIONS,
    ManagementReviewStatus,
)

MANAGEMENT_REVIEW_WORKFLOW_NAME = "management_review"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
# Only a planned review (nothing prepared yet) may be deleted; a cancelled
# review leaves reports. Nothing links *to* a review via the linking surfaces
# (decisions and action plans originate from it), so no state is linkable.
_MANAGEMENT_REVIEW_STATE_FLAGS = {
    ManagementReviewStatus.PLANNED: (True, False, True, True, False, "info"),
    ManagementReviewStatus.IN_PREPARATION: (True, False, False, False, False, "primary"),
    ManagementReviewStatus.HELD: (True, False, False, False, False, "success"),
    ManagementReviewStatus.CLOSED: (True, False, False, False, True, "dark"),
    ManagementReviewStatus.CANCELLED: (False, False, False, False, True, "danger"),
}


def _build_management_review_workflow():
    states = []
    for status in ManagementReviewStatus:
        counts, linkable, deletable, initial, terminal, tone = (
            _MANAGEMENT_REVIEW_STATE_FLAGS[status]
        )
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
                branch=status == ManagementReviewStatus.CANCELLED,
            )
        )

    transitions = []
    for source, targets in MANAGEMENT_REVIEW_TRANSITIONS.items():
        for target in targets:
            transitions.append(
                Transition(
                    str(source.value),
                    str(target.value),
                    ManagementReviewStatus(target).label,
                    # Closure is an approval act; other moves are updates.
                    action="approve" if target == ManagementReviewStatus.CLOSED else "update",
                )
            )
    for source in MANAGEMENT_REVIEW_CANCELLABLE_STATUSES:
        transitions.append(
            Transition(
                str(source.value),
                str(ManagementReviewStatus.CANCELLED.value),
                ManagementReviewStatus.CANCELLED.label,
                action="update",
                requires_comment=True,
            )
        )

    return Workflow(MANAGEMENT_REVIEW_WORKFLOW_NAME, states, transitions)


if MANAGEMENT_REVIEW_WORKFLOW_NAME not in WORKFLOW_REGISTRY:
    MANAGEMENT_REVIEW_WORKFLOW = register_workflow(_build_management_review_workflow())
else:
    MANAGEMENT_REVIEW_WORKFLOW = WORKFLOW_REGISTRY[MANAGEMENT_REVIEW_WORKFLOW_NAME]
