# Changelog

All notable changes to Cairn (formerly Fairway) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Dashboard risk treatment flow (Sankey)**: a new Sankey (cash-flow style) chart on the home dashboard, displayed above the risk matrices, visualises how treatment moves each risk from its current severity level (before treatment) to its residual level (after treatment). Each column lists the severity levels present (highest at the top, lowest at the bottom), coloured with the configured risk-level palette, and each flow's thickness is the number of risks making that transition - so a heavy downward flow reads as effective treatment and a flat flow as untreated risk. Levels are derived from the likelihood/impact pairs (with the same default 5x5 ISO 27005 fallback as the matrices), so the chart stays consistent with the matrices below even when no risk criteria are configured. The chart honours light/dark mode and is rendered with Apache ECharts. Built from a new `build_risk_treatment_flow()` helper in `risks/views.py`.
- **Ask Cairn: OpenAI and OpenAI-compatible providers**: the assistant gains an `openai` backend (`AI_ASSISTANT_PROVIDER=openai`) that targets OpenAI (ChatGPT, e.g. `gpt-4o-mini`) out of the box and, via `AI_ASSISTANT_BASE_URL`, any other endpoint implementing the OpenAI `/chat/completions` and `/embeddings` API (vLLM, LiteLLM, LocalAI, Together, Groq...). The shared request/response handling was extracted into a generic `OpenAICompatibleClient`; the existing `MistralClient` is now a thin subclass of it (Mistral already exposes an OpenAI-compatible API), so behaviour is unchanged for Mistral users. `AI_ASSISTANT_BASE_URL` now defaults to empty and each provider falls back to its own endpoint (`mistral` -> `api.mistral.ai`, `openai` -> `api.openai.com`, `anthropic` -> `api.anthropic.com`); set it only to target a custom gateway.
- **Ask Cairn: Claude (Anthropic) provider**: a native `anthropic` backend (`AI_ASSISTANT_PROVIDER=anthropic`) talks to Claude through the Messages API (`POST /v1/messages`, `x-api-key` header, top-level `system`, `content` block list) - Claude is not OpenAI-compatible, so it has its own client. Routing uses forced tool use (a `plan` tool whose `input_schema` is the routing schema) and no `temperature`/`thinking` is sent (both 400 on the current Opus family). Set `AI_ASSISTANT_MODEL` to a Claude model id (e.g. `claude-opus-4-8`). Semantic search is not available with this provider, since Anthropic has no embeddings API.
- **Ask Cairn: automatic semantic index maintenance**: the requirement semantic index now stays fresh without a manual command. A `post_delete` signal prunes a deleted requirement's embedding immediately (no provider call); the index is refreshed in a guarded background thread when a server process starts (when `AI_ASSISTANT_SEMANTIC_ENABLED`); and a dedicated **Administration -> Semantic index** page shows an index-status panel (indexed / total requirements, last updated, embedding model) with an **"Update the index now"** button (gated by `system.config.update`) that triggers a background rebuild. Embedding stays off the request path - requirement saves never embed inline; the documented daily `rebuild_semantic_index` cron remains the self-healing backstop. The rebuild logic was extracted into `assistant.semantic.rebuild_index` / `rebuild_index_async` (cache-locked to dedupe overlapping triggers) and reused by the management command.

## [0.27.1] - 2026-06-14

### Fixed

- **Command palette no longer opens in a French locale**: the Ask Cairn palette script embedded `{% trans %}` strings inside single-quoted JS literals, and French translations contain apostrophes (e.g. "L'assistant est injoignable…") that terminated the string, throwing a `SyntaxError` that killed the whole palette script. Translated strings embedded in the palette JS are now escaped with `|escapejs`. (Surfaced only in production, which runs in French; English dev was unaffected.)
- **Clearer error when the Mistral API key is missing**: `rebuild_semantic_index` and chat failed with a cryptic `httpx.LocalProtocolError: Illegal header value b'Bearer '` when `AI_ASSISTANT_API_KEY` was empty. `MistralClient` now validates the key up front and raises a clear "Mistral API key is not configured" message; `rebuild_semantic_index` exits with a clean error instead of a traceback.

## [0.27.0] - 2026-06-13

### Added

- **Ask Cairn, an optional AI question mode in the command palette**: the command palette (Ctrl+K) gains an "Ask Cairn" entry that answers simple natural-language questions like "Quelles décisions ont été prises lors de la dernière revue de direction ?". The LLM backend is a pluggable provider (`AI_ASSISTANT_PROVIDER`): [Mistral AI](https://mistral.ai/) (third-party, EU-hosted; default model `mistral-small-latest`) by default, with a self-hosted [Ollama](https://ollama.com/) provider still selectable for an on-premises, no-egress deployment. The model only routes the question to a curated allowlist of 24 read-only MCP tools executed in-process with the requesting user (existing permissions and scope filters apply, nothing is bypassed); the answer shows the real matching records as clickable cards plus a short AI-labeled summary sentence in the user's language. Internal identifiers are stripped before the summary call. The feature is disabled by default (`AI_ASSISTANT_ENABLED`), degrades gracefully when the backend is unreachable, and ships with a REST endpoint (`POST /api/v1/assistant/ask/`) and an `ask_assistant` MCP tool. Each answer carries a **thumbs up/down feedback control with an optional comment**: the captured feedback (prompt, interface language, LLM summary and returned records, provider/model, rating and comment) is stored as `AssistantFeedback`, browsable and exportable as JSON from the in-app Administration area (sidebar "Assistant feedback") and the Django admin (and via `GET /api/v1/assistant/feedback/export/` or the `list_assistant_feedback` MCP tool, gated by `system.assistant_feedback.read`) so a set of feedback can be handed to an LLM to improve the service. Feedback can be marked **corrected** once acted on (in-app button, admin action, or `POST /api/v1/assistant/feedback/{id}/resolve/`), which excludes it from future exports by default (the in-app list defaults to open feedback and the export, REST `export` and `list_assistant_feedback` MCP tool all drop corrected rows unless `include_resolved`). Optionally (`AI_ASSISTANT_SEMANTIC_ENABLED`), a **semantic, cross-language requirement search** (`semantic_search_requirements`) lets topic questions match control content regardless of language (e.g. French question, English ISO controls): requirement embeddings are stored portably (no `pgvector`) via `manage.py rebuild_semantic_index` and ranked by in-Python cosine similarity. "Who is responsible for scope X?" questions are now answered: the `list_scopes` MCP tool exposes a read-only `manager_names` field (from a new `Scope.manager_names` property) and the assistant feeds it to the summary, so the responsible managers are named instead of reported as missing.

## [0.26.3] - 2026-06-12

### Added

- **Company identity on the dashboard**: when a company name is configured (Company settings page), it replaces the "Dashboard" title in the page header, with the company logo displayed beside it; the page identity moves to the eyebrow. The `{% page_header %}` component gains a generic `logo` parameter (image rendered in place of the icon). Without a configured name, the header is unchanged.
- **Demo dataset seed script**: `scripts/seed_demo_data.py` (with `scripts/seed_demo_tables.py`) populates a fresh database with the fictional "Voltara Energy" company: users in every system group, scopes, sites, stakeholders, issues, objectives, SWOT, roles, activities, essential and support assets with dependencies and SPOFs, suppliers with contractual requirements, the full ISO/IEC 27001:2022 Annex A plus NIS2, GDPR and an internal baseline (133 requirements), audits with findings and action plans, an ISO 27005 risk assessment (threats, vulnerabilities, analyses, risks, treatment plans, acceptances), an EBIOS RM study (workshops 0-3), indicators with measurement history, and management reviews. Documented in `docs/installation.md`.

### Fixed

- **Report downloads rendered as binary in the page**: the global `hx-boost` intercepted clicks on file-download links (report list, management review PPTX/DOCX exports, risk register and assessment exports, framework import samples) and swapped the binary attachment into the page instead of letting the browser download it. Download links now opt out of boosting (`hx-boost="false"` + `download`), and a safety net in the boosted-navigation module cancels the swap and hands the URL to the browser whenever a response carries `Content-Disposition: attachment`.
- **Calendar "Upcoming events" showed negative day counts** (#112): ranged items already in progress (action plans, treatment plans, compliance assessments) displayed their range start with badges like "in -131 days" and always floated to the top of the list. The card now consumes a dedicated `/api/calendar-upcoming/` endpoint that reuses the dashboard's next-milestone logic (shared `build_upcoming_deadlines()` helper): ranged items show their start date until they begin, then their end/target date; past-due deadlines carry a red "Overdue" badge; concluded items are excluded; sorting uses the milestone date; and each row names the nature of the date in a small chip, like the dashboard.
- **Search palette ignored the user language**: the navigation and quick-action entries of the command palette (Ctrl+K) were translated once at server start instead of per request, so they always showed up in the import-time language (typically English) regardless of the user's language. The labels are now lazily translated.

### Changed

- **Search palette contrast**: the command palette dialog was 85% translucent and blended into the blurred page behind it, reading as grey-on-grey. It now uses a near-opaque frosted surface (new `--surface-glass-strong` token, light and dark), a slightly darker backdrop scrim, and stronger group labels.
- **README rewritten for accessibility**: the public README is now a short overview (what Cairn does, quick start, documentation links, tech stack). The detailed content moves to `docs/`: feature tables to `docs/features.md`, the full MCP tool reference to `docs/mcp-server.md`, installation and scheduled-command details to `docs/installation.md`, plus a new REST API overview (`docs/api.md`) and a documentation index (`docs/README.md`).
- **Documentation screenshots refreshed**: all `docs/screenshots/` captures retaken in 4:3 (1440x1080) on the current brand with the demo dataset, and embedded in the README (dashboard) and `docs/features.md` (one per module section).

## [0.26.2] - 2026-06-12

### Fixed

- **Predefined compliance indicators disagreed with the dashboard**: the "Global compliance rate" predefined indicator averaged the stored `compliance_level` field over every reportable framework (drafts and superseded included), while the dashboard computes, per active framework, the proportion of applicable requirements whose latest assessment result is compliant. The computation is extracted into a shared service (`compliance.services`) now used by the dashboard page, the dashboard WebSocket refresh (which averaged the stored field too, so a live update could overwrite the page value with a different number) and both predefined indicators (`global_compliance_rate` and `framework_compliance_rate`).
- **Roles could not be assigned from the UI**: the role create / edit modal had no "Assigned users" field, even though the model, the API and the MCP tools expose it (and the dashboard nags about mandatory roles without a user). The second step of the modal becomes "Assignment & status" and gains a multi-select of active users.

### Changed

- **SPOF and calendar deadlines fold into Today's actions**: the dashboard's standalone SPOF warning banner and "Upcoming events" card are gone. Single points of failure now appear as actionable items in the "To plan" group (one entry per dependency type, each linking to its list). Deadlines and events render as a section inside the Today's actions card, server-side (the client-side fetch is removed): upcoming dates for the next 30 days plus overdue deadlines (reviews, target dates, expiries) from the last 90 days. Ranged items (action / treatment plans, audits) now show their next milestone - the start date until they begin, then the target date - instead of always showing the range start, which produced nonsensical "in -131 days" badges; anything past due is flagged with a red "Overdue" badge instead of a negative day count. Overdue deadlines count toward the card's attention counter, and the list collapses beyond five items. Concluded items (closed or cancelled action plans, completed treatment plans, achieved objectives, revoked or renewed acceptances) stay on the calendar but leave the dashboard list: a closed plan is not "overdue". Each row names the nature of the date in a small chip (Review, Expiry, Effective date, Target date, Start date, Valid until, Audit start / end, Assessment or Analysis date) so an entry reads as "what is due", and the title drops the redundant "Review: " / "Expiry: " prefixes there.
- **Reports and Management reviews move under a Strategy group**: the sidebar's Governance section gains a collapsible "Strategy" group (compass icon) after Indicators, holding the Reports and Management reviews entries, which leave the top-level General block (Dashboard and Calendar remain there).
- **Forms adopt the same design language**: form fields take the recipe of the sidebar search field - glass card resting on the surface with a soft shadow lift, brightening on hover, surfacing to solid with the accent ring on focus (globally, in the modal form drawer, on Tom Select controls, input-group addons, the image-upload button and the scope tree containers). Fields use dedicated `--field-*` tokens: in light mode the fill is more opaque and the hairline border visible (pure glass is invisible on light surfaces), in dark mode they match the sidebar glass. The modal form drawer itself moves to the flat page-level background, like the sidebar panel, so the fields float over it the same way; its header, body and footer become transparent. The Jodit rich-text editor loses its default grey segmented chrome in both themes: the whole editor becomes one soft well that surfaces on focus, with a transparent toolbar, calm icon hovers, fading hairlines between toolbar / canvas / status bar, and themed popups. Tom Select controls follow the same well treatment and their dropdown becomes frosted glass like the other floating menus, as do the icon-picker popover and the scope-count popover. The modal wizard stepper softens: number chips rest on the muted well tones and connectors dissolve toward the next step. The drawer header / footer and the duplicated modal header / footer rules (which were overriding the theme-aware ones) get the fading hairlines, and the scope tree widget becomes a soft well whose embedded search is borderless over a fading hairline - with the selected row tinted like an active sidebar link. Input-group addons and the image-upload button align on the well tones.
- **The sidebar design language spreads to the rest of the interface**: the visual vocabulary introduced by the sidebar redesign (frosted glass, fading hairlines, sentence-case labels) now applies across the UI. Floating elements pick up the translucent backdrop-blurred glass treatment: the mobile menu button, the sidebar collapse toggle, the bulk-actions bar (which loses its heavy accent border - the accent-coloured count is enough), dropdown menus, the global search dialog (which now keeps the material of the sidebar search field it morphs from), the toasts (semantic tints kept but translucent) and the modal backdrop. Hard border lines under headers are replaced by hairlines fading at their ends, echoing the sidebar's right-edge demarcation: card headers, modal header / footer, the search overlay input row, drawer section titles, the calendar timeline month labels and the styleguide section titles. All small UPPERCASE labels move to sentence case like the sidebar section labels did: table column headers, page-header eyebrows, stat / KPI card labels, detail-page card section titles (the `text-uppercase` utility is removed from ~140 headings), SWOT and risk matrix axis labels, calendar weekday headers, drawer and metadata labels, the OAuth consent screen and the collapsed-sidebar flyout titles. Reference codes (`.ref`) deliberately stay uppercase mono - they are audit-grade identifiers, not labels. The `--sidebar-glass` tokens are generalized as `--glass` / `--glass-hover`, and the notification list inside the sidebar adopts the invisible scrollbar.
- **CI actions upgraded to Node 24 runtimes**: GitHub deprecates Node 20 action runtimes (forced to Node 24 on June 16, 2026; removed from runners on September 16, 2026). The workflows move to the latest majors, all running on Node 24: `actions/checkout` v4 -> v6, `actions/setup-python` v5 -> v6, `docker/setup-buildx-action` v3 -> v4, `docker/login-action` v3 -> v4, `docker/metadata-action` v5 -> v6, `docker/build-push-action` v6 -> v7.

## [0.26.1] - 2026-06-11

### Changed

- **Dashboard alerts become "Today's actions"**: the red global-alerts banner at the top of the dashboard is replaced by a calm "Today's actions" card. The same signals (critical risks, non-compliant requirements, overdue action plans, unassigned mandatory roles, ownerless critical activities, end-of-life assets, expired supplier contracts, expiring risk acceptances) are now phrased as actionable to-do items ("Treat 3 critical risk(s)" instead of "3 critical risk(s)"), grouped by priority (Priority / To plan / To watch, each on a soft-tinted panel with a semantic dot), and each item links to the page where the user can act. The card carries a navy top accent, an icon chip and a count badge in the header, and items render as raised rows with a calm hover lift. Renders in three columns on desktop and stacks on mobile, in both themes.
- **Bolder overall-compliance score**: the large percentage on the dashboard's "Overall compliance" card moves from weight 600 to 700 (the heaviest Inter weight allowed by the brand guidelines) so the headline figure stands out.
- **Sidebar redesign**: the main menu becomes a flat, flush panel: page-background colour, no border or rounded corners, glued to the window edges, with a subtle hairline on its right edge and an invisible scrollbar. Two floating glass elements (translucent, backdrop-blurred) frame the scrollable menu: a search field at the top showing the platform-aware shortcut (Cmd K on macOS, Ctrl K elsewhere) and opening the global search overlay, and a user footer at the bottom (avatar, name, email) whose ellipsis expands an inline Profile / Sign out menu that closes after use. Menu entries slide beneath the glass while scrolling. Section labels move to sentence case, and the user avatar and its dropdown leave the floating top-right bubble (search, about and notifications stay there). In collapsed mode the search shrinks to an icon and the footer to the avatar.
- **Search overlay entrance animation**: opening the search from the sidebar field morphs the dialog from the trigger's position and shape to its centered resting place (FLIP transform, 320 ms ease-out-expo). Ctrl+K keeps the plain fade and `prefers-reduced-motion` disables the flight.
- **Everything moves into the sidebar; the top-right bubble is gone**: notifications live in the user footer - the bell (with its unread badge) replaces the ellipsis next to the avatar and expands an inline panel above the user row, animated like the user menu (both are Bootstrap collapses, mutually exclusive, closed by outside clicks and Escape); when the sidebar is collapsed a notification dot shows on the avatar instead. The About entry joins the user menu (Profile / About / Sign out) and the About modal gains a link to the GitHub repository. With search, notifications and About now in the sidebar, the floating top-right button bubble is removed, along with the dashboard's real-time connection dot (the live updates themselves are untouched). The brand area loses its border for a gradient veil under which scrolling entries fade out progressively, and the menu's right hairline fades out toward the top and bottom of the window.

## [0.26.0] - 2026-06-11

### Fixed

- **Overall-compliance caption counted every requirement**: the dashboard's "Overall compliance" card claimed "N requirements tracked" using the full requirement inventory, while the displayed average only covers validated active frameworks, so a draft framework's requirements inflated the caption. The caption now counts the applicable requirements of the frameworks that actually feed the average (new `tracked_requirement_count`), the inventory stat card keeps the full count, and the live WebSocket refresh applies the same reportable filter to the average as the page render. The caption's French translation also gains a real singular / plural form (it previously rendered "3 exigence suivie" because of an illegal filter inside `blocktrans`).
- **Modal step gating broken by rich-text fields**: the step-completion check of the modal form engine read the first input inside each required field wrapper, which on rich-text fields is an unnamed internal input injected by the Jodit editor (always empty), so forms like the scope create / edit modal refused to advance past a step whose required fields were all filled. The check now reads the first *named* control of the wrapper (the real, synced form field). Also hardened two sidebar event handlers against non-element event targets (console `TypeError` on text-node hover).

### Changed

- **List tables show a single lifecycle column**: every domain list table now renders one Status column carrying the element's lifecycle state (`workflow_badge`), and the legacy Status / Approval column pair is gone. The 27 list views are aligned: the bespoke status badges (context binary toggles, asset ITAM states, compliance and risk workflows, management reviews) are replaced by the unified badge, the per-table "Approval" column (Approved / Pending) is removed everywhere, and the lifecycle column is sortable on `workflow_state` (this also repairs the scope / SWOT / risk-criteria headers, whose sort key did not match the view since the publication-status retirement; the risk-criteria list also still rendered the removed `status` field as a permanently empty badge). The asset, supplier and site dependency lists and the requirement list, which only showed the approval flag, gain the sortable lifecycle column in its place. The now-unused `approval_enabled_for` template tag and its `versioning_tags` library are deleted. Operational state filters above the tables (e.g. active / inactive stakeholders) are untouched: they filter the non-governing attribute, which remains visible on detail pages.

### Removed

- **Legacy approval bar retired**: the per-page "Pending approval / Approve" banner is removed from all 25 detail pages, along with the `approval_banner` styleguide component, its template tag and its CSS - the lifecycle stepper carries the state and the validation action (the Validate step is the approval act). The approve endpoints remain for API / MCP compatibility as deprecated aliases.
- **Publication `status` fields folded into the lifecycle**: the Scope, Site, SWOT analysis and Risk criteria models lose their `status` field (and the matching enums) - their draft / active / archived vocabulary is now fully carried by the unified lifecycle (`active` and `validated` fold into the `validated` state, `archived` stays `archived`, data migrations included with history). Everything that exposed those statuses moves to the lifecycle: forms (the status selects disappear, transitions go through the stepper), scope and site pickers, list filters and sortable columns, Django admin, the REST serializers / filters / ordering (the `status` field is replaced by `workflow_state`), the MCP tools (filter and fields renamed; the state changes through `transition_*`), and the templates now render the `workflow_badge`. The scope `archive` API action becomes a lifecycle transition (archiving a draft is now correctly rejected) and the SWOT `validate` action drives the approval axis. Framework and Requirement deliberately keep their `status` (`under_review` / `deprecated` / `superseded` are versioning semantics the 4-state lifecycle does not cover - spec option (b)).

### Added

- **Lifecycle workflow documentation**: the canonical framework spec lands in `docs/modules/governance/workflow.md` (architecture, the default and the fifteen specific workflows with their governance flags, the as-built rules, the REST / MCP / UI surfaces and the recorded decisions); the entity files of the four retired publication statuses point at it, the README feature table describes the unified lifecycle, and the CLAUDE.md development guidelines now reference the generic stepper (`WorkflowStepperMixin` + `includes/workflow_stepper.html`) and the workflow registry instead of the removed bespoke implementations.
- **Workflow framework (foundation)**: a new `core/workflow.py` introduces the lifecycle engine that will unify the approval and per-model status systems (see issue #105). A `Workflow` is an ordered set of `State` objects, each carrying governance flags (`counts_in_reports`, `linkable`, `deletable`, `is_initial`, `is_terminal`), plus the allowed `Transition` objects (required permission action, optional mandatory comment, declarative side effects). The module ships the default 4-state lifecycle (`draft` -> `pending` -> `validated` -> `archived`), a workflow registry, permission-aware transition validation (`validate_transition` / `allowed_transitions` / `apply_transition`) and queryset helpers (`reportable_states` / `linkable_states` / `deletable_states`). Pure-Python and fully unit tested (27 tests); no model, database or UI wiring yet (those land in the following phases).
- **Action plan specific workflow**: the compliance action plan is the first entity to run its own registered lifecycle workflow (`action_plan`), generated from the existing transition constants so the 8-state machine keeps a single source of truth. Each state carries its governance flags: `new` / `to_define` are deletable drafting states, `to_validate` onwards count in reports, `to_implement` / `implementation_to_validate` / `validated` are linkable, `closed` / `cancelled` are terminal; refusals keep their mandatory comment and per-step permissions (`update`, `validate`, `implement`, `close`, `cancel`) are enforced per transition. The model's `transition_to()` is now routed through the framework while preserving its legacy contract (ValueError on an illegal transition or missing refusal comment, completion fields auto-filled on close, `ActionPlanTransition` audit rows); the legacy `status` field and `workflow_state` are kept in sync both ways during the migration period, and a data migration aligns existing rows (including history). Linking and deletion governance now use the real action plan states (e.g. only `to_implement` / `implementation_to_validate` / `validated` plans can be linked to a treatment plan). Workflows can now also be declared per model in code (`WORKFLOW_NAME`), with the DB assignment still taking precedence.
- **Compliance assessment specific workflow**: the compliance assessment now runs its own registered lifecycle workflow (`compliance_assessment`), generated from the existing `ASSESSMENT_STATUS_TRANSITIONS` constants. Per-state governance: only `draft` assessments can be deleted; `planned` / `in_progress` / `completed` / `closed` count in reports and on the calendar while `draft` and `cancelled` do not; `closed` / `cancelled` are terminal. The model's `transition_to()` is routed through the framework while keeping its legacy contract (single status argument, ValueError on an illegal transition, EVALUATED-results reset when completing) and `status` / `workflow_state` stay in sync both ways, with a data migration aligning existing rows including history.
- **Management review specific workflow**: the management review (ISO 27001 clause 9.3) now runs its own registered lifecycle workflow (`management_review`), generated from the existing transition constants. Per-state governance: only a `planned` review can be deleted; `cancelled` reviews leave reports; `closed` / `cancelled` are terminal. The closure transition (`held` -> `closed`) is declared with the `approve` permission action, matching the rule the API already enforced, and cancellation keeps its mandatory comment, now enforced declaratively. The model's `transition_to()` is routed through the framework while keeping its legacy contract (ValueError, closure preconditions via `can_close()`, `held_date` auto-set, `ManagementReviewTransition` audit rows, snapshot flow untouched); `status` / `workflow_state` stay in sync both ways, with a data migration aligning existing rows including history.
- **Asset specific workflows**: essential and support assets now run their own registered lifecycle workflows (`essential_asset`, `support_asset`). Their statuses had no transition constants (freely editable), so the workflows encode the natural ITAM progressions (essential: identified -> active <-> under review -> decommissioned; support: in stock -> deployed -> active <-> under maintenance -> decommissioned -> disposed, with decommissioning reachable from any active state). Governance: every state stays reportable (decommissioned and disposed assets belong to audit history), decommissioned / disposed assets are no longer linkable (declarative version of RS-04) and cannot be deleted; only each model's creation-default states remain deletable (identified for essential assets, in stock / active for support assets). Legacy free status edits keep working through the status / workflow_state sync, now factored into a shared `sync_legacy_status()` helper used by all five reconciled entities, and a data migration aligns existing rows including history.
- **Risk process specific workflows**: the risk, treatment plan, risk acceptance and vulnerability now run their own registered lifecycle workflows, encoding the natural ISO 27005 progressions (these statuses were freely editable). Highlights: a freshly *identified* risk is a working entry excluded from the risk register and not yet linkable (the spec's draft analog), the monitoring loop can re-enter analysis, and a *closed* risk stays in the register as history but is terminal; the treatment plan's automated overdue flip keeps working and is mirrored into the lifecycle, with *cancelled* plans leaving reports; every acceptance state stays reportable (a revoked acceptance is audit-relevant) with *revoked* terminal; vulnerabilities follow identified -> confirmed -> mitigated / accepted -> closed with direct false-positive closure. Deletion is restricted to each model's creation-default state; a data migration aligns existing rows including history.
- **EBIOS RM specific workflows**: the six EBIOS deliverables now run their own registered lifecycle workflows. The workshop review machine (not started -> in progress -> under review -> validated / rejected -> rework) carries the dedicated `validate` permission on review verdicts and requires a comment when rejecting; the study framework, security baseline, summary, baseline gaps (an accepted deviation can later enter remediation) and PACS measures (with overdue recovery, cancelled measures leaving reports) follow their natural progressions. The study framework and summary keep `is_approved` as an independent axis through a new explicit opt-out: their draft / validated state names would otherwise trip the subsumes-approval heuristic and fight the status sync. Deletion restricted to each deliverable's initial state; a data migration aligns existing rows including history.
- **Lifecycle stepper rolled out to every detail page**: the three bespoke stepper implementations (compliance assessment, action plan, management review) are replaced by the generic component driven by their registered workflows - their hand-built context blocks, inline stepper markup and per-page transition modals are deleted, while their bespoke transition endpoints (required-fields gating, completion side effects, closure preconditions) keep receiving the posts. All other domain detail pages (context, assets, risks, compliance frameworks and requirements) now render the lifecycle stepper too, and the mandatory-comment gating of the shared modal now follows each transition's declaration (a management review cancellation requires its comment client-side as well).
- **Generic lifecycle stepper and badges (UI foundation)**: any detail view can now render the workflow stepper straight from the registered workflow definition. A `WorkflowStepperMixin` builds the stepper context (main-flow steps in declaration order, the caller's permitted next step, backward refusal / rework move, and the branch state - cancelled or archived - drawn as the off-ramp), reusing the existing stepper component unchanged; a shared endpoint (`/workflow/<app>/<model>/<pk>/transition/`) performs UI transitions with per-transition permissions, mandatory-comment enforcement and a validated-referer redirect; a `workflow_badge` template tag renders any element's state from its tone. A generic comment modal handles refusals and cancellations. Piloted on the scope detail page (Draft -> Pending validation -> Validated, with the Archived branch).
- **Risk assessment specific workflow, completing the operational rollout**: the risk assessment campaign runs its own workflow (`draft -> in_progress -> completed -> validated -> archived`, with a rework loop from completed); validation and archiving are approval acts (`approve` permission), only draft campaigns can be deleted, and draft / archived campaigns leave reports and the calendar. The approval flag and `validated_by` stamp stay independent of the states (explicit opt-out). With this, every entity with operational stages runs a registered workflow. Two scoping decisions are recorded: binary toggles (stakeholder, role, activity, asset group, threat, indicator) and outcome trackers (objective, issue, stakeholder feedback) keep their `status` as a non-governing operational attribute over the default 4-state lifecycle, as the spec's option (b); and the retirement of the overlapping publication `status` fields (scope, site, SWOT, risk criteria, framework, requirement) is deferred to the UI phase, when the stepper replaces the status selects.
- **Lifecycle transition API and MCP tools**: every lifecycle entity gains generic transition surfaces. REST: `GET /api/v1/<entity>/<id>/transition/` lists the transitions the caller may perform (filtered by permission) and `POST` performs one (`target_state`, optional `comment`), with proper 400 / 403 errors; list endpoints accept a `?workflow_state=` filter (comma-separated). MCP: `transition_<entity>(id, target_state, comment)` and `<entity>_allowed_transitions(id)` are registered for all CRUD entities, leaving the bespoke status-machine tools (action plan, management review) untouched. The `approve_*` tools and the `/approve/` REST action are now deprecated aliases: they keep working via the state sync but refuse elements in a terminal lifecycle state.
- **Notification delivery surfaces**: a bell with a live unread badge joins the user header bubble (light + dark themes), opening a dropdown with the latest notifications, per-item mark-as-read on click and a "Mark all as read" action; the badge updates in real time over a new per-user WebSocket (`/ws/notifications/`). New own-data REST endpoints under `/api/v1/notifications/` (list, unread count, mark read, mark all read) and MCP tools (`list_notifications`, `mark_notification_read`, `mark_all_notifications_read`).
- **Notification subsystem (foundation)**: a new `accounts.Notification` model stores per-user in-app notifications (generic target, resolved URL, read / unread), created by the lifecycle `notify_owner` effect when an element is submitted for validation (RG-LC-06). Recipients follow the fallback chain (RG-LC-09): the element's own managers if it is a scope-like container, otherwise the managers of its scopes, otherwise the holders of the entity's `.approve` permission, otherwise the creator; the actor and inactive users are never notified. Each notification is rendered in the recipient's language; the email copy is sent after the transaction commits (`transaction.on_commit`) and honours the new per-user `email_notifications` opt-out. Email settings are now environment-configurable (`EMAIL_BACKEND` defaults to the console backend in DEBUG, plus `EMAIL_HOST` / `DEFAULT_FROM_EMAIL` / `SITE_URL`).
- **Workflow framework (report enforcement)**: generated reports now apply the lifecycle rule (RG-LC-01). The Statement of Applicability excludes non-validated frameworks, requirements, linked risks and action plans; the risk register excludes non-validated risks (enforced inside the generators, so the UI, API and MCP callers are all covered). Assessment-scoped documents (audit report, ISO 27005 report, management review exports) keep reporting the full content of the explicitly chosen assessment or review.
- **Workflow framework (linking enforcement)**: link pickers and MCP link tools now respect the lifecycle. The form pickers (requirement's linked risks / assets / stakeholder expectations, risk's linked requirements / affected assets, treatment plan's related action plans) only offer elements in a linkable state, while keeping already-linked elements selectable so an edit never silently drops an existing link (RG-LC-03 / RG-LC-04). The MCP `link_*` / `set_*` tools reject targets that are not linkable (unless already linked) and refuse to add links to an element in a terminal state; `unlink_*` is unchanged (removing a link is always allowed). Models without a lifecycle (plain child entities) are not governed.
- **Workflow framework (data layer)**: every domain model now carries a `workflow_state` lifecycle field on `BaseModel`, exposed through a small model API (`get_workflow()`, the `counts_in_reports` / `is_linkable` / `is_deletable` properties, `available_transitions()` and `transition_to()`). A per-model assignment field (`VersioningConfig.workflow_name`) lets an item type run a specific workflow instead of the default. A data migration backfills `workflow_state` from `is_approved` (approved becomes `validated`, otherwise `draft`), and the model keeps the legacy `is_approved` flag and the new state coherent during the transition, so the existing approval flows keep working unchanged. No enforcement yet (reports, linking and deletion still ignore the state until the next phase).

## [0.25.0] - 2026-06-11

### Changed

- **Modal form engine documented**: the brand guidelines gain an "Engine (implementation)" subsection (the `SteppedFormMixin` / `Step` API, the shell / partials / JS layout, the custom widgets and the enforced rules); the `/styleguide` page gains a "modal form engine" section showcasing the stepper, completion meter and field-row anatomy; the README tech-stack table notes the shared modal form engine.
- **Modal form engine finishing touches**: a stepped form now exposes a `modal_size` (single-step `md`, multi-step `lg`) that sizes the centered dialog; steps are capped at `max_rows_per_step` (default 7) layout rows and raise `ImproperlyConfigured` if exceeded, so a step always fits one viewport without scrolling; and the field-error count is announced in the `#hx-live` polite ARIA region after an HTMX submit.

- **Risks forms migrated to the modal engine (batch 2)**: the Risk (Identity / Evaluation / Relations & status), ISO 27005 risk (Identity / Evaluation / Relations & tags) and Treatment plan (Identity / Residual & planning / Relations & tags) create / edit forms join the engine, split into `Create` / `Update` subclasses over a shared stepped base. Their dynamic `__init__` logic is preserved: Risk and Treatment plan still rebuild the likelihood/impact fields as scale-driven `TypedChoiceField`s and Risk still locks the assessment/source in edit; ISO 27005 still restricts the assessment queryset. Helpers on every field; modal titles set. With this, 27 of the 28 create/edit forms run on the shared declarative modal engine; the compliance Assessment result ("Evaluate requirement") form stays a bespoke hand-written modal on purpose, as it carries conditional field visibility, a requirement context banner, compliance-level auto-fill and multipart document attachments that the declarative engine does not model. It still renders in the shared centered modal via the legacy field block.
- **Risks forms migrated to the modal engine (batch 1)**: the Risk assessment, Threat, Vulnerability, Risk acceptance and Treatment action create / edit forms are split into `Create` / `Update` subclasses over a shared stepped base (two or three steps, column rows, a helper on every field); all ten views now set modal titles (they had none). Templates reduced to the header icon; FR translations added. The Risk, ISO 27005 risk and Treatment plan forms (which carry dynamic `__init__` logic) land in batch 2.

- **Compliance forms migrated to the modal engine (app complete)**: Framework (four steps, logo via the reusable `ImageUploadWidget`), Compliance assessment (Identity / Planning & status, keeping its status-transition and locking logic), Finding (Finding / Recommendation, keeping its assessment-scoped requirements) and Action plan (Identity / Gap & remediation / Planning / Relations & scope) create / edit forms are split into `Create` / `Update` subclasses over a shared stepped base, with column rows and a helper on every field; modal titles set. The full-page framework template is simplified to render the logo widget. With Mapping, compliance is now 5/5 forms on the modal engine.

- **Reusable `ImageUploadWidget` + Supplier form migrated (assets complete)**: the supplier logo upload is generalised into `context.widgets.ImageUploadWidget` (square preview + camera button + clear), driven by generic data-attribute JS in `base.html` that resizes the chosen file to a 128px PNG data-URI client-side (no multipart), so it works in the modal. The `logo` / `logo_resized` field pair is consolidated into a single `logo` data-URI field. The Supplier form joins the engine as a four-step form (Identity / Contact / Contract / Scope & status) with the logo and name on one row and a helper on every field; the full-page supplier template is simplified to render the widget. The shell now also emits `form.hidden_fields` so any hidden field submits even when no step lists it. This completes the assets app (5/5 forms on the modal engine).
- **Assets forms migrated to the modal engine (batch 2)**: the Essential asset (four steps: Identity / Security needs / Continuity & data / Relations & status) and Support asset (Identity / Hardware & network / Lifecycle / Relations & status) create / edit forms are split into `Create` / `Update` subclasses over a shared stepped base, with dense column rows (CIA levels, MTD/RTO/RPO, hardware pairs, dates) and a helper on every field; both view pairs set modal titles. Templates reduced to the header icon; FR translations added (using the `bien` vocabulary, consistent with the rest of the app).
- **Assets forms migrated to the modal engine (batch 1)**: the Asset group and Site create / edit forms are split into `Create` / `Update` subclasses over a shared stepped base (two steps each, column rows, a helper on every field) and now set proper modal titles; their templates are reduced to the header icon. FR translations added. The Supplier form is left for a follow-up because its logo upload needs a reusable image-upload widget first.

- **Multi-column rows in the modal form engine**: a step entry can now be a list of cells rendered side by side instead of always full width, with an optional per-cell width (`"auto"` or a 1-12 Bootstrap span) - e.g. `[[("icon", "auto"), "name"], "description"]`. Coverage validation flattens rows, so the same exactly-once rule applies. Documented in the Forms doctrine.
- **Tightened layouts across the migrated forms**: column rows are applied to every migrated context form and the compliance Mapping form (paired short selects, date pairs, threshold pairs, contact email/phone, etc.), so steps read denser without scrolling. The Scope icon picker sits inline with the name and drops its own helper (a self-evident adornment control may omit it, per the refined doctrine); its button height matches the inputs for clean alignment.

- **Form doctrine in the brand guidelines**. The `Forms` section of `docs/brand/brand-guidelines.md` is rewritten around a single modal-first model: every form opens as an overlay above the dimmed interface (never a new page), built from one reusable shell and field partial. Create and edit become distinct forms (one form per action, no `instance.pk` branching), forms never scroll vertically (large forms split into a multi-step modal), the user always sees a step indicator or a required-fields completion meter, required fields are marked and counted, and every field carries a mandatory always-visible helper. The retired single-column / two-column page-form and standalone delete-page patterns are documented as superseded; deletion becomes a confirmation modal.
- **Create / edit forms now open in a centered modal** instead of a right-side offcanvas drawer. The shared `includes/modal_form.html` shell and the global `#itemDrawer` container (in `templates/base.html`) were converted to a Bootstrap modal; the swap region id (`drawer-form-content`) and the shared `HtmxFormMixin` flow are unchanged, so all existing forms switch over without per-entity template changes. First step of the modal form refactor (declarative steps, progress tracking and per-field helpers land per form next).
- **Declarative step model for modal forms** (`core.modal_forms`): a form mixes in `SteppedFormMixin` and declares ordered `Step(title, icon, fields)` groups as the single source of truth for its grouping and ordering; the declared steps must cover every visible field exactly once (validated at instantiation). A reusable `includes/form_field.html` partial renders the label / control / helper / error anatomy. Engine foundation for the per-form migration (no form consumes it yet).
- **Context forms migrated to the modal engine (batch 2)**: the Objective, Indicator and Predefined indicator create / edit forms are split into `Create` / `Update` subclasses over a shared stepped base, each with three declarative steps and a helper on every field; the Indicator update view keeps its dynamic create/update form selection (predefined vs standard). Their modal templates are reduced to the header icon; FR translations added.
- **Reusable `IconPickerWidget` + Scope form migrated**: the Scope icon picker (preview, clear, searchable Bootstrap-icon grid popover) is extracted into a reusable `context.widgets.IconPickerWidget` with a widget template and generic data-attribute JS in `base.html`, so it works inside the modal. The Scope form joins the engine as a four-step form (Identity / Boundaries / Sites & people / Dates & tags) with a helper on every field. This completes the context app (8/8 forms on the modal engine).
- **Context forms migrated to the modal engine (batch 1)**: the Issue, Activity, SWOT analysis and Stakeholder create / edit forms are split into `Create` / `Update` subclasses over a shared stepped base, each with two or three declarative steps and a helper on every field; their modal templates are reduced to the header icon. FR translations added.
- **Inter-framework Mapping form migrated to the modal engine** (single-step pilot): `RequirementMappingCreateForm` / `RequirementMappingUpdateForm` over a shared `RequirementMappingBaseForm` with one declarative step, a helper on every field, and proper `New mapping` / `Edit mapping` modal titles (previously empty). Verified in the browser: live completion meter (`0 of 3 required` -> `3 of 3`), server-side error re-render keeping the modal open and input intact (duplicate-mapping non-field error), create + table refresh, and edit pre-fill.
- **Modal form presentation layer + Role pilot**: the shared shell auto-renders a stepper (multi-step) or a required-fields completion meter (single-step) plus the fields of a stepped form, driven by generic attribute-based JS (step navigation, per-step required-field gating, live meter, focus) and brand-compliant CSS - no per-entity JS. The Role create / edit forms are the first migration: split into `RoleCreateForm` / `RoleUpdateForm` over a shared `RoleBaseForm`, two declarative steps, and a helper on every field; the entity template is reduced to its header icon. Legacy (unmigrated) forms are unaffected (they keep their hand-written fields and a plain footer). Verified end to end in the browser: create, per-step validation gating, light and dark themes, save and list refresh.

### Fixed

- **Multi-step modal forms could not be submitted** ("An invalid form control with name=... is not focusable"): native browser validation tried to focus a constrained field (e.g. `contact_email`, `website`) sitting on a hidden step, which aborted the submit. Multi-step forms now carry `novalidate`; validation is gated per step in JS and enforced server-side, which re-renders the modal on error. Verified by creating a supplier end to end.

## [0.24.5] - 2026-06-10

### Changed

- Move CI back to GitHub Actions: the `Tests` workflow now also runs `ruff check` as a quality gate, and `docker-publish.yml` publishes release images to Docker Hub (`frousselet/cairn`) on version tags. Documentation, the Dockerfile image source label, the published-image instructions and the CHANGELOG comparison links now point to GitHub instead of GitLab.

### Removed

- GitLab CI configuration (`.gitlab-ci.yml`) and GitLab references across the README, `CLAUDE.md` and module specs.

## [0.24.4] - 2026-06-02

### Fixed

- **Migration `assets.0029` crash on duplicate empty Site reference**. The data migration that converts `SupportAsset[type=site]` rows into `Site` records called `Site.objects.create()` without setting `reference`. Migrations get the historical model frozen by `apps.get_model()`, which does not include the `ReferenceGeneratorMixin.save()` override responsible for generating `SITE-N`, so every new Site was inserted with an empty `reference` and the second insert collided with the first on the `unique=True` constraint (`duplicate key value violates unique constraint "context_site_reference_a8056d23_uniq"`). The migration now computes the next index from existing `SITE-` references and assigns `reference` explicitly on each create.

## [0.24.3] - 2026-06-02

### Fixed

- **Browser Back getting stuck after the first pop**. The previous fix (v0.24.2) disabled the HTMX history cache so every popstate triggers a fresh GET, but `loadHistoryFromServer` was falling back to a whole-body innerHTML swap (no `hx-history-elt` was set). That re-injected every inline `<script>` block that lives in `<body>` (boost wiring, drawer, tabs, sort persistence) on each Back, stacking duplicate listeners and silently breaking the second pop. `#page-shell` now carries `hx-history-elt` so popstate restores stay scoped to the shell, and a new `htmx:historyCacheMissLoad` listener syncs `document.title` from the response (our boosted `htmx:beforeSwap` hook does not fire on popstate-driven swaps because the request is not marked `boosted`).
- **Sidebar active highlight not following Back/Forward navigation**. The sidebar's active-link refresh was wired to `htmx:afterSettle` only, which fires for forward boosted swaps but not for popstate-driven restores (`loadHistoryFromServer` does not run the full request lifecycle). The refresh now also listens to `htmx:historyRestore`, so the active item, `aria-current` and the auto-expanded section follow the URL on every Back / Forward.

### Added

- **#70 : user-selectable display theme (Light / Dark / System)**. Adds `User.theme_preference` (default `system`, choices `light` / `dark` / `system`) exposed through the profile form (Preferences card), the DRF `MeSerializer` / `UserDetailSerializer` / `UserCreateSerializer`, the login response, and a new `update_me` MCP tool (which also lets external clients edit first_name, last_name, phone, language, timezone). The inline FOUC-safe theme bootstrap script (factored across `templates/base.html`, `accounts/templates/accounts/login.html` and `mcp/templates/mcp/authorize.html`) reads the server-rendered `data-theme-preference` attribute on `<html>`, falls back to `localStorage`, then to `prefers-color-scheme`, and only re-reacts to OS changes when the preference is `system`. Profile changes apply instantly via `window.cairnTheme.apply()` before the form is even submitted. Migration `accounts.0039`.

## [0.24.2] - 2026-06-02

### Added

- **MCP server URL surfaced in the profile UI**. The OAuth credentials card on the profile page now exposes the MCP endpoint URL (`{scheme}://{host}/api/v1/mcp`) with a copy button at the top of the card and inside the secret-display modal that opens after creating credentials. A short hint clarifies that the URL is what gets pasted into Claude Desktop / Claude Code (which register themselves automatically via PKCE), while the manually created credentials are only needed for server-to-server scripts using the `client_credentials` grant. Resolves user confusion about which URL to point their MCP client at after creating credentials
- **`consolidate_iso27005_risk` MCP tool**: materialises an ISO 27005 analysis (threat × vulnerability) into a `Risk` in the unified register, preserving the source link via `source_entity_id` / `source_entity_type`, copying the criteria snapshot and the affected-assets M2M. Idempotent. Closes the consolidation gap previously only addressed by the EBIOS operational-scenario tool
- **`download_report` MCP tool**: retrieves the binary content of a previously generated report as a base64-encoded string with content type, size and original filename. `list_reports` now also follows the standard `{total, items, limit, offset}` envelope
- **`Indicator.owner` (FK to User) + `linked_objectives` / `linked_requirements` M2M** to anchor the indicator-to-objective/control traceability required by ISO 27001 §6.2 / §9.1 (QA report #20). Migration `context.0026`. Exposed on both the DRF serializer and the MCP tool
- **Specifications restructured under `docs/modules/`**, one directory per module (`m0-accounts/`, `m1-context/`, `m2-assets/`, `m3-compliance/`, `m4-risks/` with the `ebios-rm/` sub-module, `management-review/`) and one Markdown file per domain entity. Each module's `README.md` keeps the cross-cutting sections (business rules, API conventions, permissions, UI, technical considerations). The monolithic `features_spec/M0-M4` files are removed. Includes a brand-new spec for the previously undocumented Indicator / IndicatorMeasurement entities. Closes the Indicators documentation gap flagged by #20 and aligns the layout with how feature changes are actually made (one file = one entity = one focused diff)

### Changed

- **MCP tool surface aligned with the data model on 30+ entities**. The generic MCP CRUD layer previously exposed only a minimal subset of each model's fields (`scopes` M2M and most descriptive attributes were silently dropped from both writes and reads). Every entity inheriting `ScopedModel` now accepts `scope_ids` on create/update through the existing `m2m_fields` mechanism and returns the resolved scope list in `list_fields`. Concretely:
  - **Context**: `Issue`, `Stakeholder`, `Objective`, `SwotAnalysis`, `SwotItem`, `Role`, `Activity`, `Indicator` now expose their full set of writable fields (trend, source, review_date, contact details, target/current values, measurement method/frequency, progress_percentage, related_issues/stakeholders/objectives, validated_by/at read-only, is_mandatory + source_standard + assigned_users for `Role`, etc.). `Objective` exposing `progress_percentage` makes the `achieved` status reachable for the first time. `Indicator` declares `first_review_date` and `review_frequency` as required.
  - **Assets**: `EssentialAsset` exposes DIC justifications, MTD/RTO/RPO, data_classification, personal_data + categories, regulatory_constraints, related_activities. `SupportAsset` exposes location, manufacturer, model_name, serial_number, software_version, operating_system, acquisition/warranty/contract dates, exposure_level, environment, parent_asset_id, plus inherited DIC trio read-only. `AssetGroup` accepts members (support assets). `AssetDependency.redundancy_level` becomes writable. `Supplier` accepts `scope_ids`.
  - **Risks**: `Threat` exposes is_from_catalog and the `other` enum value; `Vulnerability` exposes affected_asset_types, affected_assets M2M, cve_references, is_from_catalog. `RiskAssessment` exposes `methodology` (`iso27005` / `ebios_rm`), summary, next_review_date. `RiskCriteria` accepts `scope_ids`. `Risk` exposes risk_source, source_entity_{id,type}, the three DIC impact booleans, treatment_justification, review_date and the affected_essential_assets / affected_support_assets / linked_requirements M2M trio. `ISO27005Risk` exposes affected_essential_assets and affected_support_assets M2M. `RiskAcceptance` exposes review_date and surfaces accepted_at / risk_level_at_acceptance read-only.
  - **Compliance**: `Framework` exposes framework_version, the four key dates, issuing_body, jurisdiction, url, is_mandatory, is_applicable, applicability_justification, related_stakeholders. `Section` accepts the human-readable `reference` (e.g. "A.5"). `Requirement` exposes category, applicability_justification, target_date, status and linked_assets / linked_stakeholder_expectations M2M. `ComplianceAssessment` accepts `scope_ids` on create/update and returns scopes + frameworks on read. `ComplianceActionPlan` wires `requirements`, `assignees`, `findings`, `risks` and `scopes` through the M2M mechanism, exposes start_date / completion_date / cost_estimate / originating_review_id. `Scope` exposes parent_scope_id, icon, boundaries, justification_exclusions, geographic/organizational/technical scope blocks and the included/excluded sites M2M; the detail view now returns the full representation (was returning the list view's reduced field set).
- **Generic FK kwarg routing in MCP create/update/batch handlers**. Django's `Model.__init__` and `setattr` refuse raw PK values when the kwarg key matches the FK field name itself ("type=12") and only accept the descriptor form ("type_id=12"). The MCP tool schema exposes the natural attribute name on many entities, so any tool that forwarded the kwarg verbatim failed at instantiation. Two new helpers (`_resolve_model_field` and `_fk_kwarg_name`) centralise the resolution and the rewrite, applied uniformly through the generic CRUD handlers and the bespoke `ComplianceAssessment` create/update handlers. Fixes the long-standing `Supplier.type` "Cannot assign 12: must be a SupplierType instance" failure and any other entity following the same pattern
- **`_serialize_obj` extended to handle M2M and reverse-FK managers**. The serialiser previously stringified every non-scalar value (turning booleans into `"True"`, JSONField dicts into their Python repr, M2M managers into their internal `<ManyRelatedManager>` repr). It now expands managers into lists of PK strings and preserves native bools / ints / floats / dicts as-is in the JSON response
- **`OperationalScenario` enum aligned with `RiskSourceType`**. The MCP schema for the `risk_source` field on `Risk` now lists the actual TextChoices values (`iso27005_analysis`, `ebios_strategic`, `ebios_operational`, `incident`, `audit`, `compliance`, `manual`) instead of an outdated shorter list
- **`ThreatCategory` gained the missing `OTHER` value** (purely a TextChoices addition, no migration needed) to align with the other taxonomies and the QA expectations
- **`is_single_point_of_failure` removed from writable fields of site_asset_dependency and site_supplier_dependency**. The SPOF flag is auto-computed by the SPOF detection service; exposing it in writable_fields let MCP clients silently override the computation. Help-text marks the field read-only
- **MCP profile UI**: the OAuth credentials card and create modal expose the canonical MCP endpoint URL with a copy button (see Added)

### Fixed

- **#45 : assessment closure no longer clobbers requirement statuses**. Closing a `ComplianceAssessment` previously walked every `AssessmentResult` and overwrote the linked `Requirement.compliance_status` with the result's value, including for `not_assessed` rows : destroying previously-evaluated states across assessments. The transition handler now delegates to `assessment.recalculate_counts()`, the canonical pipeline that treats `not_assessed` as zero (never clobbering an existing meaningful score) and falls back through the latest-truly-evaluated result for `evaluated` placeholders.
- **#46 : overall compliance no longer counts NOT_APPLICABLE at 100 %**. `ComplianceAssessment.overall_compliance_level` now excludes `NOT_APPLICABLE` requirements from both the numerator and the denominator (SoA convention: a requirement that does not apply must not pull the average toward 100 %).
- **#41 / #42 : section compliance now propagates to ancestor sections**. `ComplianceAssessment.recalculate_counts` and the direct requirement-edit endpoint both walk up from each affected section to its root and recalculate the root; `Section.recalculate_compliance` already cascades down, so refreshing the root recomputes the whole branch. Parent sections (e.g. ISO 27001 "Annex A") finally reflect the levels of their sub-sections instead of staying stuck at zero.
- **#48 : `RequirementMapping` auto-creates the symmetric inverse row**. `equivalent` ↔ `equivalent`, `partial_overlap` ↔ `partial_overlap`, `includes` ↔ `included_by`, `related` ↔ `related`. The check is idempotent (looks up the reverse pair via `.exists()` before creating) so the recursive `save()` from the inverse row short-circuits immediately, and the unique-mapping constraint guards against duplicates. Four new tests in `compliance/tests/test_models.py` exercise the three inversion cases plus idempotency.
- **#49 : `ComplianceActionPlan` M2M relations are now assignable through MCP**. `requirements`, `assignees`, `findings`, `risks` and `scopes` are wired through the existing `m2m_fields` mechanism (renaming the schema arguments to `*_ids` for consistency with the rest of the surface). The generic create handler calls `.set()` on the manager after `save()`, sidestepping the DRF "Direct assignment to the forward side of a many-to-many set is prohibited" error.
- **#59 : `RiskTreatmentPlan.save()` flips in-flight plans to OVERDUE when `target_date` is past (RS-04)**. The `mark_overdue_treatment_plans` cron remains useful for rows that became stale without anyone touching them; the hook just keeps freshly-written rows accurate. Tests use raw `objects.filter().update()` to construct the stale state that exercises the cron.
- **#60 : `RiskAcceptance.save()` now stamps `accepted_at` and `risk_level_at_acceptance` whenever the acceptance is active and the fields are still null (RV-05)**. The acceptance instant and the risk level at acceptance no longer get lost the moment the linked risk score moves.
- **#34 : `Supplier.type` ID resolution fixed end-to-end**. Django's `Model.__init__` refuses raw PK values when the kwarg key matches the FK field name itself; the MCP layer previously forwarded `Supplier(type=12)` which failed with "Cannot assign 12: must be a SupplierType instance". The new `_fk_kwarg_name` helper rewrites every FK kwarg key to the `_id` form transparently, so any FK exposed by its natural name now works.
- **#41 : direct edits to a `Requirement` now refresh Section + Framework levels**. `Framework.recalculate_compliance` was reading from `AssessmentResult` instead of `Requirement`, so editing a requirement directly (without going through an assessment validation) left the framework level stuck at zero. The method now reads `Requirement.compliance_status` / `compliance_level` directly, consistent with `Section.recalculate_compliance`, and the assessment-driven flow keeps working because `recalculate_counts` already propagates results into the requirement state. A new `compliance.signals` module wires `post_save` / `post_delete` handlers on `Requirement` that walk up the section tree to the root and refresh both Section and Framework, registered through `ComplianceConfig.ready`. Two new tests cover the direct save and delete paths.
- **#21 : `IndicatorMeasurement.recorded_at` is now user-writable**. The field was `auto_now_add=True`, so Django ignored any explicit value passed by callers. Switching to `default=timezone.now` keeps the current-time default behaviour for "now" measurements while letting historical imports backdate the timestamp. Migration `context.0025` rewrites the field; the MCP `indicator_measurement` tool now lists `recorded_at` and `recorded_by_id` as writable.
- **#27 : `SupportAsset.supplier` FK wired**. The model carried a commented-out `supplier = models.ForeignKey("suppliers.Supplier", ...)` stub from a time when the suppliers module didn't exist. The FK is now defined against `assets.Supplier` (SET_NULL on delete, blank/null OK), migrated via `assets.0028`, and `supplier_id` is exposed on the SupportAsset MCP tool. Together with the contract_reference field (already exposed in the earlier batch), service-type support assets can finally be linked to their providing supplier through the API.
- **#18 : `Activity.essential_assets` reverse manager exposed through MCP**. The existing `EssentialAsset.related_activities` M2M already creates a reverse manager on `Activity`; rather than introducing a redundant `linked_assets` column, the Activity MCP tool now accepts `linked_essential_asset_ids` (routed through the reverse manager's `.set()`) and surfaces `essential_assets` in list_fields. Both endpoints of the relation can be alimented and read without a new migration.
- **#31 : `SiteType` enum values renamed from French to English** (`siege` -> `headquarters`, `bureau` -> `office`, `usine` -> `factory`, `entrepot` -> `warehouse`, `site_distant` -> `remote`, `autre` -> `other`; `datacenter` unchanged). The Site entity was the last place still mixing French technical values with the rest of the platform's English convention. Migration `context.0027` rewrites both the live and the historical rows, and the MCP tool schema reflects the new enum. Translated labels for the UI continue to live in the `.po` files.
- **#30 : Site / SupportAsset[type=site] redundancy resolved**. Until now a physical location could be modelled either as a `Site` in the context module or as a `SupportAsset[type=site]` in the asset inventory, with five overlapping sub-categories (`datacenter`, `office`, `remote_site`, `cloud_region`, `other_site`). Site is now the canonical model for physical locations; the `site` type is removed from `SupportAsset` (and so are the five sub-categories). Migration `assets.0029` converts every existing `SupportAsset[type=site]` to a matching `Site` row (`datacenter` and `cloud_region` -> `datacenter`, `office` -> `office`, `remote_site` -> `remote`, `other_site` -> `other`) and drops the legacy rows; cascade removes the dependent `AssetDependency` rows that pointed at sites (their semantics were fuzzy and `SiteAssetDependency` is the canonical link going forward). `Site` is promoted to `ScopedModel` so it accepts `scope_ids` like every other domain entity (migration `context.0028`). MCP and DRF tools, the SupportAsset list filter chip and the help text all reflect the new layout. A new spec lives at `docs/modules/m2-assets/site.md`.
- **WebSocket consumer no longer crashes on Redis read timeout**. `CHANNEL_LAYERS["default"]["BACKEND"]` is switched from `channels_redis.core.RedisChannelLayer` to `channels_redis.pubsub.RedisPubSubChannelLayer`. The historical core layer polls Redis with BLPOP and a finite socket read timeout, so the dashboard WebSocket consumer crashed every few seconds with `redis.exceptions.TimeoutError: Timeout reading from redis:6379` when no event was published in the polling window. The WS reconnected each time but the noise polluted the boot log. PubSub uses push instead of poll: Redis hands a message to the connected consumer when one arrives, there is no waiting-with-timeout to time out. Trade-off accepted: pub/sub does not queue messages for consumers that drop briefly, which is fine for the dashboard refresh broadcasts (the next domain save broadcasts another one) but would not be appropriate for durable work-queue style traffic
- **Boot warning « unapplied migrations » silenced**. Three diffs had accumulated without their matching migration: the Open GRC -> Cairn rebrand on `Indicator.collection_method` / `is_internal` (verbose_name change, never captured), the `risk_register` and `iso27005_report` additions to `Report.report_type` (added in v0.23.0 without an AlterField), and the `OTHER` value added to `Threat.category` during the QA sweep for #52. Three new migrations bundle each app's pending diff: `context.0029_cairn_rebrand_verbose_names`, `reports.0005_report_type_choices_refresh`, `risks.0025_threat_category_add_other`. Pure choices / verbose_name metadata, no DB schema change. Tests didn't catch them because `settings_test` builds the schema from the live model rather than replaying migrations
- **Static files served under uvicorn in DEBUG mode**. `manage.py runserver` auto-mounts static files when `DEBUG=True`, but uvicorn / daphne / gunicorn do not. `core/urls.py` now installs `staticfiles_urlpatterns()` in the DEBUG branch so every entry of `STATICFILES_DIRS` is reachable through `STATIC_URL`. The regression had been latent: `static/js/split-pane.js` is the only external static asset in `base.html` (everything else is inlined as data URIs), so it was the only file 404-ing at container boot
- **SPOF scheduler startup guard rewritten as an explicit allowlist**. `AssetsConfig.ready()` used to start the SPOF background scheduler under "anything that isn't `manage.py <non-runserver-command>`". That misclassified the inline `python -c "..."` blocks the Docker entrypoint runs before `migrate` (database wait, migration-name fixup), so the scheduler kicked off during pre-migration startup and immediately queried tables whose columns the about-to-run migrations would add. With #27's `SupportAsset.supplier` FK in the same release this surfaced as `column assets_supportasset.supplier_id does not exist` in the db logs at container boot. The guard now uses an explicit allowlist (`uvicorn`, `gunicorn`, `daphne`, `hypercorn`, or `manage.py runserver`) so any ad-hoc Python invocation, management command or test runner stays scheduler-free.
- **#51 : ComplianceActionPlan Kanban workflow documented; spec aligned with the 7-state pipeline**. Spec M3 §2.7 listed 5 simple statuses (`planned`, `in_progress`, `completed`, `cancelled`, `overdue`); the implementation runs a Kanban pipeline with 7 states (`new -> to_define -> to_validate -> to_implement -> implementation_to_validate -> validated -> closed`) plus `cancelled`, with mandatory-comment backward refusals and a full transition history. Decision (consistent with #39 / #44 / #47): keep the richer implementation, update the spec. `docs/modules/m3-compliance/compliance-action-plan.md` now documents the full transition graph, the rejection mechanism, the permission gates (`update` vs `approve`), the auto-fill of `completion_date` + `progress_percentage=100` at closure (RP-02 attached to `closed`), and the `is_overdue` computed property as the RP-01 substitute (the QA report flagged that `overdue` was missing from the status enum; `is_overdue` is a computed boolean that the earlier sweep batch already exposed in list_fields). A mapping table relates each spec-original status to its implementation counterpart. No code change.
- **#43 : ComplianceAssessment / spec divergences acked and documented**. The four points the QA report flagged are explicitly entrenched in `docs/modules/m3-compliance/compliance-assessment.md`: (1) multi-framework (the assessment carries an M2M `frameworks` instead of a single FK; the impact on RC-06 is spelled out — a single closure propagates results to the requirements of every linked framework and refreshes each `Framework.compliance_level` and `last_assessment_date`); (2) two-date period (`assessment_start_date` / `assessment_end_date`) instead of a single `assessment_date`; (3) `limitations` instead of `methodology` (methodology lives at the framework or audit-doc level); (4) scope attachment via `scope_ids` (already shipped in the earlier QA sweep batch). No code change.
- **#47 : ComplianceAssessment lifecycle documented; spec aligned with the actual workflow**. The legacy spec advertised `draft -> in_progress -> completed -> validated -> archived` but the implemented workflow is `draft -> planned -> in_progress -> completed -> closed` (+ `cancelled`), with the validation half carried by a separate orthogonal `is_approved` flag. The `validated` and `archived` statuses were unreachable, which the QA report flagged as inconsistent. Decision (option A): keep the implementation, update the spec. `docs/modules/m3-compliance/compliance-assessment.md` now documents (1) the actual transition graph (with the cancelled branch and the `in_progress -> completed -> closed` chain), (2) the mapping legacy-spec-status -> implementation-status (`validated` = `closed + is_approved=true`, `archived` = `closed` terminal), (3) the rationale for keeping approval as an orthogonal axis (decouples internal close from formal sign-off), (4) the per-transition side effects (`completed -> closed` triggers `recalculate_counts` and propagates results to requirements; `approve_compliance_assessment` is signature-only and never recomputes). RC-06 is attached to closure, not approval.
- **#44 : `AssessmentResult.compliance_status` exposes the full 11-value enum (same as Requirement)**. The MCP tool schema was previously listing only 9 of the 11 enum values, omitting `non_compliant` and `partially_compliant` and leaving the QA tester unable to record a partially-compliant result via the API even though the underlying model accepted it. The MCP schema and the help docstring now expose the complete enum and point at the conformance-mapping table in the Requirement spec. The `compliance-assessment.md` spec is updated to document AssessmentResult's actual surface (the `gaps` + `observations` of the legacy spec are fused into `finding`, plus `auditor_recommendations` is added; same 11-value enum as Requirement) and to spell out RC-06's carry-over rules including the NOT_ASSESSED preservation guard from #45.
- **#39 : `Requirement.compliance_status` 11-status enum kept, spec updated to document audit-oriented values**. The legacy spec listed only the five conformance-oriented statuses (`not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable`); the implementation also exposes the six audit-oriented statuses (`evaluated`, `major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`) inherited from the Audits module's `Finding.finding_type`. Reconciling by keeping the richer set (option A): the two families now cohabit in one enum, the conformance-conventions table maps each audit status to its conformance equivalent (used by RC-01 / RC-02 averages), and the `compliance_finding` field name is enshrined as the canonical replacement of the legacy `compliance_gaps`. The rule sheet (RC-01 through RC-06) documents how each status affects calculations and alerts. Single enumeration for Requirement, AssessmentResult and Audits/Finding eliminates the cross-module mapping table.
- **#35 : Suppliers module specified and serialization gaps closed**. Three new docs in `docs/modules/m2-assets/`: `supplier.md` (Supplier + SupplierType + SupplierTypeRequirement), `supplier-requirement.md` (SupplierRequirement + SupplierRequirementReview), `supplier-dependency.md`. The `Supplier` MCP tool already exposed `scope_ids` and `owner_id` (added in the earlier QA sweep); the previously-missing `SupplierDependency.is_single_point_of_failure` (read-only, computed by the SPOF service) and `SupplierDependency.redundancy_level` (operator-set, writable) are now surfaced on the MCP tool, aligning the supplier-dependency exposure with the asset-dependency and site-dependency contracts. The "Suppliers not specced" warning bullet is removed from the m2-assets README.
- **#62 : lists no longer stay stuck on skeletons after browser Back (bfcache restore handled)**. Filtered list pages (`risks/assessments`, `risks/register`, `assets/essential`, `compliance/assessments`) restored from the back-forward cache used to keep the in-flight skeleton placeholder forever because the async list load never re-fired. `templates/base.html` now registers a `pageshow` listener that detects `event.persisted === true` and forces a `window.location.reload()`, recomposing the page from the network so the rows render and the title is restored. Cold loads (`persisted === false`) are untouched to avoid double-fetches.
- **#64 : HtmxFormMixin now distinguishes drawer requests from `hx-boost` soft-nav**. `<body>` carries `hx-boost="true"`, which sends `HX-Request: true` on every boosted navigation. `_is_htmx()` previously returned `true` for any HX request and served the modal partial template for boosted nav too, rendering the bare drawer markup full-bleed without the page chrome whenever the user opened a create/edit URL through soft-nav. The check now requires both `HX-Boosted != true` and `HX-Target == drawer-form-content` so only genuine drawer requests get the modal template; boosted soft-nav falls through to the full-page template. The `test_create_result_via_drawer` test suite is updated to send the matching `HX-Target` header alongside `HX-Request`.
- **#65 : table search field rebinds after HTMX partial swaps**. `templates/base.html` table-search wiring was an IIFE that ran once on DOMContentLoaded; after any `hx-target` swap of the table body (or a re-render of the input itself via `htmx:afterSettle`), the input was no longer bound to a `keyup` handler and the filter became a no-op. The handler is now an `initTableSearch()` function called on `DOMContentLoaded` and `htmx:afterSettle`, guarded by a `data-search-bound` flag so multiple settles do not stack listeners. The row snapshot is taken fresh on each `filterRows()` call so the filter still works correctly when only a table body fragment was swapped.
- **#66 : browser Back no longer skips history entries for drawers, modals and detail tabs**. Drawers used to open without pushing a matching history entry, so the first Back navigated to the previous page instead of just closing the drawer; tabs used `history.replaceState` so each tab switch produced zero entries (Back jumped over the tab change entirely). The drawer offcanvas wiring in `templates/base.html` now pushes a `{drawer: '__drawer_open__'}` history entry when the drawer opens and pops it on UI-driven close (X / form save) using an internal-hide flag to avoid the popstate loop; a `popstate` listener closes the drawer when the user presses Back. The tab persistence block now uses `history.pushState` per tab switch with a `suppressPush` guard for initial and popstate-driven restores, plus a `popstate` listener that re-activates the tab matching the current URL hash.
- **#67 : WebSocket `setStatus` no longer throws on missing dot indicator**. `templates/home.html` `setStatus(connected)` accessed `dot.classList` and `dot.title` without a null check, raising `Cannot read properties of null` when the WebSocket connected before the indicator markup mounted or when the dot was removed mid-render. The function now early-returns when `wsStatus` or `dot` is missing, so transient mounting states no longer crash the connection-status indicator.
- **#68 : "Manage" link on "Identify threats" / "Identify vulnerabilities" preserves the analysis context**. The two `Manage` buttons in the ISO 27005 workflow card (`risks/assessment_detail.html`) used to point at the bare `risks:threat-list` / `risks:vulnerability-list` routes, losing the originating risk analysis. They now carry `?assessment={{ assessment.pk }}`; the list views (`ThreatListView` / `VulnerabilityListView`) read that param, fetch the parent `RiskAssessment` and expose it as `parent_assessment` in the context; the list templates render a `← Back to analysis` banner at the top so the user can return in a single click. French translations added.
- **Browser Back regression: stale title and corrupted body cache after boosted nav**. After Dashboard → Management Reviews → Back, the URL and sidebar showed Dashboard but the tab title still said "Management Reviews" and (in some scenarios) the body showed MR content. Root cause: htmx 2.0's `beforeHistorySave` for boosted requests fires AFTER the body swap, so the NEW page's body ends up cached under the OLD URL; on Back, htmx then restores the (corrupted) cache from localStorage. The `<title>` was a related but separate symptom because it lives in `<head>` and is never part of the cached body. Fix: `htmx.config.historyCacheSize = 0` disables the cache entirely, so every Back triggers a fresh GET that fires our boost `beforeSwap` hook (which already parses the response, swaps `#page-shell`, and syncs `document.title`). One extra round-trip per Back is acceptable in exchange for always-correct URL/title/content. Also tightens the drawer `hidden.bs.offcanvas` handler in `templates/base.html` to pop the drawer history entry on any UI-driven close (X button, ESC, form save) by keying off `history.state` directly, so closed drawers never leave stale entries on the stack for a future Back to land on.

## [0.24.1] - 2026-05-31

### Fixed

- **EBIOS backfill migration `risks.0024`**: the data migration that backfills `StudyFramework`, `SecurityBaseline`, `EbiosSummary` and the six `EbiosWorkshopProgress` rows on pre-existing `ebios_rm` assessments was inserting new rows with an empty `reference`. Historical models obtained via `apps.get_model` bypass `ReferenceGeneratorMixin.save()`, so the second insert collided on the `unique=True` constraint (`duplicate key value violates unique constraint "risks_ebiosworkshopprogress_reference_key" DETAIL: Key (reference)=() already exists.`). References are now assigned explicitly per model (`EFRA`, `EBSL`, `ESUM`, `EWSP`) with a locally incremented counter seeded from the current DB max; the migration also heals any `reference=""` rows left by a prior failed run, so it is safe to re-apply

## [0.24.0] - 2026-05-31

### Changed

- **Rebrand from Fairway to Cairn.** New identity: `Cairn`, from Gaelic _càrn_, a deliberate stack of stones built to mark a safe path. The metaphor maps directly to GRC (the cairns guide the way through complex regulatory terrain). Pronounced identically in FR (`/kɛʁn/`) and EN (`/kɛərn/`)
- **New logo system** (responsive two-variant) replacing the previous sailboat illustration. `mark.svg` (stepped cairn inside a C-bowl) for ≥ 24 px usage (sidebar brand, splash, app icon). `mark-sm.svg` (single triangular peak inside the same bowl) for ≤ 22 px usage (favicon, browser tab, low-res OS icon). Same bowl, different inner element based on render size — the system mimics how a real cairn reads from afar (silhouette) versus up close (distinct stones). Logos live in `docs/brand/` (source) and `static/img/cairn_*.svg` (deployed)
- **Identity colour**: indigo `#6366f1` replaced by navy `#1E3A8A` (`#3B5BB8` in dark mode). All `--accent` / `--accent-hover` / `--accent-glow` tokens and the `module-accent-compliance` / `module-accent-dashboard` derivatives are remapped. Hardcoded `#6366f1` / `#4f46e5` / `#818cf8` references in the inline logo SVGs of `templates/base.html` are replaced by the new navy mark
- **Brand guidelines** added at [`docs/brand/brand-guidelines.md`](docs/brand/brand-guidelines.md): the single source of truth for palette, typography (Inter only, no display font, no UPPERCASE on titles), spacing / radii / shadows, iconography (Bootstrap Icons only), components, motion (`--ease-out`, 150/220/320 ms durations, `prefers-reduced-motion` honoured), accessibility (WCAG 2.2 AA criteria covered), voice and tone (sober, precise, action-oriented, bilingual)
- All 148 templates that referenced "Fairway" in `{% block title %}` or body text are updated. The Python code (settings, `WSGI_APPLICATION`, MCP server name, ICS feed prodid, image-utils User-Agent, report fallback company names, model field labels) renamed to Cairn. The French `.po` translation file, the Dockerfile, the GitLab CI workflow, the `features_spec` markdown documents and the `CLAUDE.md` project description all updated. Historical CHANGELOG entries (which mention the Fairway-era releases) are preserved as record
- Old logo proposals in `logo_proposals/` and the old `static/img/fairway_*.svg` files removed

### Added

- UX audit Phase 0 (quick wins): global `.tabular-nums` utility class; ARIA live region (`#hx-live`, `role="status"`, `aria-live="polite"`) wired to HTMX `afterRequest` so successful POST/PUT/PATCH/DELETE announce a localized status ("Saved", "Deleted") to assistive tech (WCAG 4.1.3 Status Messages). Backends can override the announcement via the `X-Live-Announce` response header
- Global `prefers-reduced-motion: reduce` guard in `templates/base.html` to neutralize animations and transitions for users who request reduced motion (WCAG 2.3.3)
- UX audit Phase 1 (shared component library): new `core/templatetags/ui.py` module loaded with `{% load ui %}` that exposes ten reusable Django template tags. Each tag has a partial under `templates/components/` (`badge.html`, `page_header.html`, `empty_state.html`, `kpi_card.html`, `approval_banner.html`, `sidebar_card.html`, `filter_chip.html`, `confirm_delete.html`, `bulk_actions_bar.html`, `stepper.html`) and matching CSS classes in `templates/base.html`. Tags: `{% badge value type=... %}` backed by a `BADGE_REGISTRY` mapping enum values to (variant, icon, translated label) for `approval`, `severity`, `risk` and `status`; `{% page_header title subtitle=... reference=... icon=... %}...{% endpage_header %}` block tag with an action slot; `{% empty_state icon=... title=... message=... cta_url=... cta_label=... colspan=... %}` (block-level or table-row when `colspan` is set); `{% kpi_card icon value label variant trend trend_label href %}` with automatic trend direction; `{% approval_banner obj can_approve=... approve_url=... %}` superseding the previous inline-style `includes/approval_badge.html`; `{% sidebar_card title icon sticky %}...{% endsidebar_card %}` block tag for the right column of 2-column detail layouts; `{% filter_chip label param value count icon variant %}` that toggles a query parameter while preserving every other parameter; `{% confirm_delete url name label %}` rendering a button + Bootstrap modal pair with a per-call unique id; `{% bulk_actions_bar target_id actions label %}` for the floating bulk-action bar pattern; `{% stepper steps next_status transition_url cancelled can_cancel can_refuse refusal start_value branch_value terminal_value transition_modal_callback entity_id %}` consolidating the four copies of the workflow stepper currently scattered across `compliance/action_plan_detail`, `compliance/assessment_detail`, `risks/assessment_detail` and `reports/management_review_detail` into one component. A `build_steps()` helper turns `[(value, label), ...]` into `[Step(value, label, state), ...]` for the views
- `/styleguide/` page (`core.views.StyleGuideView`) rendering every shared component in its supported variants and the design-token palette: serves as the living reference and a regression checkpoint
- 38 new tests in `core/tests/test_ui_tags.py` covering registry lookup, override semantics, ARIA attributes, query-string toggling, sticky / non-sticky sidebar, modal id uniqueness, build_steps state inference and the `/styleguide/` end-to-end render
- French translations for every new user-facing string introduced by the component library and styleguide
- UX audit Phase 2 (design tokens): three-layer token system in `templates/base.html`. The new primitive layer exposes a curated Tailwind-aligned palette (`--color-slate-*`, `--color-charcoal-*`, `--color-indigo-*`, `--color-emerald-*`, `--color-amber-*`, `--color-red-*`, `--color-cyan-*`) that the semantic tokens now consume via `var()`. The component layer remains co-located with each component definition. Templates should still consume semantic tokens; the primitive scale is available for new components that need fine-grained control without inventing hex codes

### Changed

- UX audit Phase 2 (dark mode): repainted the `[data-bs-theme="dark"]` palette from cool slate-blue surfaces to the warm-charcoal band considered the 2026 B2B SaaS convention (`#0E1116` page, `#16181C` surface, `#1B1E24` raised, `#E6E8EB` text). Pure black is dead for product UI: warm grays read better in long sessions and avoid OLED halation. All sidebar overrides now reference the new charcoal primitives so dark mode contrast tracks the design system
- UX audit Phase 3 (anchor migrations): adopted the Phase 1 components on two representative templates so the patterns are anchored in the codebase. `risks/risk_list.html` now uses `{% page_header %}` (with descriptive `aria-label` on every icon-only action button), `{% badge value type="severity" label=... %}` for the priority pill (one of the ~202 inline status conditionals identified in the audit), `.tabular-nums` on the current-risk-level column, an `aria-label` on the row edit button, and `{% empty_state colspan=12 ... %}` for the empty register. `context/role_detail.html` was migrated from the legacy nav-tabs layout to the canonical 2-column cards pattern (col-lg-8 main + col-lg-4 sticky sidebar) with collapsible `<details>` cards for Responsibilities / Users / History sections, `{% sidebar_card %}` for Status & Tags, `{% badge %}` for status and RACI type, and `{% empty_state %}` for the empty Responsibilities / Users sub-lists. The remaining list and detail pages keep their current layout - they can adopt the components incrementally by following these two examples
- UX audit Phase 4 (command palette): the existing Cmd+K / Ctrl+K global search overlay is upgraded into a proper command palette. The `GlobalSearchView` endpoint now returns two extra groups when the query is empty or under two characters: a "Navigation" group with 17 entries covering every primary list view (Dashboard, Scopes, Issues, Risks, Requirements, Compliance assessments, Action plans, Calendar, ...), and an "Actions" group with permission-gated quick actions ("Create a risk", "Create a requirement", "Create an action plan", ..., "Open styleguide"). Each action checks the relevant `module.feature.create` permission via `user.has_perm()` so users only see actions they can perform. The frontend in `templates/base.html` now opens the palette with the navigation group already populated (no more blank state) and rebuilds it automatically when the input is cleared. Accessibility: the input gains `role="combobox"`, `aria-controls="searchResults"`, `aria-expanded="true"`, `aria-autocomplete="list"` and a synced `aria-activedescendant` pointing at the highlighted result; the results container becomes `role="listbox"`; each result item gets a unique id, `role="option"` and `aria-selected` toggled by keyboard navigation. The placeholder copy switches from "Search across all items..." to "Search or jump to..." to communicate the broader command-palette intent. The 3 existing tests on the empty-query contract are rewritten to assert the new behaviour, and one new test exercises the per-permission filtering on the Actions group
- UX audit Phase 5 (split-pane scaffolding): new `.split-pane` / `.split-pane__list` / `.split-pane__row` / `.split-pane__detail` CSS pattern in `templates/base.html` for the Linear-style master-detail layout, and a self-contained `static/js/split-pane.js` (loaded once globally, no-op if no `.split-pane` is present) that provides j/k and ArrowUp/ArrowDown keyboard navigation, Enter to open full-page, Escape to clear the detail panel, URL synchronisation via a `?focus=<id>` parameter (configurable via `data-split-param`), and ARIA `role="listbox"` / `role="option"` / `aria-selected` semantics. The pattern is documented on `/styleguide` with three demo rows. The actual migration of risks / requirements / essential-assets lists is deferred to a dedicated PR because each detail view first needs a partial-rendering mode
- UX audit Phase 6 (WCAG 2.2 AA polish): sidebar JS now sets `aria-current="page"` on the active sidebar link (WCAG 2.4.4 Link Purpose, 2.4.7 Focus Visible context); the styleguide gains a dedicated "Accessibility - WCAG 2.2 AA" section that documents the six criteria the codebase already satisfies (2.4.7 Focus Visible via global `:focus-visible` 2px accent ring, 2.3.3 Reduced Motion via global guard, 4.1.3 Status Messages via `#hx-live` region, 4.1.2 Name/Role/Value via the command palette combobox pattern, 2.4.4 Link Purpose via `aria-label` on icon-only buttons, 2.5.8 Target Size 24x24 with current `.btn-header-action` at 32x32). Full mobile audit and column-reorder / kanban drag alternatives (WCAG 2.5.7) are deferred to a dedicated PR alongside the Phase 5 list migrations
- UX audit "Premium polish" pass: visible product-grade repaint that bumps the whole product out of "Bootstrap admin 2018" territory. Eight axes of change, all contained to `templates/base.html` (no behaviour change, no test impact). (1) Light theme palette swapped from cool-blue (`#f0f4f8` bg, `#e2e8f0` borders, `#0f172a` text) to warm-stone (`#FAFAF8` bg, `rgba(28,25,23,.07)` subtle borders, `#1C1917` text); new `--color-stone-*` primitives. (2) Semantic chromas calmed: `--success #10b981 -> #059669`, `--warning #f59e0b -> #D97706`, `--danger #ef4444 -> #DC2626`, `--info #06b6d4 -> #0891B2` - same hues, lower saturation, less competing-for-attention. (3) Shadows recalibrated: warmer rgba base, less Y, more spread, lower opacity; border-light reduced from a solid grey to `rgba(28,25,23,.07)` so depth is carried by shadow and spacing, not crisp grey lines. (4) Larger radii: `--radius-lg 1rem -> 1.125rem`, `--radius-xl 1.25rem -> 1.375rem`. (5) Typography ladder rebuilt: body 13px -> 15px with line-height 1.5 -> 1.6; `h1 24px -> 32px`, `h2 20px -> 24px`, `h3 17.6px -> 20px`, all with tighter letter-spacing; mobile `h1/h2` no longer shrink to 20/17 but only down to 26/20. (6) Sidebar links breathe: padding `7px x 20px -> 10px x 20px`, font 13px -> 14px, weight 450 -> 500. (7) Cards calmed: `.card:hover` no longer triggers a shadow lift - that mannerism reads as "this is clickable" and was applied to every static content card; opt-in `.card--linked` keeps the lift for genuinely interactive cards. `.card-body` padding 22/24px -> 26/28px; `.card-header` gains real padding (16/24px). Stat cards lose the rainbow ribbon (`::before` linear-gradient on top), the `:hover` lift, the icon scale animation; padding goes 20/22px -> 26/26px; `.stat-card-value` goes 28px -> 32px with tighter letter-spacing. (8) Buttons less chunky: font 13px -> 14px, padding `7px x 16px -> 8px x 18px`, weight 500 -> 550; `.btn-primary` loses the permanent box-shadow; `.btn-outline-primary` becomes a true outline button (light border, surface background) instead of an accent-coloured outline. Z-index hierarchy documented and fixed: `.user-header-bubble` lowered from 1040 to 900 so it stops potentially covering sticky `.bulk-actions-bar`; `.bulk-actions-bar` repositioned with `top: 1rem` and a sober surface background so it doesn't look like an alert
- Home dashboard hero redesigned: the gradient violet `.hero-section` that read as "marketing landing" is replaced by a sober "Overall compliance" card. Eyebrow label ("OVERALL COMPLIANCE") in muted small-caps + 40px hero number with a subtle semantic delta-icon (good/warn/bad) next to it + a calm one-line hint + a 10px rounded progress bar with start/target/end legend underneath. Same data, ten times less visual noise, fits the audit-grade workflow tone rather than competing with it
- UX audit "Character pass": five complementary moves to give the otherwise-calm UI a recognisable personality without compromising audit-grade gravitas. (1) Module accents: each of the seven business modules + the dashboard owns a hue (`risks=red`, `compliance=indigo`, `assets=teal`, `context=violet`, `reports=amber`, `accounts=slate`, `helpers=cyan`, `dashboard=indigo`), exposed as `--module-accent-*` / `--module-accent-*-soft` CSS variables tuned per theme. `{% page_header accent="..." %}` now renders the title inside a tinted band with a 4 px left accent bar and a permission for an `eyebrow="..."` uppercase tag above the h1 - immediate editorial "where am I" signal. (2) Editorial line-art illustrations: 8 custom SVGs (`shield`, `folder-check`, `scroll`, `seal`, `network`, `calendar`, `building`, `search-chart`) in `core/templatetags/ui.py` (`ILLUSTRATIONS` dict) rendered through the new `{% illustration name size %}` tag or by passing `illustration="..."` to `{% empty_state %}`. Style: stroke-only, currentColor for the base lines + `var(--accent)` for the meaningful element, inherits the text colour so both themes work without overrides. (3) Bigger home dashboard hero: the overall compliance number jumps from 40 px to 64 px with -.04em letter-spacing, and gets a 40 px circular delta icon - confident editorial signature instead of a polite digit. (4) Pill-style reference codes: `.ref` (used on `RISK-001`, `ASST-042`, etc.) used to be a faint mono italic that vanished into the page; it now renders as a small mono-uppercase pill with a subtle surface background, border and tracked letter-spacing - the audit-grade primary key looks like one, and the `a.ref` variant hover-shifts to the accent palette. (5) Anchor templates updated: `risk_list.html` adopts `accent="risks"` + `illustration="shield"` on the empty state; `context/role_detail.html` adopts `accent="context"`; the `/styleguide` page gains a module-accent gallery (one banner per module), a `.ref` showcase, the 8-illustration catalogue and a side-by-side empty-state demo (icon vs illustration variant). 11 new tests in `core/tests/test_ui_tags.py` cover the accent modifier classes, the eyebrow rendering, the illustration fallback to icon, the `{% illustration %}` tag with size override, the registry closure and the SVG well-formedness of every shipped illustration

### Changed

- Impersonation banner styles moved from inline `style="..."` to reusable `.impersonation-banner` / `.impersonation-banner__stop` classes; the hardcoded `#f59e0b` gradient stop now uses `var(--warning)` so it tracks the theme token
- `templates/includes/approval_badge.html` no longer relies on inline styles; rendering now uses dedicated `.approval-badge`, `.approval-badge--approved`, `.approval-badge--pending` and `.approval-badge-meta` classes. Icons are flagged `aria-hidden="true"` to prevent screen-reader duplication of the visible label
- `templates/home.html` dashboard hero and framework / objective progress numbers now rely on the `.tabular-nums` utility instead of inline `font-variant-numeric: tabular-nums` style attributes
- **HTMX hx-boost navigation**: clicking any internal link (sidebar, breadcrumb, pagination, filter chip, table row) now swaps only `<main id="page-shell">` instead of triggering a full page reload. The sidebar (with its scroll position, open sections, hover state) stays mounted across navigations. `<body>` carries only `hx-boost="true"` - the swap target, response selector and swap mode are set per-request via a `htmx:beforeSwap` hook so that the existing HTMX patterns (drawer forms with `hx-target="#drawer-form-content"`, in-place table-body refresh, stepper transitions) are not polluted by inherited boost attributes. The hook also syncs `<title>` from the response and scrolls back to top. While the request is in flight a shimmer-skeleton (eyebrow + title + two card skeletons with linear-gradient `fw-skeleton-shimmer` animation) replaces the shell after a 120 ms grace period so fast swaps do not flash. `prefers-reduced-motion: reduce` collapses the shimmer to a static placeholder. Login and logout forms opt out via `hx-boost="false"` because they need the browser session round-trip. The active-sidebar-link highlight is refactored into a `syncActive()` function that re-runs on every `htmx:afterSettle` so the highlight follows the user across boosted navigations
- **Page header unification**: every list and detail template now uses `{% page_header title eyebrow=_("<section>") accent="<module>" %}` instead of inline `<h1>` or `<h2>` headers. The eyebrow label matches the sidebar section that hosts the page (Governance / Assets / Risk management / Compliance / Administration), so the user always knows where they are. Pages that sit at the sidebar top level (Reports, Management reviews) carry no eyebrow per the rule "no section, no eyebrow". All `--module-accent-*` tokens are aliased to the single brand colour `var(--accent)` (navy) in both themes - per-module hues were rejected as too noisy on top of an already calm canvas. The eyebrow + 2 px underline visual still signals "you are inside a module" but with one identity colour everywhere. Header action buttons (`+ New X`, exports, view toggles) standardised across 38 templates: `+` creates use `btn btn-primary` with the icon AND the localized label (no more 32 x 32 icon-only circles), secondary actions use `btn btn-outline-secondary`. Dead `.btn-header-action` CSS removed. `main-content` top padding bumped from 3 rem to 7 rem (light / 6.5 rem tablet / 6 rem mobile) so the title clears the floating user bubble at top-right
- **Form unification across every CRUD screen**: 6 confirm-delete templates rewritten on a canonical pattern (page-header + named object + irreversibility hint + danger button with `bi-trash` icon + outline-secondary cancel). All 63 form templates (page, drawer, EBIOS partial) carry the standardised parts: `bi-check-lg` icon + localized label on the Save button, `form-actions-sticky` action bar, non-field errors rendered as `alert alert-danger` immediately after `csrf_token`, per-field `invalid-feedback.d-block` errors, hidden-field guard `{% if field.is_hidden %}{{ field }}{% else %}…{% endif %}` so hidden inputs don't render as empty `mb-3` rows, checkbox branch in iterator templates, required `*` suffix on the label, conditional Edit / New title via `{% page_header page_title %}` with `{% trans "Edit X" as page_title %}` pre-binding. Global autofocus script in `templates/base.html` focuses the first eligible (visible, enabled, non-checkbox / radio / submit) input of every form on initial render and after each HTMX swap, with an opt-out via `data-no-autofocus` on the form
- **Forms section added to brand guidelines** (`docs/brand/brand-guidelines.md` § 8). New top-level section ahead of Motion that documents: the four patterns at a glance (drawer / single-column / two-column / confirmation) with pointers to anchor templates; field anatomy (label / control / helper / error) with the canonical snippet and per-slot spec; the seven visual states (default / hover / focus / filled / placeholder / disabled / invalid); layout recipes; field grouping by meaning (Identity / Analysis / Status / Relations / Tags); required vs. optional rule (trailing `*`, never "(optional)"); action order and hierarchy (Save left, Cancel right, danger never beside Save, sticky bar for long forms); create vs. edit pattern; the dedicated delete-confirmation recipe; the widget reference table (text / textarea + Jodit / select + TomSelect / tags / date / checkbox / scope tree / file upload); validation rules; accessibility commitments (label association, autofocus, tab order, target size, semantic required); and copy do / don't pairs specific to forms
- **Default user avatar repainted**: the topbar avatar yellow circle (`var(--warning)`) with "..." placeholder is replaced by a navy-soft gradient surface with the user's initials. New `initials` template filter in `accounts/templatetags/accounts_tags.py` returns up to two uppercase letters from the display name ("François Rousselet" -> "FR", "François" -> "F", "" or `None` -> "?"). Replaces the buggy `{{ display_name|truncatechars:1 }}` pattern that always rendered `...` because Django's truncatechars counts the marker in the length budget. Applied across topbar, profile page, user detail, user list, calendar subscription list and company settings. The pattern `linear-gradient(135deg, var(--accent-soft), color-mix(in srgb, var(--accent) 18%, transparent))` is now the single avatar-fallback recipe app-wide
- **Empty state pattern across every list**: 42 templates (list pages + table-body partials) now use `{% empty_state title=_("No X yet.") message=_("…helper sentence…") colspan=N %}` instead of `<tr><td colspan="N" class="text-muted">No X</td></tr>`. Each empty state carries a curated message that explains what the collection is for and how to populate it. The `empty_state` tag defaults to no icon / no illustration (`icon=None`) - opt in to a Bootstrap icon or a line-art illustration when the page benefits from it. The new `.empty-state--plain` modifier gives the iconless variant proper 3 rem padding so it doesn't look truncated
- **Filter chip dark mode contrast bug fix**: `.filter-chip.active` used `background: var(--text-primary); color: #fff` which in dark mode mapped to off-white (`#E4E4E7`) on white text - invisible. Now uses `var(--accent)` background + white text in both themes (AAA contrast). Hover border on inactive chips switched from hardcoded `rgba(22,19,18,.18)` to `color-mix(in srgb, var(--text-primary) 18%, transparent)`. Active chips gain a hover state that switches to `var(--accent-hover)`. The `.filter-chip.active-warning` text colour is forced to `#fff` so it stays legible on yellow in dark mode
- **French translations completed**: every untranslated entry in `locale/fr/LC_MESSAGES/django.po` is now filled, including the multi-line `msgid` blocks for empty-state helper messages, EBIOS RM descriptions, ANSSI / ISO terminology, indicator help texts and management-review review-period helpers. All 213 `#, fuzzy` flags (auto-suggested fuzzy translations from gettext's similarity matcher, most of them wrong) are reviewed and either corrected or removed. `compilemessages` runs without warnings; the file is internally consistent (no duplicate `msgid` without `msgctxt`)

## [0.23.0] - 2026-05-29

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

[Unreleased]: https://github.com/frousselet/cairn/compare/v0.27.1...HEAD
[0.27.1]: https://github.com/frousselet/cairn/compare/v0.27.0...v0.27.1
[0.27.0]: https://github.com/frousselet/cairn/compare/v0.26.3...v0.27.0
[0.26.3]: https://github.com/frousselet/cairn/compare/v0.26.2...v0.26.3
[0.26.2]: https://github.com/frousselet/cairn/compare/v0.26.1...v0.26.2
[0.26.1]: https://github.com/frousselet/cairn/compare/v0.26.0...v0.26.1
[0.26.0]: https://github.com/frousselet/cairn/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/frousselet/cairn/compare/v0.24.5...v0.25.0
[0.24.5]: https://github.com/frousselet/cairn/compare/v0.24.4...v0.24.5
[0.24.4]: https://github.com/frousselet/cairn/compare/v0.24.3...v0.24.4
[0.24.3]: https://github.com/frousselet/cairn/compare/v0.24.2...v0.24.3
[0.24.2]: https://github.com/frousselet/cairn/compare/v0.24.1...v0.24.2
[0.24.1]: https://github.com/frousselet/cairn/compare/v0.24.0...v0.24.1
[0.24.0]: https://github.com/frousselet/cairn/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/frousselet/cairn/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/frousselet/cairn/compare/v0.21.4...v0.22.0
[0.21.4]: https://github.com/frousselet/cairn/compare/v0.21.3...v0.21.4
[0.21.3]: https://github.com/frousselet/cairn/compare/v0.21.2...v0.21.3
[0.21.2]: https://github.com/frousselet/cairn/compare/v0.21.1...v0.21.2
[0.21.1]: https://github.com/frousselet/cairn/compare/v0.21.0...v0.21.1
[0.21.0]: https://github.com/frousselet/cairn/compare/v0.20.0...v0.21.0
[0.20.0]: https://github.com/frousselet/cairn/compare/v0.19.1...v0.20.0
[0.19.1]: https://github.com/frousselet/cairn/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/frousselet/cairn/compare/v0.18.3...v0.19.0
[0.18.3]: https://github.com/frousselet/cairn/compare/v0.18.2...v0.18.3
[0.18.2]: https://github.com/frousselet/cairn/compare/v0.18.1...v0.18.2
[0.18.1]: https://github.com/frousselet/cairn/compare/v0.18.0...v0.18.1
[0.18.0]: https://github.com/frousselet/cairn/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/frousselet/cairn/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/frousselet/cairn/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/frousselet/cairn/compare/v0.14.2...v0.15.0
[0.14.0 - 0.14.2]: https://github.com/frousselet/cairn/compare/v0.13.0...v0.14.2
[0.13.0]: https://github.com/frousselet/cairn/compare/v0.12.1...v0.13.0
[0.12.0 - 0.12.1]: https://github.com/frousselet/cairn/compare/v0.11.2...v0.12.1
[0.11.0 - 0.11.2]: https://github.com/frousselet/cairn/compare/v0.10.2...v0.11.2
[0.10.0 - 0.10.2]: https://github.com/frousselet/cairn/compare/v0.9.1...v0.10.2
[0.9.0 - 0.9.1]: https://github.com/frousselet/cairn/compare/v0.8.0...v0.9.1
[0.8.0]: https://github.com/frousselet/cairn/compare/v0.7.5...v0.8.0
[0.7.0 - 0.7.5]: https://github.com/frousselet/cairn/compare/v0.6.0...v0.7.5
[0.6.0]: https://github.com/frousselet/cairn/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/frousselet/cairn/compare/v0.4.8...v0.5.0
[0.4.5 - 0.4.8]: https://github.com/frousselet/cairn/compare/v0.4.4...v0.4.8
[0.4.2 - 0.4.4]: https://github.com/frousselet/cairn/compare/v0.4.1...v0.4.4
[0.4.0 - 0.4.1]: https://github.com/frousselet/cairn/compare/v0.3.1...v0.4.1
[0.3.0 - 0.3.1]: https://github.com/frousselet/cairn/compare/v0.2.16...v0.3.1
[0.2.12 - 0.2.16]: https://github.com/frousselet/cairn/compare/v0.2.11...v0.2.16
[0.2.7 - 0.2.11]: https://github.com/frousselet/cairn/compare/v0.2.6...v0.2.11
[0.2.1 - 0.2.6]: https://github.com/frousselet/cairn/compare/v0.2.0...v0.2.6
[0.2.0]: https://github.com/frousselet/cairn/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/frousselet/cairn/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/frousselet/cairn/compare/v0.0.5...v0.1.0
[0.0.5]: https://github.com/frousselet/cairn/compare/v0.0.4...v0.0.5
[0.0.2 - 0.0.4]: https://github.com/frousselet/cairn/compare/v0.0.1...v0.0.4
[0.0.1]: https://github.com/frousselet/cairn/releases/tag/v0.0.1
