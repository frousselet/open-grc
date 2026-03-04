# Open GRC — MCP Server Reference

> **Protocol**: Model Context Protocol (MCP) v2025-03-26
> **Transport**: Streamable HTTP (JSON-RPC 2.0)
> **Endpoint**: `POST /api/v1/mcp`
> **Authentication**: OAuth 2.0 (PKCE or client_credentials)

This document provides a comprehensive reference for the Open GRC MCP server,
optimized for LLM clients. It covers all available tools, their parameters,
allowed values, and the data model relationships.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Protocol Usage](#protocol-usage)
4. [Data Model Overview](#data-model-overview)
5. [Module: Context (Governance)](#module-context-governance)
6. [Module: Assets](#module-assets)
7. [Module: Compliance](#module-compliance)
8. [Module: Risks](#module-risks)
9. [Module: Accounts (System)](#module-accounts-system)
10. [Module: Helpers](#module-helpers)
11. [Common Patterns](#common-patterns)
12. [Enum Reference](#enum-reference)

---

## Overview

Open GRC is a Governance, Risk & Compliance (GRC) platform implementing
ISO 27001, ISO 27005, and EBIOS RM methodologies. The MCP server exposes
all GRC data as tools that can be called via JSON-RPC 2.0.

### Tool Naming Convention

Tools follow the pattern: `{verb}_{entity_name}[s]`

- **`list_{entity}s`** — List entities with search, filters, pagination
- **`get_{entity}`** — Get a single entity by UUID
- **`create_{entity}`** — Create a new entity
- **`update_{entity}`** — Update an existing entity
- **`delete_{entity}`** — Delete an entity
- **`approve_{entity}`** — Approve an entity (sets `is_approved=true`)

### Total Tools: ~130+

---

## Authentication

All MCP requests require a valid OAuth 2.0 access token.

**Supported flows:**
- Authorization Code + PKCE (interactive)
- Client Credentials (machine-to-machine)

The token must be sent as a Bearer token in the Authorization header.

---

## Protocol Usage

### Initialize Session

```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {},
  "id": 1
}
```

### List Available Tools

```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 2
}
```

### Call a Tool

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_scopes",
    "arguments": {"status": "active", "limit": 10}
  },
  "id": 3
}
```

### Pagination

All list tools support:
- `limit` (integer, default 25, max 100)
- `offset` (integer, default 0)
- `search` (string, full-text search)

Response format:
```json
{
  "total": 42,
  "items": [...],
  "limit": 25,
  "offset": 0
}
```

---

## Data Model Overview

### Base Model Hierarchy

All entities inherit from one of these base classes:

| Base Class | Fields | Scope-Filtered |
|------------|--------|----------------|
| **BaseModel** | `id` (UUID), `reference` (auto-generated, e.g. SCOP-1), `created_at`, `updated_at`, `created_by`, `is_approved`, `approved_by`, `approved_at`, `version`, `tags` (M2M) | No |
| **ScopedModel** (extends BaseModel) | All of BaseModel + `scopes` (M2M to Scope) | Yes |

Entities based on **ScopedModel** are automatically filtered based on the
user's allowed scopes. Only objects whose scopes overlap with the user's
assigned scopes are visible.

### Reference Format

Every entity with a `REFERENCE_PREFIX` gets an auto-generated reference:
`PREFIX-N` (e.g. `SCOP-1`, `RISK-42`, `FWRK-5`).

### Approval Workflow

Entities inheriting from BaseModel/ScopedModel support a two-step approval:
1. Create/Update → `is_approved=false`
2. Call `approve_{entity}` → `is_approved=true`, records approver and timestamp
3. Any update resets `is_approved=false` and increments `version`

---

## Module: Context (Governance)

### Scope

> **Defines the boundaries of the ISMS (Information Security Management System)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Scope name |
| `description` | string | Yes | What the scope covers |
| `status` | string | No | `draft` · `active` · `archived` |
| `boundaries` | string | No | Explicit boundaries and exclusions |
| `justification_exclusions` | string | No | Justification for exclusions |
| `geographic_scope` | string | No | Geographic coverage |
| `organizational_scope` | string | No | Organizational units included |
| `technical_scope` | string | No | Technical systems included |
| `effective_date` | date | No | When scope becomes effective |
| `review_date` | date | No | Next review date |
| `parent_scope_id` | UUID | No | Parent scope for hierarchy |
| `icon` | string | No | Bootstrap Icons class (e.g. `bi-building`) |

**Filters:** `status`
**Permission:** `context.scope.*`
**Scope-filtered:** Yes (via Scope identity)
**Has approve:** Yes

### Issue

> **Internal or external context issue (ISO 27001 clause 4.1)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Issue title |
| `description` | string | No | Detailed description |
| `type` | string | Yes | `internal` · `external` |
| `category` | string | Yes | See enum below |
| `impact_level` | string | Yes | `low` · `medium` · `high` · `critical` |
| `trend` | string | No | `improving` · `stable` · `degrading` |
| `source` | string | No | Source of the issue |
| `status` | string | No | `identified` · `active` · `monitored` · `closed` |
| `review_date` | date | No | Next review date |

**Category values by type:**
- **Internal:** `strategic`, `organizational`, `human_resources`, `technical`, `financial`, `cultural`
- **External:** `political`, `economic`, `social`, `technological`, `legal`, `environmental`, `competitive`, `regulatory`

**Validation:** Category must match the type (internal categories for internal issues, external categories for external issues).

### Stakeholder

> **Interested party (ISO 27001 clause 4.2)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Stakeholder name |
| `type` | string | Yes | `internal` · `external` |
| `category` | string | Yes | `executive_management` · `employees` · `customers` · `suppliers` · `partners` · `regulators` · `shareholders` · `insurers` · `public` · `competitors` · `unions` · `auditors` · `other` |
| `influence_level` | string | Yes | `low` · `medium` · `high` |
| `interest_level` | string | Yes | `low` · `medium` · `high` |
| `contact_name` | string | No | Primary contact |
| `contact_email` | email | No | Contact email |
| `contact_phone` | string | No | Contact phone |
| `status` | string | No | `active` · `inactive` |

### Stakeholder Expectation

> **Child of Stakeholder — no approval workflow**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stakeholder_id` | UUID | Yes | Parent stakeholder |
| `description` | string | Yes | What is expected |
| `type` | string | Yes | `requirement` · `expectation` · `need` |
| `priority` | string | Yes | `low` · `medium` · `high` · `critical` |
| `is_applicable` | boolean | No | Default true |

### Objective

> **Security or business objective (ISO 27001 clause 6.2)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Objective title |
| `category` | string | Yes | `confidentiality` · `integrity` · `availability` · `compliance` · `operational` · `strategic` |
| `type` | string | Yes | `security` · `compliance` · `business` · `other` |
| `owner_id` | UUID | Yes | User who owns this |
| `status` | string | No | `draft` · `active` · `achieved` · `not_achieved` · `cancelled` |
| `progress_percentage` | integer | No | 0-100. Must be 100 if status=achieved |
| `measurement_frequency` | string | No | `daily` · `weekly` · `monthly` · `quarterly` · `semi_annual` · `annual` |
| `target_date` | date | No | Target date |

### SWOT Analysis / SWOT Item

**SwotAnalysis** status: `draft` · `validated` · `archived`

**SwotItem** fields:
- `swot_analysis_id` (UUID, required)
- `quadrant`: `strength` · `weakness` · `opportunity` · `threat`
- `description` (required)
- `impact_level`: `low` · `medium` · `high`
- `order` (integer)

### Role / Responsibility

**Role** type: `governance` · `operational` · `support` · `control`
**Role** status: `active` · `inactive`

**Responsibility** (child of Role):
- `raci_type`: `responsible` · `accountable` · `consulted` · `informed`

### Activity

Type: `core_business` · `support` · `management`
Criticality: `low` · `medium` · `high` · `critical`
Status: `active` · `inactive` · `planned`

### Site

Type: `siege` · `bureau` · `usine` · `entrepot` · `datacenter` · `site_distant` · `autre`
Status: `draft` · `active` · `archived`

### Indicator

| Field | Type | Description |
|-------|------|-------------|
| `indicator_type` | string | `organizational` · `technical` |
| `collection_method` | string | `manual` · `api` · `internal` |
| `format` | string | `number` · `boolean` |
| `critical_threshold_operator` | string | For numbers: `below` · `above`. For booleans: `is_false` · `is_true` |
| `review_frequency` | string | `daily` · `weekly` · `monthly` · `quarterly` · `semi_annual` · `annual` |
| `status` | string | `active` · `inactive` · `draft` |
| `internal_source` | string | `global_compliance_rate` · `framework_compliance_rate` · `objective_progress` · `risk_treatment_rate` · `approved_scopes_rate` · `mandatory_roles_coverage` |

### Tag

Simple entity: `name` (string, unique), `color` (hex string).
Tools: `list_tags`, `create_tag`, `delete_tag`.

---

## Module: Assets

### Essential Asset

> **Business process or information asset with DIC (Confidentiality, Integrity, Availability) valuation**

| Field | Type | Values |
|-------|------|--------|
| `type` | string | `business_process` · `information` |
| `category` | string | Depends on type. Process: `core_process`, `support_process`, `management_process`. Information: `strategic_data`, `operational_data`, `personal_data`, `financial_data`, `technical_data`, `legal_data`, `research_data`, `commercial_data` |
| `confidentiality_level` | integer | 0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical |
| `integrity_level` | integer | 0-4 (same scale) |
| `availability_level` | integer | 0-4 (same scale) |
| `data_classification` | string | `public` · `internal` · `confidential` · `restricted` · `secret` |
| `status` | string | `identified` · `active` · `under_review` · `decommissioned` |

### Support Asset

| Field | Type | Values |
|-------|------|--------|
| `type` | string | `hardware` · `software` · `network` · `person` · `site` · `service` · `paper` |
| `category` | string | Must match type. 40+ values (see tools schema) |
| `exposure_level` | string | `internal` · `exposed` · `internet_facing` · `dmz` |
| `environment` | string | `production` · `staging` · `development` · `test` · `disaster_recovery` |
| `status` | string | `in_stock` · `deployed` · `active` · `under_maintenance` · `decommissioned` · `disposed` |

**Category mapping (type → valid categories):**
- **hardware:** server, workstation, laptop, mobile_device, network_equipment, storage, peripheral, iot_device, removable_media, other_hardware
- **software:** operating_system, database, application, middleware, security_tool, development_tool, saas_application, other_software
- **network:** lan, wan, wifi, vpn, internet_link, firewall_zone, dmz, other_network
- **person:** internal_staff, contractor, external_provider, administrator, developer, other_person
- **site:** datacenter, office, remote_site, cloud_region, other_site
- **service:** cloud_service, hosting_service, managed_service, telecom_service, outsourced_service, other_service
- **paper:** archive, printed_document, form, other_paper

### Asset Dependency

Links an essential asset to a support asset.
- `dependency_type`: `runs_on` · `stored_in` · `transmitted_by` · `managed_by` · `hosted_at` · `protected_by` · `other`
- `criticality`: `low` · `medium` · `high` · `critical`
- `redundancy_level`: `none` · `partial` · `full`

### Supplier

- `criticality`: `low` · `medium` · `high` · `critical`
- `status`: `active` · `under_evaluation` · `suspended` · `archived`
- `type_id`: FK to SupplierType (integer)

### Supplier Dependency

Links a support asset to a supplier.
- `dependency_type`: `hosted_by` · `provided_by` · `maintained_by` · `developed_by` · `operated_by` · `monitored_by` · `other`

### Site Dependencies

**Site-Asset:** `dependency_type`: `located_at` · `hosted_at` · `deployed_at` · `other`
**Site-Supplier:** `dependency_type`: `maintained_by` · `managed_by` · `powered_by` · `secured_by` · `other`

### Asset Valuation

Historical DIC evaluation for an essential asset. Levels are integers 0-4.

### Supplier Type / Supplier Type Requirement / Supplier Requirement / Supplier Requirement Review

Configuration and compliance tracking for supplier management.
- **Supplier Requirement** `compliance_status`: `not_assessed` · `compliant` · `partially_compliant` · `non_compliant`

---

## Module: Compliance

### Framework

| Field | Type | Values |
|-------|------|--------|
| `type` | string | `standard` · `law` · `regulation` · `contract` · `internal_policy` · `industry_framework` · `other` |
| `category` | string | `information_security` · `privacy` · `risk_management` · `business_continuity` · `cloud_security` · `sector_specific` · `it_governance` · `quality` · `contractual` · `internal` · `other` |
| `status` | string | `draft` · `active` · `under_review` · `deprecated` · `archived` |

**Special tool:** `get_framework_compliance_summary` — Returns overall compliance %, section breakdown, and status distribution.

### Requirement

| Field | Type | Values |
|-------|------|--------|
| `type` | string | `mandatory` · `recommended` · `optional` |
| `category` | string | `organizational` · `technical` · `physical` · `legal` · `human` · `other` |
| `compliance_status` | string | `not_assessed` · `non_compliant` · `partially_compliant` · `compliant` · `not_applicable` |
| `status` | string | `active` · `deprecated` · `superseded` |
| `priority` | string | `low` · `medium` · `high` · `critical` |

### Compliance Assessment

Status: `draft` · `in_progress` · `completed` · `validated` · `archived`

### Assessment Result

Per-requirement result within an assessment.
`compliance_status`: same as Requirement.

### Requirement Mapping

Cross-framework mapping between requirements.
- `mapping_type`: `equivalent` · `partial_overlap` · `includes` · `included_by` · `related`
- `coverage_level`: `full` · `partial` · `minimal`

### Action Plan

- `priority`: `low` · `medium` · `high` · `critical`
- `status`: `planned` · `in_progress` · `completed` · `cancelled` · `overdue`

---

## Module: Risks

### Risk Assessment

- `methodology`: `iso27005` · `ebios_rm`
- `status`: `draft` · `in_progress` · `completed` · `validated` · `archived`

### Risk Criteria

Configures the risk matrix (likelihood × impact → risk level).
- `status`: `draft` · `active` · `archived`
- Contains **Scale Levels** (likelihood/impact) and **Risk Levels**

### Risk

| Field | Type | Description |
|-------|------|-------------|
| `risk_source` | string | `iso27005_analysis` · `ebios_strategic` · `ebios_operational` · `incident` · `audit` · `compliance` · `manual` |
| `status` | string | `identified` · `analyzed` · `evaluated` · `treatment_planned` · `treatment_in_progress` · `treated` · `accepted` · `closed` · `monitoring` |
| `priority` | string | `low` · `medium` · `high` · `critical` |
| `treatment_decision` | string | `accept` · `mitigate` · `transfer` · `avoid` · `not_decided` |
| `initial/current/residual_likelihood` | integer | Scale level (1-5 typically) |
| `initial/current/residual_impact` | integer | Scale level (1-5 typically) |
| `initial/current/residual_risk_level` | integer | Auto-calculated from risk matrix |

### Risk Treatment Plan

- `treatment_type`: `mitigate` · `transfer` · `avoid`
- `status`: `planned` · `in_progress` · `completed` · `cancelled` · `overdue`

### Treatment Action

Child of treatment plan.
- `status`: `planned` · `in_progress` · `completed` · `cancelled`

### Risk Acceptance

- `status`: `active` · `expired` · `revoked` · `renewed`

### Threat

| Field | Type | Values |
|-------|------|--------|
| `type` | string | `deliberate` · `accidental` · `environmental` · `other` |
| `origin` | string | `human_internal` · `human_external` · `natural` · `technical` · `other` |
| `category` | string | `malware` · `social_engineering` · `unauthorized_access` · `denial_of_service` · `data_breach` · `physical_attack` · `espionage` · `fraud` · `sabotage` · `human_error` · `system_failure` · `network_failure` · `power_failure` · `natural_disaster` · `fire` · `water_damage` · `theft` · `vandalism` · `supply_chain` · `insider_threat` · `ransomware` · `apt` |
| `status` | string | `active` · `inactive` |

### Vulnerability

| Field | Type | Values |
|-------|------|--------|
| `category` | string | `configuration_weakness` · `missing_patch` · `design_flaw` · `coding_error` · `weak_authentication` · `insufficient_logging` · `lack_of_encryption` · `physical_vulnerability` · `organizational_weakness` · `human_factor` · `obsolescence` · `insufficient_backup` · `network_exposure` · `third_party_dependency` |
| `severity` | string | `low` · `medium` · `high` · `critical` |
| `status` | string | `identified` · `confirmed` · `mitigated` · `accepted` · `closed` |

### ISO 27005 Risk

Threat × vulnerability analysis scenario with:
- `threat_likelihood`, `vulnerability_exposure` → `combined_likelihood`
- `impact_confidentiality`, `impact_integrity`, `impact_availability` → `max_impact`
- `risk_level` (auto-calculated from risk matrix)

---

## Module: Accounts (System)

### Tools

| Tool | Description |
|------|-------------|
| `list_users` | List users (filter: `is_active`) |
| `get_user` | Get user details |
| `get_me` | Get current authenticated user |
| `list_groups` | List permission groups |
| `get_group` | Get group with permissions and user count |
| `list_permissions` | List all permissions (filter: `module`, `feature`) |
| `list_access_logs` | List auth events (filter: `event_type`, `user_id`) |

### Access Log Event Types

`login_success` · `login_failed` · `logout` · `token_refresh` · `password_change` · `account_locked` · `account_unlocked` · `passkey_login_success` · `passkey_login_failed` · `passkey_registered` · `passkey_deleted`

### Permission Format

`module.feature.action` (e.g. `context.scope.read`, `risks.risk.approve`)

**Modules:** context, assets, compliance, risks, system
**Actions:** create, read, update, delete, approve, access, assess, validate

---

## Module: Helpers

### Help Content

Contextual help entries keyed by page/feature and language.

| Tool | Description |
|------|-------------|
| `list_help_contents` | List all help entries (filter: `language`) |
| `get_help_content` | Get by ID |
| `get_help_by_key` | Get by key + language (e.g. `key="context.scope_list"`, `language="fr"`) |
| `create_help_content` | Create new entry |
| `update_help_content` | Update existing entry |
| `delete_help_content` | Delete entry |

---

## Common Patterns

### Creating an Entity

1. Call `create_{entity}` with required fields
2. A unique `reference` is auto-generated (e.g. `SCOP-1`)
3. `created_by` is set to the current user
4. `is_approved` is `false` by default
5. Call `approve_{entity}` when ready

### Filtering Lists

All list tools accept:
- `search` — full-text search across name, description, reference
- `limit` / `offset` — pagination
- Entity-specific filters (status, type, etc.) — exact match

### Foreign Key Fields

FK fields are passed and returned as UUIDs (strings).
- Writable: `owner_id`, `parent_scope_id`, `framework_id`, etc.
- Returned: same UUID string format

### Date Fields

All dates use `YYYY-MM-DD` format. DateTime uses ISO 8601.

---

## Enum Reference

### Universal Enums

| Enum | Values |
|------|--------|
| Priority (context/compliance) | `low` · `medium` · `high` · `critical` |
| Criticality (assets) | `low` · `medium` · `high` · `critical` |

### DIC Levels (Integer)

| Value | Label |
|-------|-------|
| 0 | Negligible |
| 1 | Low |
| 2 | Medium |
| 3 | High |
| 4 | Critical |

### All Status Enums

| Entity | Status Values |
|--------|---------------|
| Scope, Site | `draft` · `active` · `archived` |
| Issue | `identified` · `active` · `monitored` · `closed` |
| Stakeholder, Role | `active` · `inactive` |
| Objective | `draft` · `active` · `achieved` · `not_achieved` · `cancelled` |
| SWOT Analysis | `draft` · `validated` · `archived` |
| Activity | `active` · `inactive` · `planned` |
| Indicator | `active` · `inactive` · `draft` |
| Essential Asset | `identified` · `active` · `under_review` · `decommissioned` |
| Support Asset | `in_stock` · `deployed` · `active` · `under_maintenance` · `decommissioned` · `disposed` |
| Asset Group | `active` · `inactive` |
| Supplier | `active` · `under_evaluation` · `suspended` · `archived` |
| Framework | `draft` · `active` · `under_review` · `deprecated` · `archived` |
| Requirement | `active` · `deprecated` · `superseded` |
| Assessment (compliance & risk) | `draft` · `in_progress` · `completed` · `validated` · `archived` |
| Risk Criteria | `draft` · `active` · `archived` |
| Risk | `identified` · `analyzed` · `evaluated` · `treatment_planned` · `treatment_in_progress` · `treated` · `accepted` · `closed` · `monitoring` |
| Treatment Plan, Action Plan | `planned` · `in_progress` · `completed` · `cancelled` · `overdue` |
| Treatment Action | `planned` · `in_progress` · `completed` · `cancelled` |
| Risk Acceptance | `active` · `expired` · `revoked` · `renewed` |
| Threat | `active` · `inactive` |
| Vulnerability | `identified` · `confirmed` · `mitigated` · `accepted` · `closed` |
| Compliance Status | `not_assessed` · `non_compliant` · `partially_compliant` · `compliant` · `not_applicable` |
| Supplier Requirement | `not_assessed` · `compliant` · `partially_compliant` · `non_compliant` |
