# Changelog

All notable changes to Fairway are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- EBIOS RM GUI W2-W5: full pages for workshops 2 to 5 replacing the placeholders. W2 lists risk sources with their auto-computed ANSSI threat level V1..V4 badge, the targeted objectives nested per source and the SR/OV pairs with their priority score. W3 shows the ecosystem stakeholders with their threat zone badge (control / monitoring / danger) and the strategic scenarios with their attack path steps. W4 shows the operational scenarios with inline attack technique chips, the inherited gravity flag and a one-click consolidation button that materialises the scenario into a Risk in the unified register (idempotent). W5 shows the EbiosSummary detail card with edit form, the before/after risk mapping snapshots with capture buttons per slot, and the PACS measures table. 30+ new URL routes under `/risks/assessments/<uuid>/ebios/{risk-sources,sr-ov-pairs,ecosystem,strategic-scenarios,operational-scenarios}/create/` and `/risks/ebios/<entity>/<uuid>/{edit,delete}/`. The W4 page also exposes a per-scenario `consolidate` POST that mirrors the API action. 10 new tests in `risks/tests/test_ebios_views.TestWorkshopW2W5Views` covering the dispatcher templates, the create flows for risk sources / ecosystem stakeholders / PACS measures, the consolidate idempotency and the capture-mappings slot toggle
- EBIOS RM GUI foundation: clickable workshop stepper on the assessment detail page (each W0..W5 pill now links to the workshop page), workshop transition CTAs (`Start workshop`, `Submit for review`, `Validate workshop`, `Reject workshop` with mandatory reason modal), porte-de-validation enforcement (workshop N can only be started after workshop N-1 is validated). Workshop detail page with a 2-column layout (entities + form / status sidebar) and a dispatcher view picking the right template per workshop_number. Full pages for W0 (study framework view + dedicated edit form covering mission, perimeters, participants, applicable frameworks) and W1 (security baseline summary + inline feared events and baseline gaps with create/edit/delete forms). Placeholder pages for W2..W5 announcing the API/MCP surfaces. New URL namespace under `/risks/assessments/<uuid>/ebios/workshops/<uuid>/{start,submit,validate,reject}/` and `/risks/ebios/{study-frameworks,baselines,feared-events,gaps}/<uuid>/edit/`. 15 new tests in `risks/tests/test_ebios_views.py` covering the dispatcher template selection, the four transitions with their porte-de-validation, the W0 form submission and the W1 inline forms
- EBIOS RM (ANSSI v1.5) workshop W5: new models `EbiosSummary` (ESUM) and `PACSMeasure` (EPAC). `EbiosSummary` is auto-created by the post_save signal on ebios_rm assessments (the signal now bootstraps StudyFramework + SecurityBaseline + EbiosSummary + the six EbiosWorkshopProgress rows). It holds the residual risk strategy, monitoring plan, PACS narrative summary and two JSON snapshots `risk_mapping_before` / `risk_mapping_after` captured on demand via the `capture_risk_mappings(capture_before=True, capture_after=True)` method. The snapshot shape aggregates the assessment's risk register into stable counters (total + by_status + by_priority + by_initial / current / residual_risk_level) so the UI can render the before-vs-after cartography without re-querying. `PACSMeasure` is the structured measure of the Plan d'Amélioration Continue de la Sécurité with type (governance / protection / defense / resilience / awareness), owner, target date, cost estimate, expected gain, priority, status and progress percentage. It links to `RiskTreatmentPlan`, `BaselineGap` and compliance `Requirement` so the PACS doubles as a treatment roadmap and a traceability matrix. REST endpoints `/api/v1/risks/ebios/{summaries,pacs-measures}/` with filters by assessment, measure_type, priority, status and target_date. Custom action `POST /summaries/{id}/capture-mappings/` (parameters `capture_before` / `capture_after`) triggers the snapshot from the API. 13 new MCP tools including `capture_ebios_risk_mappings`. Coverage: 10 new tests in `risks/tests/test_ebios_w5_models.py` (bootstrap signal extended, snapshot shape, slot-level capture isolation, PACSMeasure linkage matrix) and 5 new tests in `risks/tests/test_ebios_api.py` (auto-creation, capture endpoint, PACS filter)
- EBIOS RM (ANSSI v1.5) workshop W4: new models `MitreAttackTechnique`, `OperationalScenario` (EOPS) and `AttackTechnique` (EATT). `MitreAttackTechnique` is the shared MITRE ATT&CK Enterprise Matrix catalogue, seeded via data migration `risks.0022_seed_mitre_attack_catalog` from `risks/fixtures/mitre_attack_v15.json` (curated subset of v15.1 covering the 14 tactics) and refreshable with the new management command `python manage.py refresh_mitre_attack [path]`. `OperationalScenario` declines a strategic scenario into a technical sequence and inherits `gravity_level` from its parent by default (`gravity_inherited` flag with mandatory override justification when set to false). `likelihood_v` is the ANSSI V1..V4 operational scale stored as integer 1..4 and fed into the assessment risk matrix to compute `risk_level`. `AttackTechnique` enforces a XOR constraint at `full_clean()` (MITRE FK or `custom_name`) and uniqueness on `(scenario, order)`. REST endpoints under `/api/v1/risks/ebios/{mitre-techniques,operational-scenarios,attack-techniques}/`. Custom actions: `POST /operational-scenarios/{id}/consolidate/` (idempotent materialisation into the unified Risk register with auto-filled scoring and criteria_snapshot copy) and `GET /operational-scenarios/mitre-heatmap/?assessment=<uuid>` (heatmap grouped by tactic for visualisation). 26 new MCP tools including `consolidate_ebios_operational_scenario_to_risk`. Coverage: 14 new tests in `risks/tests/test_ebios_w4_models.py` and 8 new tests in `risks/tests/test_ebios_api.py` (consolidate idempotency, heatmap aggregation, MITRE filter, XOR constraint and inheritance flow)
- EBIOS RM (ANSSI v1.5) workshop W3: new models `EcosystemStakeholder` (EECS), `StrategicScenario` (ESTS) and `AttackPathStep` (EAPS). `EcosystemStakeholder.threat_level` is auto-computed at save() as `(dependency * penetration) / (maturity * trust)` and the `threat_zone` (control / monitoring / danger) is derived from `DEFAULT_ECOSYSTEM_THRESHOLDS` (0.5 / 1.5), both overridable per assessment through `RiskCriteria.risk_matrix["ebios_ecosystem_thresholds"]` and frozen in `criteria_snapshot` at first scoring. `StrategicScenario.risk_level` is computed via the assessment risk matrix (likelihood x gravity) with the same immutable snapshot pattern. `AttackPathStep` enforces a unique `(scenario, order)` constraint and exposes an `action_type` taxonomy (initial access, lateral movement, exfiltration, ...). REST endpoints under `/api/v1/risks/ebios/{ecosystem-stakeholders,strategic-scenarios,attack-path-steps}/` with filters by threat zone, attack vector, risk level, gravity and likelihood. Custom action `GET /ecosystem-stakeholders/graph/?assessment=<uuid>` returns the ecosystem as nodes + edges + zone metadata, ready for a graph viewer. 25 new MCP tools (CRUD + batch + approve for ecosystem and strategic scenario). Coverage: 26 new tests in `risks/tests/test_ebios_w3_models.py` including the 5 sample formula cells, the threshold boundaries and the criteria snapshot freeze
- EBIOS RM (ANSSI v1.5) workshop W2: new models `RiskSource` (ERSC), `TargetedObjective` (ETOV) and `RiskSourceObjectivePair` (ESOV). `RiskSource.threat_level` is auto-computed at save() from `(motivation_level, resources_level, activity_level)` via the ANSSI Grid A documented in M4bis spec §2.8 (V1..V4 scale). The grid is overridable per assessment through `RiskCriteria.risk_matrix["ebios_threat_grid"]` and frozen in `criteria_snapshot` at first scoring so historical scores stay immutable. SR/OV pairs carry a `priority_score = max(threat_level, relevance_weight)` recomputed on save and a unique constraint per `(assessment, risk_source, targeted_objective)`. REST endpoints under `/api/v1/risks/ebios/{risk-sources,targeted-objectives,sr-ov-pairs}/` with filters by category, retention, threat level, relevance and priority score; 21 new MCP tools (CRUD + batch + approve for SR and SR/OV pair). Coverage: 35 new tests in `risks/tests/test_ebios_w2_models.py` including the 16 cells of Grid A
- EBIOS RM (ANSSI v1.5) foundation (workshops W0 and W1): new sub-package `risks/models/ebios/` with `StudyFramework` (EFRA), `EbiosWorkshopProgress` (EWSP), `SecurityBaseline` (EBSL), `FearedEvent` (EFER) and `BaselineGap` (EBGP). A `post_save` signal on `RiskAssessment` automatically bootstraps one study framework, one security baseline and six workshop progress trackers (W0..W5, strategic cycle, iteration 1) whenever an assessment with `methodology = ebios_rm` is saved
- EBIOS RM REST API under `/api/v1/risks/ebios/` for study frameworks, workshops, baselines, feared events and baseline gaps, with filters per assessment, DIC criterion, severity and status
- 31 new MCP tools covering CRUD plus batch-create on every W0/W1 entity (`list_*`, `get_*`, `create_*`, `update_*`, `delete_*`, `batch_create_*` and `approve_ebios_security_baseline`)
- 7 new permission features under `risks` module (`ebios_assessment`, `ebios_baseline`, `ebios_risk_source`, `ebios_ecosystem`, `ebios_strategic`, `ebios_operational`, `ebios_summary`) covering workshops W0 to W5 in one shot, with sensible grants for each of the six system groups
- EBIOS RM workshop stepper component (`risks/templates/risks/ebios/_workshop_stepper.html`) rendered on the assessment detail page when `methodology = ebios_rm`, replacing the previous static placeholder. It shows the live status of W0..W5 with light/dark-aware styling
- `M4bis_EBIOS_RM_Specifications.md` ANSSI-aligned spec replacing section 4 of the M4 document. Covers the 16 EBIOS entities, ANSSI scoring grids (motivation x ressources x activite, threat zone (dependency x penetration) / (maturity x trust), V1-V4 likelihood), iterative cycles (strategic vs operational) and validation gates per workshop
- Persistent management review workflow (ISO 27001:2022 clause 9.3) with full life cycle (planned, in_preparation, held, closed, cancelled), horizontal stepper, snapshot-based auditability, and 2-column detail layout
- `ManagementReview` model (title, frequency, period, planned/held dates, facilitator, approver, scopes, agenda, summary, next review date)
- `ManagementReviewDecision` for clause 9.3.3 outputs, with category, input clause, owner, due date, priority, status, and promote-to-action-plan flow
- `IsmsChange` for recording scope/policy/control/resource changes decided during reviews (clause 9.3.3)
- `ManagementReviewParticipant` (internal + external) with attendance tracking and signature fields
- `ManagementReviewComment` and `ManagementReviewTransition` for audit trail
- `StakeholderFeedback` in the context app (formal feedback channel, clause 9.3.2.e) with channel, sentiment, severity, and status
- Retrochaining FKs (`originating_review`) on `ComplianceActionPlan`, `RiskTreatmentPlan`, and `Objective`
- REST API under `/api/v1/reports/management-reviews/`, `/api/v1/reports/decisions/`, `/api/v1/reports/isms-changes/`, and `/api/v1/context/stakeholder-feedback/`
- Ten new MCP tools: `list_management_reviews`, `get_management_review`, `create_management_review`, `transition_management_review`, `export_management_review`, `list_management_review_decisions`, `create_management_review_decision`, `promote_decision_to_action_plan`, `list_isms_changes`, `create_isms_change`, `list_stakeholder_feedback`, `create_stakeholder_feedback`
- New permissions `reports.management_review.{create,read,update,delete,approve}` and `context.stakeholder_feedback.{create,read,update,delete}`, auto-assigned to the six system groups
- Enhanced PPTX/DOCX export consumes a persistent review: adds decisions and ISMS changes sections, pre-fills signatures from participants, replaces placeholders with actual summary and next review date
- Graphical (non-eIDAS) participant signature: PNG/JPEG upload (max 500 KB) per participant, stored as a base64 data URI, embedded as an actual image in the DOCX signature table
- MCP tool `set_participant_signature` to attach a signature data URI programmatically
- "Management reviews" link added to the main sidebar navigation
- Test suites `test_management_review_api.py` and `test_management_review_mcp.py` covering the REST and MCP surfaces, plus participant signature tests in `test_management_review.py`
- Approval workflow on `RiskAcceptance`: REST `approve` and `reject` actions, MCP tool `approve_risk_acceptance`, `/risks/acceptances/<pk>/approve/` UI endpoint with approval badge on the detail page
- New permission `risks.acceptance.approve` assigned by default to Super Administrateur, Administrateur and RSSI / DPO groups
- Tests for acceptance approval covering UI, REST and MCP surfaces, including a new `risks/tests/test_mcp.py`
- `Risk` and `ISO27005Risk` now freeze the risk matrix and criteria metadata (`criteria_snapshot` JSONField) at first evaluation, so later edits to `RiskCriteria` do not silently rewrite historical scores. A "Scoring snapshot" panel on the risk detail page surfaces the captured criteria name, version and timestamp
- Data migration `risks.0016_risk_criteria_snapshot` backfills `criteria_snapshot` for every already-evaluated risk and ISO 27005 analysis using the current state of its assessment's criteria
- M2M link between `RiskTreatmentPlan` and `compliance.ComplianceActionPlan` (`related_action_plans` / `related_treatment_plans`). The link is exposed on the treatment plan detail page, on the action plan detail page (Linkages section), in the REST serializer and through four MCP tools: `list_treatment_plan_action_plans`, `link_treatment_plan_action_plans`, `unlink_treatment_plan_action_plans`, `set_treatment_plan_action_plans`
- Risk register Excel (.xlsx) export at `GET /risks/register/export/xlsx/` and via the MCP tool `generate_risk_register`. The export honours the active scope, assessment, status and priority filters and is persisted as a `Report` of type `risk_register` for traceability. New `RISK_REGISTER` ReportType.
- Approval workflow extended to `Threat`, `Vulnerability` and `ISO27005Risk`: REST `approve`/`reject` actions, MCP tools `approve_threat`/`approve_vulnerability`/`approve_iso27005_risk`, `/<entity>/<pk>/approve/` UI endpoints, approval badge on each detail page. New permissions `risks.threat.approve`, `risks.vulnerability.approve`, `risks.iso27005.approve` granted by default to Super Administrateur, Administrateur and RSSI / DPO
- Factories for `Threat`, `Vulnerability`, `RiskAcceptance`, `RiskTreatmentPlan`, `TreatmentAction` and `ISO27005Risk` in `risks/tests/factories.py`, plus full approval-workflow coverage (REST + MCP + UI) for `RiskAssessment`, `Risk` and `RiskTreatmentPlan` to round out the suite started in P0-A1 and P0-B1
- Management command `expire_risk_acceptances` (sets `RiskAcceptance.status = EXPIRED` past `valid_until`, lists upcoming expirations within `--reminder-days`, supports `--dry-run`) and `mark_overdue_treatment_plans` (sets `RiskTreatmentPlan.status = OVERDUE` past `target_date`, supports `--dry-run`). Both are documented in the README as daily cron jobs.
- ISO 27005 risk assessment DOCX export at `GET /risks/assessments/<pk>/export/docx/` and via the MCP tool `generate_iso27005_report`. The report covers eight sections: context, risk criteria (scales, levels, matrix), threats, vulnerabilities, ISO 27005 analyses, consolidated risks, treatment plans and acceptances. Persisted as a `Report` of new type `iso27005_report`.

### Changed

- Management review export now accepts a `review` argument and hydrates from `snapshot_data` when the review is closed, ensuring exports remain immutable for audit purposes
- Management review templates use the `has_perm` template tag instead of `perms.reports.management_review.*` so dotted permission codenames resolve correctly through the custom permission backend
- Management review export query parameter renamed from `format` to `fmt` to avoid clashing with DRF's built-in renderer negotiation
- `RiskAcceptance` updates now reset approval and bump version like other approvable risk models, via `ApprovableUpdateMixin` (UI) and `ApprovableAPIMixin` (REST)
- `Risk.calculate_risk_level` and `ISO27005Risk.save` now consult `criteria_snapshot` first and fall back to the live `RiskCriteria.risk_matrix` only when no snapshot has been captured
- Statement of Applicability (SoA) PDF now lists the treated risks per control with their residual level (colour-coded low/medium/high pill) and treatment decision; when a requirement is applicable, has no action plan, but addresses linked risks, the justification falls back to "Selected to address linked risks." A small per-framework summary reports the total deduplicated risks addressed. The data-building step is exposed as a reusable `build_soa_frameworks_data` helper
- `/risks/` now shows a `RiskDashboardView` (was a redirect to `/risks/assessments/`): top counters, current and residual heatmaps, status / priority / treatment-decision distributions, top 10 critical risks, overdue treatment plans, and acceptances expiring within 90 days. Scope-filtered through the assessment's `scopes` M2M and guarded by `risks.risk.read`
- Advanced filters on the risk register list and REST endpoint: `treatment_decision` (chip row), `date_after` / `date_before` (creation date window), `essential_asset`, `support_asset`, `threat`, `vulnerability`, `linked_requirement`. The UI exposes them through a collapsible "Advanced filters" panel auto-opened when any of them is active
- REST endpoints for `TreatmentAction` (CRUD), `ScaleLevel` (read-only) and `RiskLevel` (read-only) under `/api/v1/risks/treatment-actions/`, `/api/v1/risks/scale-levels/`, `/api/v1/risks/risk-levels/`, with the matching filter sets
- `batch/` create endpoint added on the `RiskTreatmentPlan`, `RiskAcceptance` and `ISO27005Risk` viewsets so every writable risk resource now supports bulk ingest
- Inline add / edit / delete of `TreatmentAction` rows directly from the treatment plan detail page (HTMX-driven drawer form), gated by `risks.treatment.update`
- Bulk approve and bulk delete on the risk register list with select-all and a sticky toolbar; the server-side `RiskBulkActionView` scope-filters the queryset before acting and enforces `risks.risk.approve` / `risks.risk.delete`
- Sticky right sidebar on the four risks detail pages (assessment, risk, treatment plan, acceptance) so the metadata stays in view while the main content scrolls
- Test suite startup no longer replays the ~150 historical migrations: `core.settings_test` bypasses them with `MIGRATION_MODULES`, and a session-scoped `conftest.py` fixture re-seeds the `accounts.Permission` rows and the six system groups from `accounts.constants.PERMISSION_REGISTRY` / `SYSTEM_GROUPS`. Combined with `pytest-xdist` (`-n auto` on the CI matrix), the full suite drops from ~37 min to a few seconds per parallel job

### Fixed

- Management review decision and ISMS change REST serializers no longer require the `review` field on input ; it is populated from the nested URL parameter

## [0.22.0] - 2026-04-13

### Added

- Management review export (ISO 27001 clause 9.3) with two output formats : PowerPoint presentation and Word meeting minutes
- Seven structured sections : action plan status, internal/external issues, stakeholder needs, security performance (NC, indicators, audits, objectives), interested party feedback, risk assessment and treatment status, improvement opportunities
- Scope-based filtering for management review data
- Period date range filtering (start/end) for management review exports
- MCP tools `generate_management_review_pptx` and `generate_management_review_docx`
- REST API endpoint `POST /api/v1/reports/reports/generate-management-review/`
- New dependencies : `python-pptx` and `python-docx`

## [0.21.4] - 2026-04-01

### Added

- Changelog popup on dashboard : automatically displays a modal with all changes between the previously seen version and the current version when the app is updated
- `last_seen_version` field on User model to track the last version acknowledged by each user
- Changelog parser utility (`core/changelog.py`) to extract entries from `CHANGELOG.md` between two versions
- Dismiss endpoint (`POST /dashboard/changelog-dismiss/`) to mark the current version as seen

## [0.21.3] - 2026-03-26

### Added

- REST API batch creation endpoints (`POST /api/v1/<module>/<entity>/batch/`) for 10 entities: Requirement, Section, EssentialAsset, SupportAsset, AssetDependency, Threat, Vulnerability, Risk, Stakeholder, Supplier. Each endpoint accepts up to 100 items with partial success support (non-atomic)
- `BatchCreateMixin` reusable DRF mixin for adding batch creation to any ViewSet
- MCP `help` tool providing comprehensive usage documentation (call with no args for full guide, or with topic: context, assets, compliance, risks, batch, workflow, permissions, examples)

### Changed

- MCP batch creation tools now use non-atomic partial success instead of all-or-nothing transactions
- `SupplierDependencyType` choices updated: `provides`, `hosts`, `manages`, `develops`, `supports`, `licenses`, `maintains`, `other`
- `SiteSupplierDependencyType` choices updated to match SupplierDependencyType values

### Fixed

- Fix `Supplier.type` FK resolution in DRF serializer - explicitly declared as `PrimaryKeyRelatedField` for proper SupplierType lookup
- Fix `SupplierDependency.dependency_type` rejecting valid values other than `other`

## [0.21.2] - 2026-03-26

### Added

- `non_compliant` and `partially_compliant` choices for requirement `compliance_status`, enabling simple compliance tracking alongside detailed audit-oriented statuses
- MCP DIC level fields now accept text labels (`negligible`, `low`, `medium`, `high`, `critical`) in addition to integers (0-4)
- MCP batch creation tools (`batch_create_*`) for all entities, allowing up to 500 items per atomic transaction

### Fixed

- Fix `Supplier.type` FK resolution in MCP create/update handlers - string IDs are now properly coerced to integers for SupplierType lookup
- Fix MCP `create_supplier` / `update_supplier` handlers not calling `_coerce_field_value`, causing FK and type coercion failures
- Fix MCP supplier `type` field schema declaring `string`/UUID type instead of `integer` (SupplierType uses AutoField PK)

## [0.21.1] - 2026-03-26

### Added

- Scope managers : assign one or more responsible users to a scope (`Scope.managers` M2M). Managers automatically gain access to the scope even without group-based scope assignment. Available in UI, REST API, and MCP tools
- Reusable `{% user_badge %}` template tag displaying user avatar (with initials fallback) and display name, with configurable size, link, and layout options
- M2M relationship between action plans and requirements (`ComplianceActionPlan.requirements`), enabling linked requirements on action plan detail and requirement detail pages
- Generic M2M field support in MCP `_register_crud` create/update handlers (`m2m_fields` parameter)

### Changed

- Redesign all 16 detail pages to a consistent 2-column card layout (left content, right metadata sidebar) replacing tab-based layouts across context, compliance, risks and assets modules
- Replace all inline user field displays (`{{ obj.owner }}`, `{{ obj.approved_by }}`, etc.) with `{% user_badge %}` tag across 19 detail templates, showing avatar + real name
- MCP tool schemas now document all valid enum values for every choice field across all modules (context, assets, compliance, risks), with `enum` arrays in parameter definitions
- MCP tool schemas now declare `required` fields on create operations, aligned with Django model constraints
- MCP server returns detailed validation error messages instead of generic "Invalid params" / "Internal error" responses
- MCP DIC level fields (`confidentiality_level`, `integrity_level`, `availability_level`) now correctly declared as `integer` type with `enum: [0, 1, 2, 3, 4]` instead of `string`
- MCP supplier `type` field description clarified as a foreign key (UUID of SupplierType) instead of an enum
- Add `create` and `delete` actions to `assets.config` permissions, enabling MCP SupplierType management for non-superuser accounts

### Fixed

- Fix 500 error on requirement detail page caused by missing `action_plans` reverse relation

## [0.21.0] - 2026-03-25

### Added

- User impersonation for administrators (`system.users.impersonate` permission) with session-based switching, fixed amber banner, access log tracking, and security guards (no nesting)
- Robot user type: users can be marked as "Robot" (API/MCP-only accounts with no web login, optional first name, dedicated badge in UI)
- Trivy vulnerability scanning in CI security stage with GitLab container scanning report
- JUnit test report artifacts in CI
- Parallelize CI unit tests into one job per app directory (9 parallel jobs) with combined coverage report

## [0.20.0] - 2026-03-25

### Added

- Enforce RBAC permission checks on all UI views (~200 views across context, assets, compliance, risks and reports apps) via `PermissionRequiredMixin`
- Add parent-based scope filtering (`scope_parent_lookup`) for child models (Requirement, Risk, TreatmentPlan, Finding, etc.) in both UI and API
- Add RBAC (`ModulePermission`) to ReportViewSet and PermissionViewSet API endpoints
- Add `GroupDeleteView` with confirmation page, allowing deletion of any group (including system groups)
- Allow modification of system groups (name, permissions, users, scopes)
- Add ruff linter with syntax-focused config in pyproject.toml
- Split CI into quality (syntax, translations), test (unit), and deploy (docker-image) stages
- Add translations CI job to verify .po files compile without errors
- Add pip caching and Cobertura coverage artifact with MR badge regex
- Factor common CI rules into `.not-tags` YAML template

### Changed

- System groups are no longer locked: they can be edited, have their permissions changed, and be deleted like custom groups
- MCP `action_plan_transition` tool now requires `compliance.action_plan.update` permission instead of `.read`
- Remove all version pins from Docker images (Dockerfile, docker-compose, CI) to always use latest
- Remove all version constraints from Python dependencies in requirements.txt
- PostgreSQL volume mount changed from `/var/lib/postgresql/data` to `/var/lib/postgresql` (required by PostgreSQL 18+)

> **Warning:** The PostgreSQL volume layout changed. Existing deployments must dump and restore their database before upgrading:
>
> ```bash
> docker compose exec db pg_dumpall -U postgres > backup.sql
> docker compose down && docker volume rm <project>_postgres_data
> docker compose up -d
> docker compose exec -T db psql -U postgres < backup.sql
> ```

### Fixed

- Fix undefined `HttpResponseRedirect` in compliance views

## [0.19.1] - 2026-03-24

### Changed

- Redesign logo with a sailboat navigating a channel (fairway) replacing the old F-letter mark
- New logo features curved sails, wind pennant, sleek hull and accentuated waves
- Light, dark and 32x32 icon variants all updated along with all inline SVGs in templates

## [0.19.0] - 2026-03-24

### Changed

- Rebrand from Open GRC to Fairway across all user-facing strings, templates, documentation and CI/CD
- Replace Bootstrap shield icon with custom SVG logo (light/dark variants with inline SVG)
- Add favicon as inline data URI SVG
- Update GitLab registry and Docker Hub image paths to `fairway/fairway`
- Add `STATICFILES_DIRS` setting for project-level static assets

## [0.18.3] - 2026-03-24

### Added

- Branch workflow and git author guidelines in CLAUDE.md

## [0.18.2] - 2026-03-24

### Fixed

- Fix Docker CI job by setting DOCKER_HOST to mounted socket

## [0.18.1] - 2026-03-24

### Fixed

- Fix GitLab CI Docker build by using host Docker socket instead of DinD

## [0.18.0] - 2026-03-24

### Changed

- Switch Docker image publishing from Docker Hub to GitLab Container Registry

## [0.17.0] - 2026-03-24

### Added

- GitLab CI pipeline as primary CI alongside GitHub Actions
- Comprehensive CHANGELOG based on git history and tags
- CHANGELOG and README maintenance guidelines in CLAUDE.md

### Changed

- Set GitLab as primary git remote (origin), GitHub as secondary
- Revamp README with feature tables, MCP tools reference, and missing features list

## [0.16.0] - 2026-03-17

### Added

- Calendar spanning events with iCal subscription support and admin management

### Changed

- Rename ActionPlanStatus constants and DB values from French to English
- Unify action plan page titles between list and kanban views

### Fixed

- Fix AttributeError in MCP action_plan_transitions and kanban tools

## [0.15.0] - 2026-03-16

### Added

- Kanban board workflow for action plans with drag-and-drop status transitions
- Threaded comments on action plans with HTML rendering and user avatars
- Multi-assignee support with avatar display and comment count on Kanban cards
- Offcanvas drawer previews for linked risks and findings on action plans
- Visual workflow stepper for action plan status transitions

### Changed

- Redesign action plan detail page with two-column card layout replacing tabs
- Rename Owner to Supervisor with photo and full name display
- Use display_name (First Last) instead of email fallback for users
- Make kanban board the default view for action plans with full-width layout and scrollable columns

### Fixed

- Fix overdue action plan alert to use correct status values
- Fix MCP action plan tools with proper permissions, error handling, and workflow rules
- Fix drag-and-drop on kanban cards using Sortable.js forceFallback
- Fix French translation escaping in kanban JS

## [0.14.0 - 0.14.2] - 2026-03-13 to 2026-03-14

### Added

- Company settings management (logo, name, address) with report cover page branding
- "Cancelled" audit status with SVG branch lines in workflow stepper
- Confirmation dialog on assessment status transitions
- M2M support for framework_ids and requirement_ids in MCP compliance tools
- Missing reports permissions added to permission system

### Fixed

- Fix migration conflicts with merge migration for 0022 migrations
- Fix stepper layout to use flex instead of grid to prevent pill stretching
- Fix mobile stepper wrapping in single scrollable container
- Fix stats and status propagation for MCP compliance tools
- Clear stale __pycache__ in entrypoint to prevent migration conflicts

## [0.13.0] - 2026-03-13

### Added

- Audit report PDF generation with professional template design
- Scopes displayed as indented tree in audit report PDF
- Finding counts by type and impacted requirements count in report summary
- Assessment limitations field and result attachments
- Requirement body text in audit report finding detail cards

## [0.12.0 - 0.12.1] - 2026-03-13

### Added

- Multi-framework support per assessment with grouped requirements display
- Bulk toggle button to select/deselect all requirements for evaluation
- Visual workflow stepper on assessment detail page
- Per-status required field validation for assessment transitions
- Generic loading spinner for HTMX buttons, delete buttons, and approval actions
- Visual feedback on toggle click in assessment requirements

### Changed

- Revamp assessment workflow with new statuses and sequential transitions
- Exclude non-applicable requirements from coverage and compliance statistics
- Exclude EVALUATED status from compliance percentage calculation
- Auto-create AssessmentResults on assessment create/update
- Reorganize assessment detail with metadata in header, results merged into Planning tab
- Compute framework compliance from latest audit results by end date
- Compute dashboard compliance segments from assessment results

### Fixed

- Fix coverage calculation exceeding 100% for non-applicable requirements
- Fix bulk toggle to auto-initialize missing assessment results
- Fix calendar crash with correct field names for compliance assessments
- Fix dashboard compliance percentage to use computed values
- Fix coverage/compliance columns in assessment list to match detail view
- Redirect to edit form when transition requires missing fields

### Removed

- Remove methodology field from compliance assessments
- Remove per-theme dashboards

## [0.11.0 - 0.11.2] - 2026-03-10 to 2026-03-12

### Added

- SWOT matrix view with CRUD operations and user-defined TOWS strategies
- Logo support for compliance frameworks with dashboard display
- Findings (Constats) tab in compliance assessments with 3-state toggle
- Multi-color stacked progress bars for section compliance breakdown
- Coverage and compliance gauges on assessment detail page
- Audit-grade compliance status vocabulary

### Changed

- Redesign SWOT UI with strategies tab and context badges in matrix cells
- Rename compliance Assessments to Audits in menu and page titles
- Merge Summary tab into General tab on assessment detail page
- Use plain text fields for SWOT descriptions instead of HTML editor

### Fixed

- Fix HTMX delete buttons by adding global CSRF token header
- Fix blank drawer when clicking + on SWOT detail page
- Fix findings table HTML rendering and requirement badge centering
- Fix coverage mismatch by auto-creating AssessmentResult for requirements with findings
- Fix compliance gauge to compute dynamically from covered results only
- Fix finding delete not updating assessment results
- Fix duplicate translation entries in French .po file

## [0.10.0 - 0.10.2] - 2026-03-10

### Added

- Reports module with Statement of Applicability (SoA) PDF generation
- HTML rendering in SoA PDF justification column
- Natural sort for requirements in SoA export

### Fixed

- Fix WeasyPrint import with lazy loading to avoid missing system libs at startup
- Fix Dockerfile package name for gdk-pixbuf on Bookworm
- Fix SoA PDF generation by upgrading WeasyPrint for pydyf compatibility
- Fix SoA PDF download by storing file content in database
- Add media/ and staticfiles/ to .gitignore

## [0.9.0 - 0.9.1] - 2026-03-09 to 2026-03-10

### Added

- Interactive compliance evaluation UI with guided workflow
- Coverage % and compliance % columns in assessment list and detail
- Segmented compliance bars on dashboard using requirement-level status
- recalculate_compliance management command
- assessed_at, assessed_by_id, and observations fields in MCP assessment_result tool

### Changed

- Propagate assessment results to requirements, sections, and framework
- Show compliance from latest assessment on dashboards
- Treat not-assessed as 0% and not-applicable as 100% in compliance calculation

### Fixed

- Fix SPOF scheduler starting during management commands
- Fix dark theme and natural sort for assessment results table
- Fix swot_item MCP tool using wrong field names
- Fix phantom fields and missing required fields across 10 MCP tools
- Fix duplicate msgid entries in French translations

## [0.8.0] - 2026-03-09

### Added

- Versioning behavior management in Administration with translated field verbose names

### Fixed

- Fix versioning config form not saving by populating major_fields choices from POST data
- Standardize helpers display and add missing helper content
- Fix missing versioning_tags load in asset list templates

## [0.7.0 - 0.7.5] - 2026-03-07 to 2026-03-08

### Added

- HTMX offcanvas drawer forms for create/edit across all apps (context, risks, compliance, assets)
- Drawer modals for indicator create/edit forms
- OAuth token authentication added to REST Framework defaults
- logo_32 field in SupplierListSerializer for iOS app

### Changed

- Redesign drawer forms following Ant Design/Stripe/Linear patterns with metadata bar and single-column flow
- Convert list page header buttons to icon buttons, keeping only create button
- Change OAuthAuthorizationCode.redirect_uri from URLField to CharField for custom URL schemes

### Fixed

- Fix indicator values losing decimal precision on dashboard
- Fix indicator number input to accept locale-specific decimal formats
- Fix indicator decimal animation using raw numeric value
- Fix OAuth redirect to support custom URL schemes (e.g. opengrc://)
- Fix OAuth/JWT auth chain to return None instead of raising on unknown token

## [0.6.0] - 2026-03-06

### Added

- Global search bar with dynamic results grouped by item type

### Fixed

- Fix WebSocket proxy support with SECURE_PROXY_SSL_HEADER, CSRF_TRUSTED_ORIGINS, and AllowedHostsOriginValidator

## [0.5.0] - 2026-03-06

### Added

- WebSocket support for real-time dashboard updates
- Animated indicator cards with smooth counting animation on WebSocket value changes
- Sonar-style animated dot for WebSocket connection status
- Thousand separators preserved on indicator values during animations

## [0.4.5 - 0.4.8] - 2026-03-04 to 2026-03-06

### Added

- Image URL support for supplier logo upload via MCP
- Risk-to-requirement linking with ergonomic Tom Select UI and MCP tools
- Rich text editor (Jodit) with centralized dark theme support
- Sticky action bar with gradient fade on forms
- Sortable column header translations in all list views
- Floating user bubble in header with about modal
- Collapsible sidebar with icon-only mode, flyout sub-menus, and smooth animations
- Pill/chip-style table filters replacing select-based filters
- Stat card count-up animations and scroll-triggered progress bar animations

### Changed

- Redesign requirement form with grouped fields and two-column layout
- Render rich text as HTML in all detail templates
- Fullscreen dependency graph with zoom-to-fit default view and edge-to-edge layout
- Theme-aware form fields and Bootstrap components for dark mode
- Improve MCP tool descriptions for LLM clarity

### Fixed

- Fix AssessmentResult ordering after order field removal
- Fix card-header background leaking through rounded corners
- Fix mobile display for multi-select dropdowns
- Fix 5 MCP API issues blocking ISO 27005 risk assessment workflow
- Fix action logs 500 error on pagination by handling str() failures
- Fix sidebar collapse flash on page reload
- Fix flyout sub-menus disappearing when moving mouse to them
- Fix mobile sidebar layout and sub-menu alignment
- Fix dependency graph supplier nodes, gap, and legend alignment

### Removed

- Remove colored left border from indicator cards

## [0.4.2 - 0.4.4] - 2026-03-03 to 2026-03-04

### Added

- Server-side sorting and filtering for all list tables with persisted user preferences
- Natural sorting for references and requirement numbers
- Scope sorting with tree hierarchy and predefined filter chips
- Missing supplier, supplier_dependency, and indicator permissions
- Treatment_type and missing fields added to MCP risk tools
- Supplier logo support and missing fields in MCP tools

### Changed

- MCP OAuth tokens set to never expire
- Improve rights management GUI ergonomics

### Fixed

- Fix MCP disconnect by allowing DELETE without strict auth and revoking token
- Fix natural_sort_key array index for REGEXP_MATCHES result
- Fix SQLite compatibility for natural_sort_key migration

## [0.4.0 - 0.4.1] - 2026-03-03

### Added

- Indicators module with dashboard widget, user-configurable pinning, and sparkline charts
- Daily and weekly measurement frequencies for indicators
- Min/max critical thresholds with green/red/default card border status
- Persistent helper dismissal per user with reset in profile
- Toast notifications replacing inline alerts
- Tab persistence across page refresh via URL hash and sessionStorage
- Modern table design with dot-pill status badges
- User scopes displayed on all dashboard pages

### Changed

- Auto-generate reference fields and make them non-editable
- Reorder dashboard with overall compliance above SPOF and objectives progression
- Display 10 indicators (5 per line) with optional evolution chart
- Indicator cards use icons, locale-formatted numbers, and delta display
- Halve outer spacing around sidebar menu

### Fixed

- Fix migration ordering for auto-references before unique constraint
- Fix NameError from missing gettext_lazy import
- Fix tab underline alignment offset across all detail pages
- Fix sparkline draw animation on Safari
- Fix accounts migration dependency referencing nonexistent migration
- Replace PostgreSQL-specific RunSQL with database-agnostic RunPython
- Skip SPOF scheduler during test runs
- Fix MCP notification accumulation
- Fix indicator card width uniformity with CSS Grid

## [0.3.0 - 0.3.1] - 2026-03-02

### Added

- Integrated MCP server with OAuth 2.0 authentication (JSON-RPC 2.0)
- OAuth credential management UI in user profile page
- OAuth Authorization Code + PKCE flow for Claude.ai MCP integration

### Fixed

- Fix weak cryptographic hashing on sensitive data (code scanning alert #13)
- Fix information exposure through exceptions (code scanning alerts #11, #12)

## [0.2.12 - 0.2.16] - 2026-03-02

### Added

- Passkey (WebAuthn/FIDO2) authentication support
- Multi-scope support with hierarchical tree selector and breadcrumb-style badges
- Automatic SPOF detection service with 5 rules running at startup and every 5 minutes
- Compact count popover for scopes in list tables

### Fixed

- Fix passkey RP ID mismatch by deriving from request
- Fix passkey JS broken in French due to unescaped apostrophes
- Fix scope filtering for multi-scope M2M relationships
- Fix scope popover clipped by table-responsive overflow

## [0.2.7 - 0.2.11] - 2026-03-01

### Added

- User profile photo (avatar) support
- Auto-resize uploaded images to reduce DB and bandwidth load
- Missing help_modal tags added to 36 templates

### Changed

- Finalize interface modernization with pixel-perfect design polish
- Replace sidebar glassmorphism with clean solid style
- Redesign profile, supplier, and all form templates with multi-column grouped layouts
- Replace table action text buttons with icon buttons
- Replace sidebar footer dropdown with direct profile link and logout icon
- Store images and files as base64 data URIs in database instead of filesystem
- Round compliance percentages to whole numbers
- Improve dark theme sidebar text contrast and sub-menu colors

### Fixed

- Fix risk matrix padding, event alignment, and missing translations
- Fix supplier type creation by adding requirement formset to template
- Fix help_modal template tag syntax errors
- Crop non-square supplier logos with object-fit:cover

## [0.2.1 - 0.2.6] - 2026-03-01

### Added

- Floating mobile menu button with animated hamburger

### Changed

- Improve mobile responsive dashboard and add new KPIs
- Use version.txt for app version instead of git describe
- Bake APP_VERSION into Docker image via build arg
- Style sidebar as floating glass panel with backdrop blur

### Fixed

- Fix mobile menu overlap and overflow issues
- Fix version stuck on 0.2.0 by writing to /etc/app-version outside volume mount

## [0.2.0] - 2026-03-01

### Added

- Supplier management with dependencies and dependency graph visualization
- Supplier logo support with display in list, detail, and graph views
- SPOF and redundancy tracking for supplier dependencies
- Supplier type management with configurable requirements and review system
- Supplier reviews added to calendar
- Site management moved to assets with site dependency models

### Fixed

- Fix version display when APP_VERSION env var is unset
- Fix supplier list layout
- Fix migration for CharField to FK data migration

## [0.1.1] - 2026-03-01

### Added

- Unique auto-generated references for all items in PREFIX-N format
- References displayed in all list tables and detail views with monospace font
- Clickable references in tables

### Fixed

- Fix data migrations to handle NULL references in historical tables

## [0.1.0] - 2026-03-01

### Added

- Tag support for all items with ergonomic Tom Select input and inline creation
- Tag administration page with usage tracking, editing, and deletion

## [0.0.5] - 2026-03-01

### Added

- App version display from Git tag in sidebar
- Vertical divider line for sidebar submenus

### Changed

- Increase text size and lighten sidebar sub-links

### Fixed

- Set is_approved default to False so items require explicit approval

## [0.0.2 - 0.0.4] - 2026-02-28

### Changed

- Auto-run migrate and create super-admin on container startup

### Fixed

- Prevent Gunicorn worker crashes in Docker behind a reverse proxy
- Add --preload to Gunicorn to prevent worker timeout on startup
- Wait for PostgreSQL to be fully ready before running migrations

## [0.0.1] - 2026-02-28

### Added

- Initial release with Django 5.2 GRC platform
- Organizational context management (scopes, sites, issues, stakeholders, objectives, SWOT, roles, activities)
- Asset management with DIC valuation and support assets
- Risk management with ISO 27005 analysis and treatment plans
- Compliance tracking with frameworks, requirements, and assessments
- Custom user model with email-based authentication and UUID primary keys
- Role-based access control with 6 system groups and custom permissions
- Full i18n support (English and French)
- Calendar view for all dated elements
- Contextual help banners
- REST API under /api/v1/
- Docker Compose deployment with PostgreSQL
- GitHub Actions CI with pytest
- Docker Hub publish workflow on version tags

[Unreleased]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.22.0...HEAD
[0.22.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.21.4...v0.22.0
[0.21.4]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.21.3...v0.21.4
[0.21.3]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.21.2...v0.21.3
[0.21.2]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.21.1...v0.21.2
[0.21.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.21.0...v0.21.1
[0.21.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.20.0...v0.21.0
[0.20.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.19.1...v0.20.0
[0.19.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.19.0...v0.19.1
[0.19.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.18.3...v0.19.0
[0.18.3]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.18.2...v0.18.3
[0.18.2]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.18.1...v0.18.2
[0.18.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.18.0...v0.18.1
[0.18.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.17.0...v0.18.0
[0.17.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.16.0...v0.17.0
[0.16.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.15.0...v0.16.0
[0.15.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.14.2...v0.15.0
[0.14.0 - 0.14.2]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.13.0...v0.14.2
[0.13.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.12.1...v0.13.0
[0.12.0 - 0.12.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.11.2...v0.12.1
[0.11.0 - 0.11.2]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.10.2...v0.11.2
[0.10.0 - 0.10.2]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.9.1...v0.10.2
[0.9.0 - 0.9.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.8.0...v0.9.1
[0.8.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.7.5...v0.8.0
[0.7.0 - 0.7.5]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.6.0...v0.7.5
[0.6.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.5.0...v0.6.0
[0.5.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.4.8...v0.5.0
[0.4.5 - 0.4.8]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.4.4...v0.4.8
[0.4.2 - 0.4.4]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.4.1...v0.4.4
[0.4.0 - 0.4.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.3.1...v0.4.1
[0.3.0 - 0.3.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.2.16...v0.3.1
[0.2.12 - 0.2.16]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.2.11...v0.2.16
[0.2.7 - 0.2.11]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.2.6...v0.2.11
[0.2.1 - 0.2.6]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.2.0...v0.2.6
[0.2.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.1.1...v0.2.0
[0.1.1]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.1.0...v0.1.1
[0.1.0]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.0.5...v0.1.0
[0.0.5]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.0.4...v0.0.5
[0.0.2 - 0.0.4]: https://gitlab.rslt.fr/fairway/fairway/-/compare/v0.0.1...v0.0.4
[0.0.1]: https://gitlab.rslt.fr/fairway/fairway/-/tags/v0.0.1
