# Features

Detailed feature reference for Cairn. For module-level specifications (business rules, model fields, lifecycle), see [docs/modules/](modules/README.md).

## Governance (Context & Organisation)

| Feature | Description |
| ------- | ----------- |
| Scopes | Hierarchical organisational perimeters with versioning, approval workflow and assignable managers |
| Sites | Physical and logical locations (offices, datacenters, cloud regions) with hierarchy |
| Issues | Internal/external strategic issues (PESTLE categories) with impact and trend tracking |
| Stakeholders | Interested parties with expectations, influence/interest levels and RACI support |
| Objectives | Security and business objectives with KPI tracking (target/current values, progress %) |
| SWOT Analysis | Structured strengths/weaknesses/opportunities/threats with impact levels |
| Roles & Responsibilities | RACI matrix, mandatory role enforcement, responsibility assignments |
| Activities | Hierarchical business processes (core, support, management) with criticality levels |
| Tags | Reusable tags assignable to any domain object for cross-cutting classification |

## Asset Management

| Feature | Description |
| ------- | ----------- |
| Essential Assets | Business processes and information assets with DIC valuation (Confidentiality, Integrity, Availability on a 5-level scale) |
| Support Assets | IT infrastructure (hardware, software, network, services, sites, people) with lifecycle tracking (EOL, warranty) |
| Dependencies | Essential-to-support asset mapping with criticality, SPOF detection and redundancy tracking |
| Site Dependencies | Site-to-asset and site-to-supplier dependency tracking |
| Asset Groups | Logical grouping of support assets |
| DIC Inheritance | Support assets automatically inherit max DIC levels from linked essential assets |
| Valuations | Historical DIC evaluation tracking per essential asset |
| Suppliers | Supplier registry with types, contractual requirements, evidence reviews and dependency mapping |

## Risk Management

| Feature | Description |
| ------- | ----------- |
| Risk Assessments | ISO 27005 and EBIOS RM methodologies |
| Risk Criteria | Configurable likelihood/impact scales with dynamic risk matrix generation |
| Risks | Three-level tracking (initial, current, residual) with treatment decisions (accept, mitigate, transfer, avoid) and a frozen criteria snapshot so historical scores remain immutable when the matrix is edited |
| Threat Catalog | Reusable threats by type (deliberate, accidental, environmental) and origin, with approval workflow |
| Vulnerability Catalog | Reusable vulnerabilities with severity, CVE references, remediation guidance and approval workflow |
| ISO 27005 Analysis | Atomic threat x vulnerability risk scenarios with combined likelihood/impact calculation and approval workflow |
| EBIOS RM Foundation (ANSSI v1.5) | Workshop 0 study framework, workshop 1 security baseline with feared events (one per DIC criterion per essential asset) and baseline gaps linked to compliance requirements. Automatic bootstrap of the six workshop progress trackers on every ebios_rm assessment. Strategic vs operational iteration cycles. See [docs/modules/m4-risks/ebios-rm/](modules/m4-risks/ebios-rm/) |
| EBIOS RM Workshop 2 | ANSSI risk sources with motivation/resources/activity and auto-computed threat level V1..V4 via Grid A. Targeted objectives (lucrative, strategic, terrorist, ideological, revenge, ludic). SR/OV pairs with relevance scoring, priority score (max of threat level and relevance weight) and retention gate for workshop 3 |
| EBIOS RM Workshop 3 | Ecosystem stakeholder cartography (`(dependency × penetration) / (maturity × trust)` formula with control/monitoring/danger zoning). Strategic scenarios linking SR/OV pairs to feared events, with risk level computed via the assessment matrix and ordered attack path steps (initial access, lateral movement, exfiltration, ...). Custom REST endpoint for the ecosystem graph (nodes + edges + zones) |
| EBIOS RM Workshop 4 | Operational scenarios with ANSSI V1..V4 likelihood, gravity inherited from the parent strategic scenario, attack techniques mapped to a shared MITRE ATT&CK catalogue (seeded from a versioned fixture, refreshable via `python manage.py refresh_mitre_attack`). Custom REST endpoints for the MITRE heatmap and idempotent consolidation into the unified Risk register |
| EBIOS RM Workshop 5 | Auto-created summary per ebios_rm assessment with residual risk strategy, monitoring plan, PACS narrative, before/after cartography snapshots captured on demand. Structured PACS measures (governance, protection, defense, resilience, awareness) linked to treatment plans, baseline gaps and compliance requirements |
| Treatment Plans | Structured remediation with ordered actions, progress tracking, cost estimates and linkage to compliance action plans |
| Risk Acceptance | Formal acceptance records with expiry dates, conditions, review tracking and two-step approval workflow |
| Risk Matrices | Visual heatmaps (current vs residual) |

## Compliance

| Feature | Description |
| ------- | ----------- |
| Frameworks | Regulatory and standard frameworks (ISO 27001, GDPR, NIS2, etc.) with type, category and jurisdiction |
| Sections | Hierarchical framework structure |
| Requirements | Per-framework requirements with compliance status, evidence and gap tracking |
| Assessments | Compliance evaluations with per-requirement results and automatic compliance level calculation |
| Findings | Audit findings (major/minor non-conformities, observations, opportunities, strengths) linked to assessments |
| Action Plans | Gap remediation plans with priority, progress, cost tracking and threaded comments |
| Inter-Framework Mappings | Requirement-to-requirement mappings across frameworks (equivalent, partial, includes, related) |
| Framework Import | Excel-based bulk import of frameworks and requirements |

## Users & Access Control

| Feature | Description |
| ------- | ----------- |
| Custom User Model | Email-based authentication with UUID primary keys |
| Role-Based Access Control | Granular permissions (90+) using `module.feature.action` codenames |
| 6 System Groups | Super Admin, Admin, RSSI/DPO, Auditor, Contributor, Reader |
| Scope-Based Tenancy | Groups can be restricted to specific organisational scopes; scope managers automatically gain access |
| Account Security | Failed login lockout (5 attempts / 15 min), password complexity enforcement |
| Dual Authentication | Session-based (web UI) + JWT with token rotation (API) |
| Passkey Authentication | FIDO2 WebAuthn passwordless login with discoverable credentials |
| Access Logs | Full audit trail of authentication events (login, logout, lockout, password change) |

## Indicators (KPI Tracking)

| Feature | Description |
| ------- | ----------- |
| Custom Indicators | Manual KPI, metric and compliance metric tracking with number, boolean or percentage formats |
| Predefined Indicators | Auto-computed metrics (global compliance rate, risk treatment rate, objective progress, etc.) |
| Thresholds | Critical threshold detection with configurable operators and min/max bounds |
| Measurement History | Timestamped measurements with trend and delta tracking |
| Sparklines | Inline charts on the dashboard for numeric indicators |

## Platform Capabilities

| Feature | Description |
| ------- | ----------- |
| Real-Time Dashboard | WebSocket-powered live statistics via Django Channels with animated counters and auto-reconnect |
| Calendar & iCal | Unified calendar view across all modules with iCal subscription feed and per-user tokens |
| Global Search | Multi-category search across all domain objects |
| Reports | Configurable report generation (SoA PDF, Audit report PDF, Management review PPTX/DOCX) with status tracking |
| Management reviews | Persistent ISO 27001:2022 clause 9.3 workflow with life cycle, decisions, ISMS changes, participants, snapshot-based auditability, and retrochaining to action plans, treatment plans, and objectives |
| Stakeholder feedback | Formal feedback channel (clause 9.3.2.e) with sentiment, severity, and traceability to issues and expectations |
| Lifecycle Workflows | Unified lifecycle on every domain model (Draft / Pending validation / Validated / Archived by default, plus 15 entity-specific workflows), driving report inclusion, linking, deletion and notifications, with a generic stepper UI, per-transition permissions and mandatory comments on refusals / cancellations |
| Notifications | In-app + email notifications on lifecycle events (element submitted for validation), with a live bell badge (WebSocket), recipient fallback chain (scope managers, approvers, creator) and per-user email opt-out |
| Audit Trail | Full change history on every model via django-simple-history |
| Versioning | Automatic version increment on all domain objects |
| Company Settings | Centralised platform configuration (organisation name, logo, defaults) |
| Bilingual UI | Full French/English interface with contextual help banners |
| Excel Export | Export assets, risks, compliance data to Excel |
| Display Theme | Per-user Light / Dark / System preference (System follows the OS), persisted server-side and exposed through the API |
| Responsive UI | Collapsible sidebar, mobile-friendly layout |
| REST API | Full CRUD + filtering, search, pagination, batch creation and export on all resources - see [api.md](api.md) |
| HTMX Integration | Dynamic partial updates without full page reloads |
| MCP Server | JSON-RPC 2.0 server with 50+ tools and OAuth 2.0 authentication for external clients - see [mcp-server.md](mcp-server.md) |
