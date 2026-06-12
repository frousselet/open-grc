# MCP Server (Model Context Protocol)

Cairn ships with a built-in JSON-RPC 2.0 MCP server exposing 55 tools across all modules, so AI assistants and external clients can read and manage GRC data directly. Authentication uses OAuth 2.0. All tools enforce RBAC permissions and scope-based tenancy.

## Endpoints

| Endpoint | Purpose |
| -------- | ------- |
| `POST /api/v1/mcp` | JSON-RPC 2.0 MCP endpoint |
| `GET /api/v1/mcp/.well-known/oauth-protected-resource` | OAuth resource metadata (RFC 9728) for client discovery |
| `POST /api/v1/oauth/register/` | Dynamic client registration |
| `POST /api/v1/oauth/token/` | Token endpoint (authorization code + refresh token grants) |

## CRUD pattern

Most domain entities expose a standard set of operations generated automatically:

| Operation | Tool name pattern | Description |
| --------- | ----------------- | ----------- |
| List | `list_{entity}s` | Paginated list with search, filters, limit/offset |
| Get | `get_{entity}` | Get a single object by UUID |
| Create | `create_{entity}` | Create a new object |
| Batch Create | `batch_create_{entity}s` | Create up to 500 objects with partial success (non-atomic) |
| Update | `update_{entity}` | Update an existing object |
| Delete | `delete_{entity}` | Delete an object (only allowed from a deletable lifecycle state) |
| Transition | `transition_{entity}` | Change the object's lifecycle state (draft / pending / validated / archived), validating permissions, mandatory comments and side effects |
| Allowed transitions | `{entity}_allowed_transitions` | List the lifecycle transitions the caller may perform from the current state |
| Approve | `approve_{entity}` | Deprecated alias of `transition_{entity}` with `target_state="validated"` |

## Context module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `scope` | Yes | type, status |
| `issue` | Yes | type, category |
| `stakeholder` | Yes | type, influence_level |
| `objective` | Yes | type, status |
| `role` | Yes | - |
| `activity` | Yes | type, criticality |
| `site` | Yes | type, status |
| `indicator` | Yes | indicator_type, status, format, collection_method |
| `indicator_measurement` | No | indicator_id |
| `responsibility` | No | role_id, raci_type |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `list_tags` | List all tags |
| `create_tag` | Create a tag |
| `delete_tag` | Delete a tag |

## Assets module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `essential_asset` | Yes | type, category, status |
| `support_asset` | Yes | type, category, status |
| `asset_dependency` | Yes | essential_asset_id, support_asset_id, dependency_type, criticality |
| `site_asset_dependency` | Yes | support_asset_id, site_id, dependency_type, criticality |
| `site_supplier_dependency` | Yes | site_id, supplier_id, dependency_type, criticality |
| `asset_group` | Yes | type, status |
| `supplier` | Yes | type, criticality, status |
| `supplier_dependency` | Yes | support_asset_id, supplier_id |
| `asset_valuation` | No | essential_asset_id |
| `supplier_type` | No | - |
| `supplier_type_requirement` | No | supplier_type_id |
| `supplier_requirement` | No | supplier_id, compliance_status |
| `supplier_requirement_review` | No | supplier_requirement_id, result |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `update_supplier_logo` | Upload a logo via base64 data URI or public URL with automatic variant generation (128/64/32/16px) |

## Compliance module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `framework` | Yes | type, category, status |
| `section` | No | framework_id, parent_section_id |
| `requirement` | Yes | framework_id, section_id, compliance_status, type, priority |
| `compliance_assessment` | Yes | status |
| `assessment_result` | No | assessment_id, requirement_id, compliance_status |
| `requirement_mapping` | No | source_requirement_id, target_requirement_id, mapping_type |
| `action_plan` | Yes | status, priority |
| `finding` | No | assessment_id, finding_type |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `get_framework_compliance_summary` | Compliance summary with section-level scores and status distribution |
| `action_plan_transition` | Transition an action plan through the Kanban workflow (forward, refusal, cancellation) |
| `action_plan_transitions` | List transition history for an action plan |
| `action_plan_kanban` | Get action plans grouped by status for Kanban board with workflow rules |
| `action_plan_allowed_transitions` | Get allowed transitions for an action plan with permission checks |
| `list_action_plan_comments` | List threaded comments on an action plan |
| `create_action_plan_comment` | Create a comment or reply on an action plan |

## Risks module

| CRUD entity | Approve | Filters |
| ----------- | ------- | ------- |
| `risk_assessment` | Yes | status |
| `risk_criteria` | No | status |
| `scale_level` | No | criteria_id, scale_type |
| `risk_level` | No | criteria_id, requires_treatment |
| `risk` | Yes | status, priority, assessment_id |
| `risk_treatment_plan` | Yes | status, risk_id |
| `treatment_action` | No | treatment_plan_id, status |
| `risk_acceptance` | No | risk_id, status |
| `threat` | Yes | type, status |
| `vulnerability` | Yes | category, severity, status |
| `iso27005_risk` | No | assessment_id, threat_id, vulnerability_id |

Additional tools:

| Tool | Description |
| ---- | ----------- |
| `list_risk_requirements` | List compliance requirements linked to a risk |
| `list_requirement_risks` | List risks linked to a compliance requirement |
| `link_risk_requirements` | Link requirements to a risk (additive) |
| `unlink_risk_requirements` | Remove requirement links from a risk |
| `set_risk_requirements` | Replace all linked requirements on a risk |

## Accounts module

| Tool | Description |
| ---- | ----------- |
| `list_users` | List users with search and active status filter |
| `get_user` | Get detailed user information |
| `get_me` | Get the currently authenticated user |
| `update_me` | Update the current user's profile (first_name, last_name, phone, language, timezone, theme_preference) |
| `list_notifications` | List the current user's in-app notifications with the unread count |
| `mark_notification_read` | Mark one of the current user's notifications as read |
| `mark_all_notifications_read` | Mark all of the current user's notifications as read |
| `list_groups` | List all groups |
| `get_group` | Get group details including permissions |
| `list_permissions` | List all available permissions with module filter |
| `list_access_logs` | List authentication events (login, logout, lockout) |

## Reports & Settings

| Tool | Description |
| ---- | ----------- |
| `list_reports` | List generated reports with optional type filter |
| `generate_soa_report` | Generate a Statement of Applicability (SoA) PDF for selected frameworks |
| `generate_audit_report` | Generate an audit report PDF for a completed assessment |
| `generate_risk_register` | Generate an Excel (.xlsx) export of the risk register with optional scope/assessment/status/priority filters |
| `generate_iso27005_report` | Generate an ISO 27005 risk assessment DOCX report for one assessment (context, criteria, threats, vulnerabilities, analyses, risks, plans, acceptances) |
| `generate_management_review_pptx` | Generate a management review PowerPoint presentation (ISO 27001 clause 9.3) |
| `generate_management_review_docx` | Generate a management review Word meeting minutes (ISO 27001 clause 9.3) |
| `list_management_reviews` | List persistent management reviews (ISO 27001:2022 clause 9.3) with status and scope filters |
| `get_management_review` | Get a management review with decision/change counts and snapshot state |
| `create_management_review` | Create a persistent management review |
| `transition_management_review` | Transition a management review through its life cycle (auto-snapshot on closure) |
| `export_management_review` | Export a management review as DOCX or PPTX (base64) |
| `list_management_review_decisions` | List decisions recorded during management reviews (clause 9.3.3 outputs) |
| `create_management_review_decision` | Record a decision from a management review |
| `promote_decision_to_action_plan` | Create a ComplianceActionPlan from a decision and link them |
| `list_isms_changes` | List ISMS changes decided during management reviews |
| `create_isms_change` | Record an ISMS change decided during a management review |
| `set_participant_signature` | Attach a base64 graphical signature (non-eIDAS) to a management review participant for DOCX embedding |
| `list_stakeholder_feedback` | List formal stakeholder feedback (clause 9.3.2.e) |
| `create_stakeholder_feedback` | Record formal feedback from an interested party |
| `delete_report` | Delete a generated report |
| `get_company_settings` | Get company settings (name, address) |
| `update_company_settings` | Update company settings |
