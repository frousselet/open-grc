# Lifecycle workflow framework

`core.workflow` - implemented by the `workflow-framework` chantier (issue #105, PR #106).

Every domain element runs a **lifecycle workflow**: an ordered set of states with the
allowed transitions between them. Governance is metadata carried by each state, so the
cross-cutting rules (inclusion in reports / KPIs / the calendar, linking, deletion,
notifications) read state flags instead of hardcoded status values. This framework
replaced the two historical mechanisms: the boolean approval workflow
(`is_approved` on `BaseModel`) and the per-model `status` state machines.

## Architecture

Declared in code, assigned per model, governed by flags:

- **`State`** : `code`, translatable `label`, UI `tone` (badge colour), `branch`
  (off-ramp states like cancelled / archived, drawn below the stepper's main flow),
  and the governance flags:
  - `counts_in_reports` - included in reports, KPIs, the calendar and exports;
  - `linkable` - may be targeted by a new link;
  - `deletable` - may be deleted;
  - `is_initial` (exactly one per workflow) / `is_terminal` (at least one per workflow,
    no outgoing transition).
- **`Transition`** : `source`, `target`, translatable `verb`, `action` (permission
  action suffix, resolved against the entity's `module.feature` namespace),
  `requires_comment`, declarative `effects` (`notify_owner`, `stamp_validation`).
- **`Workflow`** : name + states + transitions; invariants validated at construction.
  `subsumes_approval` is true for default-lifecycle-shaped workflows (both `draft`
  and `validated` states): there the legacy `is_approved` flag mirrors the state.
  Workflows whose state names merely overlap opt out explicitly via the constructor.
- **`WORKFLOW_REGISTRY`** : name -> workflow. Specific workflows are registered from
  each app's `AppConfig.ready()` (`compliance/workflows.py`, `reports/workflows.py`,
  `risks/workflows.py`, `assets/workflows.py`).
- **Assignment** : `VersioningConfig.workflow_name` (DB, explicit admin override)
  takes precedence over the model's `WORKFLOW_NAME` class attribute, which falls
  back to the default workflow.

Model API (`context.models.base.BaseModel`): `workflow_state` field (indexed),
`get_workflow()`, `get_lifecycle_state()`, `lifecycle_label`, the governance
properties (`counts_in_reports`, `is_linkable`, `is_deletable`),
`available_transitions(user)`, `transition_to(target, user, comment=...)` and a
`workflow_perm_namespace` property (overridden where the permission feature differs
from the model name, e.g. `compliance.action_plan`).

Queryset helpers: `reportable(qs)`, `linkable(qs)`, `linkable_or_linked(qs, linked_qs)`
plus the state-set functions (`reportable_states`, `linkable_states`,
`deletable_states`). All no-op for models without a lifecycle (plain child models).

## The default workflow (`default_lifecycle`)

Applies to every model without a specific workflow.

| State | In reports | Linkable | Deletable | Branch | Terminal |
|---|---|---|---|---|---|
| `draft` (initial) | no | no | **yes** | no | no |
| `pending` | no | no | no | no | no |
| `validated` | **yes** | **yes** | no | no | no |
| `archived` | no | no | no | yes | yes |

| Verb | Transition | Permission | Effects |
|---|---|---|---|
| Submit | draft -> pending | `.update` | `notify_owner` |
| Send back to draft | pending -> draft | `.update` | - |
| Validate | pending -> validated | `.approve` | `stamp_validation` |
| Archive | validated -> archived | `.approve` | - |

On default-workflow models the approval axis is subsumed: `is_approved` mirrors
`workflow_state == "validated"` both ways (the save sync promotes a freshly approved
draft and demotes an unapproved validated element). Major-field edits keep the
historical behaviour: approval reset + version increment via `VersioningConfig`.

## Specific workflows

Fifteen registered workflows preserve the operational semantics that the 4-state
lifecycle does not cover. State codes equal the legacy status values, so the data
migrations were identity copies; the legacy `status` field is kept in sync with
`workflow_state` both ways during the migration period
(`core.workflow.sync_legacy_status`), and `is_approved` stays an **independent
approval axis** (no specific workflow subsumes it).

| Workflow | Model | Highlights |
|---|---|---|
| `action_plan` | compliance.ComplianceActionPlan | 8 states from the legacy constants; refusals require a comment; per-step permissions (`update`, `validate`, `implement`, `close`, `cancel`); `to_implement` / `implementation_to_validate` / `validated` linkable; `new` / `to_define` deletable; transitions logged in `ActionPlanTransition` |
| `compliance_assessment` | compliance.ComplianceAssessment | only `draft` deletable; `cancelled` leaves reports / the calendar; EVALUATED-results reset on completion preserved |
| `management_review` | reports.ManagementReview | closure (`held -> closed`) carries `.approve`; cancellation requires a comment; `can_close()` preconditions and the closure snapshot preserved |
| `essential_asset` / `support_asset` | assets | natural ITAM progressions; decommissioned / disposed not linkable (declarative RS-04) and not deletable; every state stays reportable (audit history) |
| `risk` | risks.Risk | `identified` is the draft analog (not in the register, not linkable); monitoring -> analysis review loop; `closed` terminal but reportable |
| `risk_treatment_plan` | risks.RiskTreatmentPlan | automated overdue flip preserved; `cancelled` leaves reports |
| `risk_acceptance` | risks.RiskAcceptance | renewal cycle; `revoked` terminal; every state reportable (audit trail) |
| `vulnerability` | risks.Vulnerability | direct false-positive closure |
| `risk_assessment` | risks.RiskAssessment | rework loop from `completed`; validation / archiving on `.approve`; `validated_by` stamp independent |
| `ebios_workshop` | risks (EBIOS) | review verdicts on `.validate` (`risks.ebios_assessment.validate`); rejection requires a comment; rework loop |
| `ebios_study_framework`, `ebios_security_baseline`, `ebios_summary`, `ebios_baseline_gap`, `ebios_pacs_measure` | risks (EBIOS) | natural deliverable progressions; the study framework and summary opt out of `subsumes_approval` explicitly |

Decisions recorded during the rollout:

- **Binary toggles** (Stakeholder, Role, Activity, AssetGroup, Threat, Indicator) and
  **outcome trackers** (Objective, Issue, StakeholderFeedback) keep their `status` as a
  non-governing operational attribute over the default lifecycle. A toggle has no
  terminal state, so it is not a lifecycle.
- **Publication statuses retired**: Scope, Site, SwotAnalysis and RiskCriteria lost
  their `status` field entirely (`active` / `validated` folded into `validated`,
  `archived` kept). Framework and Requirement keep `status` as a versioning attribute
  (`under_review` / `deprecated` / `superseded` carry semantics the lifecycle does not).

## Governance rules (as built)

- **RG-LC-01** : an element whose state has `counts_in_reports = false` is excluded
  from generated reports (SoA, risk register), computed KPI rates, the compliance
  donut and the calendar. Dashboard inventory count tiles deliberately stay full
  (product decision: counts are a working inventory). Assessment-scoped documents
  (audit report, ISO 27005, management review exports) keep the full content of the
  explicitly chosen assessment.
- **RG-LC-03 / RG-LC-04 (target-side linking)** : a new link may only target a
  `linkable` element; already-linked elements stay selectable so an edit never drops
  an existing link; an element in a terminal state cannot gain new links; unlinking
  is always allowed. Authoring links *from* a draft element is allowed by design
  (the validator reviews the element with its links).
- **RG-LC-05** : deletion is blocked at the model level (`BaseModel.delete()` raises
  `LifecycleProtectedError`) unless the state is `deletable`. Cascade and bulk
  deletes bypass it by design.
- **RG-LC-06 / RG-LC-09 (notifications)** : transitions carrying `notify_owner`
  (Submit on the default workflow) notify, in fallback order: the element's own
  `managers` (scope-like containers), the managers of its scopes, the holders of the
  entity's `.approve` permission, then the creator. The actor and inactive users are
  never notified. Delivery: in-app `accounts.Notification` rows (rendered in the
  recipient's language) + email on `transaction.on_commit` (per-user
  `email_notifications` opt-out) + a per-user WebSocket badge push
  (`/ws/notifications/`).
- **RG-LC-07** : each transition requires its declared permission action, resolved
  against the entity's `module.feature` namespace.

## Surfaces

- **REST** : `GET /api/v1/<entity>/<pk>/transition/` lists the caller's permitted
  transitions; `POST` performs one (`target_status`, optional `comment`). Lifecycle
  lists accept `?workflow_state=a,b`. Provided by `ApprovableAPIMixin`; the bespoke
  transition endpoints (assessment required-fields gating, action plan, management
  review closure) keep their extra side effects and shadow the generic action.
  `/approve/` and `/reject/` are deprecated aliases that refuse terminal states.
- **MCP** : `transition_<entity>(id, target_state, comment)` and
  `<entity>_allowed_transitions(id)` for every CRUD entity; `approve_<entity>` is a
  deprecated alias. Link tools enforce the linking rules with explicit error lists.
- **UI** : every detail page renders the generic stepper
  (`includes/workflow_stepper.html`, context built by
  `accounts.mixins.WorkflowStepperMixin`) - main flow pills, permission-aware next
  step, refusal / rework button, branch off-ramp, shared comment modal gated by each
  transition's `requires_comment`. Transitions post to `workflow:transition`
  (`/workflow/<app>/<model>/<pk>/transition/`, validated-referer redirect) or to the
  entity's bespoke endpoint (`workflow_transition_url_name`). State badges render
  via `{% workflow_badge obj %}` (`helpers.templatetags.workflow_tags`).

## Follow-ups

- Retire the `is_approved` / `approved_by` / `approved_at` columns once the
  deprecation window for the `approve_*` aliases closes (needs a history-aware
  migration; ~200 read sites still display the flag).
- The remaining `?status=` list filters on kept-status models are untouched;
  lifecycle filtering is uniform via `?workflow_state=`.
