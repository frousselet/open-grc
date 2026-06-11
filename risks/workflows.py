"""Specific lifecycle workflows for the risks module.

These statuses had no transition constants (freely editable), so the graphs
encode the natural ISO 27005 progressions; legacy free status writes (and the
automated overdue / expiry flips) keep working through the
status <-> workflow_state sync during the migration period.

Governance highlights: a freshly *identified* risk is a working entry and does
not reach the risk register yet (the spec's draft analog); a *closed* risk
stays in the register as history but cannot gain new links; a *cancelled*
treatment plan leaves reports while every acceptance state remains reportable
(a revoked acceptance is audit-relevant governance history).

Imported from ``RisksConfig.ready()`` so registration happens at startup.
"""

from core.workflow import (
    WORKFLOW_REGISTRY,
    State,
    Transition,
    Workflow,
    register_workflow,
)
from risks.constants import (
    AcceptanceStatus,
    AssessmentStatus,
    BaselineGapStatus,
    EbiosBaselineStatus,
    EbiosStudyFrameworkStatus,
    EbiosSummaryStatus,
    EbiosWorkshopStatus,
    PACSMeasureStatus,
    RiskStatus,
    TreatmentPlanStatus,
    VulnerabilityStatus,
)

RISK_WORKFLOW_NAME = "risk"
TREATMENT_PLAN_WORKFLOW_NAME = "risk_treatment_plan"
ACCEPTANCE_WORKFLOW_NAME = "risk_acceptance"
VULNERABILITY_WORKFLOW_NAME = "vulnerability"

# code -> (counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
_RISK_STATE_FLAGS = {
    RiskStatus.IDENTIFIED: (False, False, True, True, False, "secondary"),
    RiskStatus.ANALYZED: (True, True, False, False, False, "info"),
    RiskStatus.EVALUATED: (True, True, False, False, False, "primary"),
    RiskStatus.TREATMENT_PLANNED: (True, True, False, False, False, "primary"),
    RiskStatus.TREATMENT_IN_PROGRESS: (True, True, False, False, False, "warning"),
    RiskStatus.TREATED: (True, True, False, False, False, "success"),
    RiskStatus.ACCEPTED: (True, True, False, False, False, "success"),
    RiskStatus.MONITORING: (True, True, False, False, False, "info"),
    RiskStatus.CLOSED: (True, False, False, False, True, "dark"),
}

_RISK_TRANSITIONS = [
    (RiskStatus.IDENTIFIED, RiskStatus.ANALYZED),
    (RiskStatus.ANALYZED, RiskStatus.EVALUATED),
    (RiskStatus.EVALUATED, RiskStatus.TREATMENT_PLANNED),
    (RiskStatus.EVALUATED, RiskStatus.ACCEPTED),
    (RiskStatus.TREATMENT_PLANNED, RiskStatus.TREATMENT_IN_PROGRESS),
    (RiskStatus.TREATMENT_IN_PROGRESS, RiskStatus.TREATED),
    (RiskStatus.TREATED, RiskStatus.ACCEPTED),
    (RiskStatus.TREATED, RiskStatus.MONITORING),
    (RiskStatus.TREATED, RiskStatus.CLOSED),
    (RiskStatus.ACCEPTED, RiskStatus.MONITORING),
    (RiskStatus.ACCEPTED, RiskStatus.CLOSED),
    # The monitoring loop can re-enter the analysis cycle (periodic review).
    (RiskStatus.MONITORING, RiskStatus.ANALYZED),
    (RiskStatus.MONITORING, RiskStatus.CLOSED),
]

_TREATMENT_PLAN_STATE_FLAGS = {
    TreatmentPlanStatus.PLANNED: (True, True, True, True, False, "info"),
    TreatmentPlanStatus.IN_PROGRESS: (True, True, False, False, False, "primary"),
    TreatmentPlanStatus.OVERDUE: (True, True, False, False, False, "danger"),
    TreatmentPlanStatus.COMPLETED: (True, False, False, False, True, "success"),
    TreatmentPlanStatus.CANCELLED: (False, False, False, False, True, "danger"),
}

_TREATMENT_PLAN_TRANSITIONS = [
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.IN_PROGRESS),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.COMPLETED),
    # Overdue is normally flipped automatically when the target date passes,
    # but the moves stay legal as manual transitions too.
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.OVERDUE),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.OVERDUE),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.IN_PROGRESS),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.COMPLETED),
    (TreatmentPlanStatus.PLANNED, TreatmentPlanStatus.CANCELLED),
    (TreatmentPlanStatus.IN_PROGRESS, TreatmentPlanStatus.CANCELLED),
    (TreatmentPlanStatus.OVERDUE, TreatmentPlanStatus.CANCELLED),
]

_ACCEPTANCE_STATE_FLAGS = {
    AcceptanceStatus.ACTIVE: (True, False, True, True, False, "success"),
    AcceptanceStatus.RENEWED: (True, False, False, False, False, "info"),
    AcceptanceStatus.EXPIRED: (True, False, False, False, False, "warning"),
    AcceptanceStatus.REVOKED: (True, False, False, False, True, "danger"),
}

_ACCEPTANCE_TRANSITIONS = [
    (AcceptanceStatus.ACTIVE, AcceptanceStatus.EXPIRED),
    (AcceptanceStatus.ACTIVE, AcceptanceStatus.RENEWED),
    (AcceptanceStatus.ACTIVE, AcceptanceStatus.REVOKED),
    (AcceptanceStatus.RENEWED, AcceptanceStatus.EXPIRED),
    (AcceptanceStatus.RENEWED, AcceptanceStatus.REVOKED),
    (AcceptanceStatus.EXPIRED, AcceptanceStatus.RENEWED),
    (AcceptanceStatus.EXPIRED, AcceptanceStatus.REVOKED),
]

_VULNERABILITY_STATE_FLAGS = {
    VulnerabilityStatus.IDENTIFIED: (True, True, True, True, False, "secondary"),
    VulnerabilityStatus.CONFIRMED: (True, True, False, False, False, "warning"),
    VulnerabilityStatus.MITIGATED: (True, True, False, False, False, "success"),
    VulnerabilityStatus.ACCEPTED: (True, True, False, False, False, "info"),
    VulnerabilityStatus.CLOSED: (True, False, False, False, True, "dark"),
}

_VULNERABILITY_TRANSITIONS = [
    (VulnerabilityStatus.IDENTIFIED, VulnerabilityStatus.CONFIRMED),
    # A false positive can be closed directly.
    (VulnerabilityStatus.IDENTIFIED, VulnerabilityStatus.CLOSED),
    (VulnerabilityStatus.CONFIRMED, VulnerabilityStatus.MITIGATED),
    (VulnerabilityStatus.CONFIRMED, VulnerabilityStatus.ACCEPTED),
    (VulnerabilityStatus.MITIGATED, VulnerabilityStatus.CLOSED),
    (VulnerabilityStatus.ACCEPTED, VulnerabilityStatus.CLOSED),
]


def _build(name, status_enum, flags, transition_pairs, *, subsumes_approval=None):
    """Build a workflow from per-state flags and (source, target[, options]) pairs.

    A transition tuple may carry an options dict as third element with
    ``action`` (permission action suffix, default ``update``) and
    ``requires_comment``.
    """
    states = []
    for status in status_enum:
        counts, linkable, deletable, initial, terminal, tone = flags[status]
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
            )
        )
    transitions = []
    for pair in transition_pairs:
        source, target = pair[0], pair[1]
        options = pair[2] if len(pair) > 2 else {}
        transitions.append(
            Transition(
                str(source.value),
                str(target.value),
                status_enum(target).label,
                action=options.get("action", "update"),
                requires_comment=options.get("requires_comment", False),
            )
        )
    return Workflow(name, states, transitions, subsumes_approval=subsumes_approval)


# ── Risk assessment campaign ────────────────────────────────
#
# Validation and archiving are approval acts; the assessment keeps its own
# validated_by stamp and the independent is_approved axis (explicit opt-out:
# the draft / validated state names would otherwise trip the heuristic).

RISK_ASSESSMENT_WORKFLOW_NAME = "risk_assessment"

_RISK_ASSESSMENT_STATE_FLAGS = {
    AssessmentStatus.DRAFT: (False, False, True, True, False, "secondary"),
    AssessmentStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    AssessmentStatus.COMPLETED: (True, False, False, False, False, "info"),
    AssessmentStatus.VALIDATED: (True, False, False, False, False, "success"),
    AssessmentStatus.ARCHIVED: (False, False, False, False, True, "dark"),
}

_RISK_ASSESSMENT_TRANSITIONS = [
    (AssessmentStatus.DRAFT, AssessmentStatus.IN_PROGRESS),
    (AssessmentStatus.IN_PROGRESS, AssessmentStatus.COMPLETED),
    # A completed campaign found lacking returns to work.
    (AssessmentStatus.COMPLETED, AssessmentStatus.IN_PROGRESS),
    (AssessmentStatus.COMPLETED, AssessmentStatus.VALIDATED, {"action": "approve"}),
    (AssessmentStatus.VALIDATED, AssessmentStatus.ARCHIVED, {"action": "approve"}),
]


# ── EBIOS RM deliverables ──────────────────────────────────
#
# Workshop reviews carry the dedicated `validate` permission action
# (`risks.ebios_assessment.validate`); rejecting a workshop requires a
# comment. The study framework and summary keep `is_approved` as an
# independent axis (explicit opt-out: their draft / validated state names
# would otherwise trip the subsumes-approval heuristic and fight the
# status sync).

EBIOS_WORKSHOP_WORKFLOW_NAME = "ebios_workshop"
EBIOS_STUDY_FRAMEWORK_WORKFLOW_NAME = "ebios_study_framework"
EBIOS_SECURITY_BASELINE_WORKFLOW_NAME = "ebios_security_baseline"
EBIOS_SUMMARY_WORKFLOW_NAME = "ebios_summary"
EBIOS_BASELINE_GAP_WORKFLOW_NAME = "ebios_baseline_gap"
EBIOS_PACS_MEASURE_WORKFLOW_NAME = "ebios_pacs_measure"

_EBIOS_WORKSHOP_STATE_FLAGS = {
    EbiosWorkshopStatus.NOT_STARTED: (True, False, True, True, False, "secondary"),
    EbiosWorkshopStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    EbiosWorkshopStatus.UNDER_REVIEW: (True, False, False, False, False, "warning"),
    EbiosWorkshopStatus.VALIDATED: (True, False, False, False, True, "success"),
    EbiosWorkshopStatus.REJECTED: (True, False, False, False, False, "danger"),
}

_EBIOS_WORKSHOP_TRANSITIONS = [
    (EbiosWorkshopStatus.NOT_STARTED, EbiosWorkshopStatus.IN_PROGRESS),
    (EbiosWorkshopStatus.IN_PROGRESS, EbiosWorkshopStatus.UNDER_REVIEW),
    (EbiosWorkshopStatus.UNDER_REVIEW, EbiosWorkshopStatus.VALIDATED, {"action": "validate"}),
    (
        EbiosWorkshopStatus.UNDER_REVIEW,
        EbiosWorkshopStatus.REJECTED,
        {"action": "validate", "requires_comment": True},
    ),
    (EbiosWorkshopStatus.REJECTED, EbiosWorkshopStatus.IN_PROGRESS),
]

_EBIOS_STUDY_FRAMEWORK_STATE_FLAGS = {
    EbiosStudyFrameworkStatus.DRAFT: (True, False, True, True, False, "secondary"),
    EbiosStudyFrameworkStatus.VALIDATED: (True, False, False, False, True, "success"),
}

_EBIOS_STUDY_FRAMEWORK_TRANSITIONS = [
    (
        EbiosStudyFrameworkStatus.DRAFT,
        EbiosStudyFrameworkStatus.VALIDATED,
        {"action": "validate"},
    ),
]

_EBIOS_SECURITY_BASELINE_STATE_FLAGS = {
    EbiosBaselineStatus.DRAFT: (True, False, True, True, False, "secondary"),
    EbiosBaselineStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    EbiosBaselineStatus.COMPLETED: (True, False, False, False, True, "success"),
}

_EBIOS_SECURITY_BASELINE_TRANSITIONS = [
    (EbiosBaselineStatus.DRAFT, EbiosBaselineStatus.IN_PROGRESS),
    (EbiosBaselineStatus.IN_PROGRESS, EbiosBaselineStatus.COMPLETED),
]

_EBIOS_SUMMARY_STATE_FLAGS = {
    EbiosSummaryStatus.DRAFT: (True, False, True, True, False, "secondary"),
    EbiosSummaryStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    EbiosSummaryStatus.UNDER_REVIEW: (True, False, False, False, False, "warning"),
    EbiosSummaryStatus.VALIDATED: (True, False, False, False, True, "success"),
}

_EBIOS_SUMMARY_TRANSITIONS = [
    (EbiosSummaryStatus.DRAFT, EbiosSummaryStatus.IN_PROGRESS),
    (EbiosSummaryStatus.IN_PROGRESS, EbiosSummaryStatus.UNDER_REVIEW),
    (EbiosSummaryStatus.UNDER_REVIEW, EbiosSummaryStatus.VALIDATED, {"action": "approve"}),
    (EbiosSummaryStatus.UNDER_REVIEW, EbiosSummaryStatus.IN_PROGRESS),
]

_EBIOS_BASELINE_GAP_STATE_FLAGS = {
    BaselineGapStatus.IDENTIFIED: (True, False, True, True, False, "secondary"),
    BaselineGapStatus.ACCEPTED: (True, False, False, False, False, "info"),
    BaselineGapStatus.IN_REMEDIATION: (True, False, False, False, False, "warning"),
    BaselineGapStatus.REMEDIATED: (True, False, False, False, True, "success"),
}

_EBIOS_BASELINE_GAP_TRANSITIONS = [
    (BaselineGapStatus.IDENTIFIED, BaselineGapStatus.ACCEPTED),
    (BaselineGapStatus.IDENTIFIED, BaselineGapStatus.IN_REMEDIATION),
    # An accepted deviation can later be scheduled for remediation.
    (BaselineGapStatus.ACCEPTED, BaselineGapStatus.IN_REMEDIATION),
    (BaselineGapStatus.IN_REMEDIATION, BaselineGapStatus.REMEDIATED),
]

_EBIOS_PACS_MEASURE_STATE_FLAGS = {
    PACSMeasureStatus.PLANNED: (True, False, True, True, False, "info"),
    PACSMeasureStatus.IN_PROGRESS: (True, False, False, False, False, "primary"),
    PACSMeasureStatus.OVERDUE: (True, False, False, False, False, "danger"),
    PACSMeasureStatus.COMPLETED: (True, False, False, False, True, "success"),
    PACSMeasureStatus.CANCELLED: (False, False, False, False, True, "danger"),
}

_EBIOS_PACS_MEASURE_TRANSITIONS = [
    (PACSMeasureStatus.PLANNED, PACSMeasureStatus.IN_PROGRESS),
    (PACSMeasureStatus.IN_PROGRESS, PACSMeasureStatus.COMPLETED),
    (PACSMeasureStatus.PLANNED, PACSMeasureStatus.OVERDUE),
    (PACSMeasureStatus.IN_PROGRESS, PACSMeasureStatus.OVERDUE),
    (PACSMeasureStatus.OVERDUE, PACSMeasureStatus.IN_PROGRESS),
    (PACSMeasureStatus.OVERDUE, PACSMeasureStatus.COMPLETED),
    (PACSMeasureStatus.PLANNED, PACSMeasureStatus.CANCELLED),
    (PACSMeasureStatus.IN_PROGRESS, PACSMeasureStatus.CANCELLED),
    (PACSMeasureStatus.OVERDUE, PACSMeasureStatus.CANCELLED),
]

_DEFINITIONS = [
    (RISK_WORKFLOW_NAME, RiskStatus, _RISK_STATE_FLAGS, _RISK_TRANSITIONS, None),
    (
        RISK_ASSESSMENT_WORKFLOW_NAME,
        AssessmentStatus,
        _RISK_ASSESSMENT_STATE_FLAGS,
        _RISK_ASSESSMENT_TRANSITIONS,
        False,  # is_approved / validated_by stay independent of the states
    ),
    (
        TREATMENT_PLAN_WORKFLOW_NAME,
        TreatmentPlanStatus,
        _TREATMENT_PLAN_STATE_FLAGS,
        _TREATMENT_PLAN_TRANSITIONS,
        None,
    ),
    (
        ACCEPTANCE_WORKFLOW_NAME,
        AcceptanceStatus,
        _ACCEPTANCE_STATE_FLAGS,
        _ACCEPTANCE_TRANSITIONS,
        None,
    ),
    (
        VULNERABILITY_WORKFLOW_NAME,
        VulnerabilityStatus,
        _VULNERABILITY_STATE_FLAGS,
        _VULNERABILITY_TRANSITIONS,
        None,
    ),
    (
        EBIOS_WORKSHOP_WORKFLOW_NAME,
        EbiosWorkshopStatus,
        _EBIOS_WORKSHOP_STATE_FLAGS,
        _EBIOS_WORKSHOP_TRANSITIONS,
        None,
    ),
    (
        EBIOS_STUDY_FRAMEWORK_WORKFLOW_NAME,
        EbiosStudyFrameworkStatus,
        _EBIOS_STUDY_FRAMEWORK_STATE_FLAGS,
        _EBIOS_STUDY_FRAMEWORK_TRANSITIONS,
        False,  # is_approved stays independent of the draft/validated states
    ),
    (
        EBIOS_SECURITY_BASELINE_WORKFLOW_NAME,
        EbiosBaselineStatus,
        _EBIOS_SECURITY_BASELINE_STATE_FLAGS,
        _EBIOS_SECURITY_BASELINE_TRANSITIONS,
        None,
    ),
    (
        EBIOS_SUMMARY_WORKFLOW_NAME,
        EbiosSummaryStatus,
        _EBIOS_SUMMARY_STATE_FLAGS,
        _EBIOS_SUMMARY_TRANSITIONS,
        False,  # is_approved stays independent of the draft/validated states
    ),
    (
        EBIOS_BASELINE_GAP_WORKFLOW_NAME,
        BaselineGapStatus,
        _EBIOS_BASELINE_GAP_STATE_FLAGS,
        _EBIOS_BASELINE_GAP_TRANSITIONS,
        None,
    ),
    (
        EBIOS_PACS_MEASURE_WORKFLOW_NAME,
        PACSMeasureStatus,
        _EBIOS_PACS_MEASURE_STATE_FLAGS,
        _EBIOS_PACS_MEASURE_TRANSITIONS,
        None,
    ),
]

for _name, _enum, _flags, _pairs, _subsumes in _DEFINITIONS:
    if _name not in WORKFLOW_REGISTRY:
        register_workflow(
            _build(_name, _enum, _flags, _pairs, subsumes_approval=_subsumes)
        )
