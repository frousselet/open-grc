"""
MCP tool definitions covering all Fairway API functionality.

Each tool maps to one or more API endpoints and performs operations
using the Django ORM directly, respecting the user's permissions.
"""

import json
from functools import wraps

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from mcp.server import InvalidParamsError


# ── Permission helpers ─────────────────────────────────────

def require_perm(codename):
    """Decorator that checks user permission before executing tool handler."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(user, arguments):
            if not user.is_superuser and not user.has_perm(codename):
                return _error(f"Permission denied: {codename}")
            return fn(user, arguments)
        return wrapper
    return decorator


def _error(message):
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
        "isError": True,
    }


def _serialize_obj(obj, fields=None):
    """Simple serialization of a model instance to dict."""
    if fields is None:
        fields = [f.name for f in obj._meta.fields]
    data = {}
    for field_name in fields:
        val = getattr(obj, field_name, None)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif hasattr(val, "pk"):
            val = str(val.pk)
        elif isinstance(val, (list, set)):
            val = list(val)
        else:
            val = str(val) if val is not None else None
        data[field_name] = val
    return data


def _serialize_qs(qs, fields=None, limit=50, offset=0):
    """Serialize a queryset to list of dicts."""
    qs = qs[offset:offset + limit]
    return [_serialize_obj(obj, fields) for obj in qs]


def _get_model(app_label, model_name):
    return apps.get_model(app_label, model_name)


def _filter_by_scopes(qs, user, model=None):
    """Apply scope-based filtering to a queryset."""
    if user.is_superuser:
        return qs
    scope_ids = user.get_allowed_scope_ids()
    if scope_ids is None:
        return qs
    model = model or qs.model
    Scope = _get_model("context", "Scope")
    if model is Scope or model._meta.label == "context.Scope":
        return qs.filter(id__in=scope_ids)
    if any(f.name == "scopes" for f in model._meta.many_to_many):
        return qs.filter(scopes__id__in=scope_ids).distinct()
    return qs


def _apply_filters(qs, arguments, allowed_filters):
    """Apply simple equality filters from arguments."""
    for key in allowed_filters:
        val = arguments.get(key)
        if val is not None:
            qs = qs.filter(**{key: val})
    return qs


def _apply_search(qs, arguments, search_fields):
    """Apply text search across multiple fields."""
    search = arguments.get("search")
    if search and search_fields:
        q = Q()
        for field in search_fields:
            q |= Q(**{f"{field}__icontains": search})
        qs = qs.filter(q)
    return qs


# ── Generic CRUD helpers ───────────────────────────────────

def _list_handler(model_class, fields, search_fields=None, filters=None, scope_filtered=True):
    """Create a generic list handler."""
    def handler(user, arguments):
        qs = model_class.objects.all()
        if scope_filtered:
            qs = _filter_by_scopes(qs, user)
        if search_fields:
            qs = _apply_search(qs, arguments, search_fields)
        if filters:
            qs = _apply_filters(qs, arguments, filters)
        limit = min(int(arguments.get("limit", 25)), 100)
        offset = int(arguments.get("offset", 0))
        total = qs.count()
        items = _serialize_qs(qs, fields, limit=limit, offset=offset)
        return {"total": total, "items": items, "limit": limit, "offset": offset}
    return handler


def _get_handler(model_class, fields, scope_filtered=True):
    """Create a generic get-by-id handler."""
    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")
        return _serialize_obj(obj, fields)
    return handler


def _coerce_field_value(model_class, field_name, value):
    """Coerce a value to the correct Python type for a Django model field.

    MCP arguments arrive as strings/JSON; this ensures integer fields get ints,
    boolean fields get bools, and JSON fields get parsed dicts/lists.
    """
    if value is None:
        return value
    # Resolve the Django field object — field_name may be 'foo_id' for FK 'foo'
    try:
        field = model_class._meta.get_field(field_name)
    except Exception:
        # For _id suffixed FK fields, try the base field name
        if field_name.endswith("_id"):
            try:
                field = model_class._meta.get_field(field_name[:-3])
            except Exception:
                return value
        else:
            return value
    from django.db.models import (
        IntegerField, PositiveIntegerField, PositiveSmallIntegerField,
        SmallIntegerField, BigIntegerField, BooleanField, FloatField,
        DecimalField, JSONField, ForeignKey, AutoField,
    )
    int_types = (IntegerField, PositiveIntegerField, PositiveSmallIntegerField,
                 SmallIntegerField, BigIntegerField)
    # ForeignKey: coerce the PK value to the related model's PK type
    if isinstance(field, ForeignKey):
        related_pk = field.related_model._meta.pk
        if isinstance(related_pk, (AutoField,) + int_types):
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        return value
    if isinstance(field, int_types):
        try:
            return int(value)
        except (ValueError, TypeError):
            # For IntegerChoices fields, accept text labels (e.g., "medium" -> 2)
            if hasattr(field, 'choices') and field.choices:
                value_lower = str(value).lower()
                for choice_val, choice_label in field.choices:
                    if value_lower == str(choice_label).lower():
                        return choice_val
            return value
    if isinstance(field, BooleanField):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    if isinstance(field, FloatField):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    if isinstance(field, JSONField) and isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def _create_handler(model_class, writable_fields, scope_filtered=True, m2m_fields=None):
    """Create a generic create handler."""
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        kwargs = {}
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in arguments:
                if field_name in m2m_fields:
                    m2m_values[field_name] = arguments[field_name]
                else:
                    kwargs[field_name] = _coerce_field_value(
                        model_class, field_name, arguments[field_name])
        if hasattr(model_class, "created_by"):
            kwargs["created_by"] = user
        try:
            obj = model_class(**kwargs)
            obj.full_clean()
            obj.save()
            # Set M2M fields after save
            for param_name, ids in m2m_values.items():
                m2m_attr = m2m_fields[param_name]
                getattr(obj, m2m_attr).set(ids)
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _batch_create_handler(model_class, writable_fields, scope_filtered=True, m2m_fields=None):
    """Create a generic batch create handler (non-atomic: partial success)."""
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        items = arguments.get("items", [])
        if not isinstance(items, list) or not items:
            return _error("'items' must be a non-empty array of objects.")
        if len(items) > 500:
            return _error("Batch size limited to 500 items.")

        results = []
        created_count = 0
        error_count = 0
        fields = [f.name for f in model_class._meta.fields]
        for idx, item_data in enumerate(items):
            try:
                if not isinstance(item_data, dict):
                    raise ValidationError(
                        f"Expected an object, got {type(item_data).__name__}.")
                kwargs = {}
                m2m_values = {}
                for field_name in writable_fields:
                    if field_name in item_data:
                        if field_name in m2m_fields:
                            m2m_values[field_name] = item_data[field_name]
                        else:
                            kwargs[field_name] = _coerce_field_value(
                                model_class, field_name, item_data[field_name])
                if hasattr(model_class, "created_by"):
                    kwargs["created_by"] = user
                obj = model_class(**kwargs)
                obj.full_clean()
                obj.save()
                for param_name, ids in m2m_values.items():
                    m2m_attr = m2m_fields[param_name]
                    getattr(obj, m2m_attr).set(ids)
                results.append({
                    "index": idx,
                    "status": "created",
                    "id": str(obj.pk),
                    "reference": getattr(obj, "reference", None),
                })
                created_count += 1
            except (ValidationError, Exception) as e:
                results.append({
                    "index": idx,
                    "status": "error",
                    "errors": str(e),
                })
                error_count += 1
        return {
            "status": "completed" if error_count == 0 else "completed_with_errors",
            "total": len(items),
            "created": created_count,
            "errors": error_count,
            "results": results,
        }
    return handler


def _update_handler(model_class, writable_fields, scope_filtered=True, m2m_fields=None):
    """Create a generic update handler."""
    m2m_fields = m2m_fields or {}

    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")
        changed_fields = set()
        m2m_values = {}
        for field_name in writable_fields:
            if field_name in arguments:
                if field_name in m2m_fields:
                    m2m_values[field_name] = arguments[field_name]
                    changed_fields.add(field_name)
                else:
                    setattr(obj, field_name, _coerce_field_value(
                        model_class, field_name, arguments[field_name]))
                    changed_fields.add(field_name)
        # Reset approval on update (respects VersioningConfig)
        if hasattr(obj, "is_approved") and hasattr(obj, "version"):
            from core.models import VersioningConfig
            if VersioningConfig.is_approval_enabled(model_class):
                major_fields = VersioningConfig.get_major_fields(model_class)
                is_major = major_fields is None or bool(changed_fields & major_fields)
                if is_major:
                    obj.is_approved = False
                    obj.approved_by = None
                    obj.approved_at = None
                    obj.version = (obj.version or 0) + 1
        try:
            obj.full_clean()
            obj.save()
            # Set M2M fields after save
            for param_name, ids in m2m_values.items():
                m2m_attr = m2m_fields[param_name]
                getattr(obj, m2m_attr).set(ids)
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _delete_handler(model_class, scope_filtered=True):
    """Create a generic delete handler."""
    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        if scope_filtered:
            qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
            if not qs.exists():
                return _error("Access denied: object is outside your allowed scopes.")
        obj.delete()
        return {"deleted": True, "id": str(pk)}
    return handler


def _approve_handler(model_class, scope_filtered=True):
    """Create a generic approve handler."""
    def handler(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        obj.is_approved = True
        obj.approved_by = user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        return {"approved": True, "id": str(pk)}
    return handler


# ── Schema helpers ─────────────────────────────────────────

def _list_schema(extra_props=None):
    props = {
        "search": {"type": "string", "description": "Text search query"},
        "limit": {"type": "integer", "description": "Max items to return (default 25, max 100)"},
        "offset": {"type": "integer", "description": "Offset for pagination"},
    }
    if extra_props:
        props.update(extra_props)
    return {"type": "object", "properties": props}


def _id_schema():
    return {
        "type": "object",
        "properties": {"id": {"type": "string", "description": "UUID of the object"}},
        "required": ["id"],
    }


def _obj_schema(properties, required=None):
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _html_field(label):
    """Return a field override dict indicating an HTML rich-text field."""
    return {"type": "string", "description": f"{label} (HTML rich text)"}


# Common override for entities that only have a description rich-text field.
_HTML_DESC = {"description": _html_field("Description")}


# ── Tool registration ──────────────────────────────────────

def register_all_tools(server):
    """Register all MCP tools on the given McpServer instance."""
    _register_help_tool(server)
    _register_context_tools(server)
    _register_assets_tools(server)
    _register_compliance_tools(server)
    _register_risks_tools(server)
    _register_accounts_tools(server)
    _register_reports_tools(server)


# ── Help Tool ─────────────────────────────────────────────

def _register_help_tool(server):
    """Register the MCP help tool that describes how to use the Fairway MCP server."""

    HELP_TEXT = """\
# Fairway MCP Server - Usage Guide

Fairway is a Governance, Risk & Compliance (GRC) platform. This MCP server
exposes its full API as tools organized by module.

Call `help` with a topic for detailed field-level documentation:
  context, assets, compliance, risks, batch, workflow, permissions, examples

## Modules

| Module | Prefix | Description |
|--------|--------|-------------|
| Context | context.* | Organizational context: scopes, issues, stakeholders, objectives, SWOT, roles, activities, sites, indicators |
| Assets | assets.* | Asset management: essential assets, support assets, dependencies, groups, suppliers |
| Compliance | compliance.* | Compliance: frameworks, sections, requirements, assessments, findings, action plans, mappings |
| Risks | risks.* | Risk management: criteria, assessments, risks, treatment plans, threats, vulnerabilities, ISO 27005 |
| Accounts | system.* | Users, groups, permissions, access logs, company settings |
| Reports | compliance.report.* | SOA and audit report generation |

## Tool Naming Convention

Every entity follows a consistent CRUD pattern:

| Operation | Tool pattern | Description |
|-----------|-------------|-------------|
| List | `list_{entity}s` | Paginated list. Params: search, limit (default 50), offset, plus entity-specific filters |
| Get | `get_{entity}` | Get one by ID. Param: id (UUID) |
| Create | `create_{entity}` | Create one. Returns the created object with all fields |
| Batch Create | `batch_create_{entity}s` | Create up to 500 items. Param: items (array). Non-atomic: valid items are created even if others fail |
| Update | `update_{entity}` | Update by ID. Param: id + only the fields to change (partial update) |
| Delete | `delete_{entity}` | Delete by ID. Param: id |
| Approve | `approve_{entity}` | Approve (where workflow applies). Param: id |

## Key Concepts

### UUIDs
All domain objects use UUID primary keys (e.g. "550e8400-e29b-41d4-a716-446655440000").
Foreign key fields expect UUID strings.
Exception: SupplierType uses integer auto-increment IDs.

### Scopes
Scopes represent organizational boundaries (departments, subsidiaries, projects).
Most entities have a `scopes` M2M field (array of scope UUIDs).
Users only see objects within their assigned scopes (unless superuser).
Always pass scopes when creating scoped entities, or they will be invisible to non-superusers.

### Approval Workflow
Entities with `is_approved` support a two-step workflow: create/update, then approve_*.
Updating a major field resets approval to false and increments version.

### References
Most entities auto-generate a unique reference on creation (e.g. RISK-1, REQT-42, SUPP-3).
References are read-only and sequential. Reference prefixes by entity:
  Scope=SCOP, Issue=ISSU, Stakeholder=STKH, Objective=OBJT, SwotAnalysis=SWOT,
  Role=ROLE, Activity=ACTV, Site=SITE, Indicator=INDI,
  EssentialAsset=EAST, SupportAsset=SAST, AssetDependency=ADEP, AssetGroup=AGRP,
  Supplier=SUPP, SupplierType=SPTY, SupplierDependency=SDEP,
  SiteAssetDependency=SADP, SiteSupplierDependency=SSDP,
  Framework=FRMW, Section=SECT, Requirement=REQT, ComplianceAssessment=CASS,
  Finding=(NCMAJ/NCMIN/OBS/OA/STR per type), ActionPlan=ACTPL,
  RiskCriteria=RCRT, RiskAssessment=RASS, Risk=RISK,
  RiskTreatmentPlan=RTPL, Threat=THRT, Vulnerability=VULN, ISO27005Risk=I27R

### HTML Rich Text Fields
Fields marked "(HTML)" accept HTML rich text content.
Use standard HTML tags: <p>, <ul>, <li>, <strong>, <em>, <a>, <table>, <h3>, etc.

## Error Handling

- Permission denied: {"error": "Permission denied: <codename>"}
- Not found: {"error": "<Entity> not found."}
- Validation error: {"error": "<field details>"}
- All errors set isError: true in the response
"""

    TOPIC_CONTEXT = """\
# Context Module - Field Reference

## scope
Writable: name (required), description (HTML), type, status, effective_date, review_date, manager_ids
- type: draft | active | archived
- status: draft | active | archived
- manager_ids: array of user UUIDs (M2M, scope managers get automatic access)
- effective_date / review_date: ISO 8601 date (e.g. "2025-12-31")
Filters: type, status

## issue
Writable: name (required), description (HTML), type, category, impact_level, priority, status, owner_id, review_date, scopes
- type: internal | external
- category (internal): strategic | organizational | human_resources | technical | financial | cultural
- category (external): political | economic | social | technological | legal | environmental | competitive | regulatory
- impact_level: low | medium | high | critical
- priority: low | medium | high | critical
- status: identified | active | monitored | closed
Filters: type, category, priority, status

## stakeholder
Writable: name (required), type (required), category (required), description, contact_name, contact_email, contact_phone, influence_level (required), interest_level (required), status, review_date, scopes
- type: internal | external
- category: executive_management | employees | customers | suppliers | partners | regulators | shareholders | insurers | public | competitors | unions | auditors | other
- influence_level: low | medium | high
- interest_level: low | medium | high
- status: active | inactive
Filters: type, category, influence_level, interest_level, status

## expectation (nested under stakeholder)
Writable: stakeholder_id (required), name (required), description, type, priority
- type: requirement | expectation | need
- priority: low | medium | high | critical
Filters: stakeholder_id, type, priority

## objective
Writable: name (required), description (HTML), type, category, priority, status, target_date, owner_id, linked_issues, scopes
- type: security | compliance | business | other
- category: confidentiality | integrity | availability | compliance | operational | strategic
- priority: low | medium | high | critical
- status: draft | active | achieved | not_achieved | cancelled
- linked_issues: array of issue UUIDs (M2M)
Filters: type, priority, status

## swot_analysis
Writable: name (required), description (HTML), scope_id, status, scopes
- status: draft | validated | archived
Filters: status

## swot_item
Writable: analysis_id (required), category (required), description (required), priority
- category: strength | weakness | opportunity | threat
- priority: low | medium | high | critical
Filters: analysis_id, category, priority

## swot_strategy
Writable: analysis_id (required), strategy_type (required), name (required), description (HTML), priority, status, target_date, owner_id, linked_items
- strategy_type: so | st | wo | wt (Strengths-Opportunities, Strengths-Threats, Weaknesses-Opportunities, Weaknesses-Threats)
- priority: low | medium | high | critical
- status: draft | active | archived
- linked_items: array of swot_item UUIDs (M2M)
Filters: analysis_id, strategy_type, priority, status

## role
Writable: name (required), description (HTML), type, status, holder_id, scopes
- type: governance | operational | support | control
- status: active | inactive
- holder_id: UUID of the user holding this role
Filters: type, status

## responsibility (nested under role)
Writable: role_id (required), name (required), description, raci_type
- raci_type: responsible | accountable | consulted | informed
Filters: role_id

## activity
Writable: name (required), description (HTML), type, status, owner_id, scopes
- type: core_business | support | management
- status: active | inactive | planned
Filters: type, status, owner_id

## site
Writable: name (required), description (HTML), type, status, address, city, country, latitude, longitude, scopes
- type: siege | bureau | usine | entrepot | datacenter | site_distant | autre
- status: draft | active | archived
Filters: type, status, country

## indicator
Writable: name (required), description (HTML), type, format, unit, frequency, collection_method, target_value, critical_threshold, critical_threshold_operator, status, objective_id, scopes
- type: organizational | technical
- format: number | boolean
- frequency: daily | weekly | monthly | quarterly | semi_annual | annual
- collection_method: manual | api | internal
- critical_threshold_operator: below | above | is_false | is_true
- status: active | inactive | draft
Filters: type, frequency, status, objective_id

## indicator_measurement
Writable: indicator_id (required), value (required), measured_at, measured_by_id, comment
Filters: indicator_id

## tag
Only 3 tools: list_tags, create_tag(name, color), delete_tag(id)
"""

    TOPIC_ASSETS = """\
# Assets Module - Field Reference

## essential_asset
Writable: name (required), description (HTML), type (required), category, owner_id (required), custodian_id,
  confidentiality_level, integrity_level, availability_level,
  confidentiality_justification, integrity_justification, availability_justification,
  max_tolerable_downtime, recovery_time_objective, recovery_point_objective,
  data_classification, personal_data, personal_data_categories, regulatory_constraints,
  related_activities, status, review_date, tags, scopes
- type: business_process | information
- category (process): core_process | support_process | management_process
- category (info): strategic_data | operational_data | personal_data | financial_data | technical_data | legal_data | research_data | commercial_data
- confidentiality/integrity/availability_level: integer 0-4 OR text: negligible | low | medium | high | critical
- data_classification: public | internal | confidential | restricted | secret
- personal_data: boolean
- status: identified | active | under_review | decommissioned
- tags: array of tag UUIDs (M2M)
Filters: type, category, status, owner_id, data_classification, personal_data
Ref prefix: EAST

## support_asset
Writable: name (required), description (HTML), type (required), category, owner_id (required), custodian_id,
  location, manufacturer, model_name, serial_number, software_version,
  ip_address, hostname, operating_system,
  acquisition_date, end_of_life_date, warranty_expiry_date, contract_reference,
  exposure_level, environment, parent_asset_id, status, review_date, tags, scopes
- type: hardware | software | network | person | site | service | paper
- category (hardware): server | workstation | laptop | mobile_device | network_equipment | storage | peripheral | iot_device | removable_media | other_hardware
- category (software): operating_system | database | application | middleware | security_tool | development_tool | saas_application | other_software
- category (network): lan | wan | wifi | vpn | internet_link | firewall_zone | dmz | other_network
- category (person): internal_staff | contractor | external_provider | administrator | developer | other_person
- category (site): datacenter | office | remote_site | cloud_region | other_site
- category (service): cloud_service | hosting_service | managed_service | telecom_service | outsourced_service | other_service
- category (paper): archive | printed_document | form | other_paper
- exposure_level: internal | exposed | internet_facing | dmz
- environment: production | staging | development | test | disaster_recovery
- status: in_stock | deployed | active | under_maintenance | decommissioned | disposed
Read-only computed: inherited_confidentiality, inherited_integrity, inherited_availability (inherited from essential assets via dependencies)
Filters: type, category, status, environment, exposure_level, owner_id
Ref prefix: SAST

## asset_dependency
Links an essential asset to a support asset.
Writable: essential_asset_id (required), support_asset_id (required), dependency_type (required), criticality (required), description (HTML)
- dependency_type: runs_on | stored_in | transmitted_by | managed_by | hosted_at | protected_by | other
- criticality: low | medium | high | critical
Read-only: is_single_point_of_failure (auto-detected), redundancy_level
Filters: essential_asset_id, support_asset_id, dependency_type, criticality
Ref prefix: ADEP

## asset_valuation
DIC valuation record for an essential asset.
Writable: essential_asset_id (required), evaluation_date, confidentiality_level (0-4), integrity_level (0-4), availability_level (0-4), justification, context
Creating a valuation automatically updates the essential asset's DIC levels.
Filters: essential_asset_id

## asset_group
Writable: name (required), description, type, members (array of support_asset UUIDs), owner_id, status, tags, scopes
- type: hardware | software | network | person | site | service | paper
- status: active | inactive
Filters: type, status, owner_id
Ref prefix: AGRP

## supplier
Writable: name (required), description (HTML), type, criticality, owner_id (required),
  contact_name, contact_email, contact_phone, website, address, country,
  contract_reference, contract_start_date, contract_end_date, status, notes (HTML), tags, scopes
- type: INTEGER (SupplierType ID, NOT a UUID). Use list_supplier_types to get valid IDs.
- criticality: low | medium | high | critical
- status: active | under_evaluation | suspended | archived
Special tools: update_supplier_logo(id, image_url) - fetches and stores logo from URL
Filters: type, criticality, status, owner_id, country
Ref prefix: SUPP

## supplier_type
Writable: name (required), description
Ref prefix: SPTY (integer PK, not UUID)

## supplier_dependency
Links a support asset to a supplier.
Writable: support_asset_id (required), supplier_id (required), dependency_type (required), criticality (required), description (HTML)
- dependency_type: provides | hosts | manages | develops | supports | licenses | maintains | other
- criticality: low | medium | high | critical
Filters: support_asset_id, supplier_id
Ref prefix: SDEP

## site_asset_dependency
Links a site to a support asset.
Writable: support_asset_id (required), site_id (required), dependency_type (required), criticality (required), description (HTML), is_single_point_of_failure (bool), redundancy_level
- dependency_type: located_at | hosted_at | deployed_at | other
- criticality: low | medium | high | critical
- redundancy_level: none | partial | full
Filters: support_asset_id, site_id, dependency_type, criticality
Ref prefix: SADP

## site_supplier_dependency
Links a site to a supplier.
Writable: site_id (required), supplier_id (required), dependency_type (required), criticality (required), description (HTML), is_single_point_of_failure (bool), redundancy_level
- dependency_type: provides | hosts | manages | develops | supports | licenses | maintains | other
- criticality: low | medium | high | critical
- redundancy_level: none | partial | full
Filters: site_id, supplier_id, dependency_type, criticality
Ref prefix: SSDP

## supplier_requirement
Writable: supplier_id (required), title (required), description, requirement_id (FK to compliance requirement, optional), compliance_status, evidence, due_date
- compliance_status: not_assessed | compliant | partially_compliant | non_compliant
Filters: supplier_id, compliance_status

## supplier_requirement_review
Writable: supplier_requirement_id (required), review_date, reviewer_id, result, comment, evidence_file
- result: not_assessed | compliant | partially_compliant | non_compliant
Filters: supplier_requirement_id, result
"""

    TOPIC_COMPLIANCE = """\
# Compliance Module - Field Reference

## framework
Writable: name (required), short_name, description (HTML), type, category, version_label, source_url, publication_date, effective_date, owner_id, status, scopes
- type: standard | law | regulation | contract | internal_policy | industry_framework | other
- category: information_security | privacy | risk_management | business_continuity | cloud_security | sector_specific | it_governance | quality | contractual | internal | other
- status: draft | active | under_review | deprecated | archived
Filters: type, category, status
Ref prefix: FRMW

## section
Writable: framework_id (required), name (required), description, order (integer for sorting), parent_section_id (UUID for nesting)
Sections form a tree: use parent_section_id to nest (e.g. "A.5" under "A").
Filters: framework_id, parent_section_id
Ref prefix: SECT

## requirement
Writable: framework_id (required), section_id, requirement_number, name (required), description (HTML, required), guidance (HTML),
  type, category, is_applicable (bool), applicability_justification,
  compliance_status, compliance_level (0-100), compliance_evidence (HTML), compliance_finding (HTML),
  owner_id, priority, target_date, linked_assets (M2M), linked_stakeholder_expectations (M2M), linked_risks (M2M, required - pass [] if none),
  status, tags
- type: mandatory | recommended | optional
- category: organizational | technical | physical | legal | human | other
- compliance_status: not_assessed | evaluated | non_compliant | partially_compliant | major_non_conformity | minor_non_conformity | observation | improvement_opportunity | compliant | strength | not_applicable
- priority: low | medium | high | critical
- status: active | deprecated | superseded
Filters: framework_id, section_id, type, compliance_status, priority, is_applicable
Ref prefix: REQT

## requirement_mapping
Maps requirements across frameworks.
Writable: source_requirement_id (required), target_requirement_id (required), mapping_type (required), coverage_level, notes
- mapping_type: equivalent | partial_overlap | includes | included_by | related
- coverage_level: full | partial | minimal
Filters: source_requirement_id, target_requirement_id, mapping_type

## compliance_assessment (custom CRUD)
Writable: name (required), description (HTML), limitations (HTML), assessment_start_date, assessment_end_date, status, assessor_id, framework_ids (array of framework UUIDs)
- status: draft | planned | in_progress | completed | closed | cancelled
- framework_ids: when set, assessment_results are auto-created for all requirements in those frameworks
Read-only computed: overall_compliance_level, total_requirements, compliant_count, major_non_conformity_count, minor_non_conformity_count, observation_count, improvement_opportunity_count, strength_count, not_applicable_count

Assessment status transitions:
  draft -> planned -> in_progress -> completed -> closed
  draft -> cancelled
  planned -> cancelled
  (completed and closed are terminal - cannot go back)

## assessment_result (custom CRUD)
Writable: assessment_id (required), requirement_id (required), compliance_status, compliance_level (0-100), finding (HTML), auditor_recommendations (HTML), evidence (HTML), assessed_by_id, assessed_at
- compliance_status: not_assessed | evaluated | major_non_conformity | minor_non_conformity | observation | improvement_opportunity | compliant | strength | not_applicable
Updating a result auto-recalculates the assessment's aggregate counts.

## finding (custom CRUD)
Writable: assessment_id (required), finding_type (required), description (HTML, required), evidence (HTML), recommendation (HTML), assessor_id, requirement_ids (M2M array)
- finding_type: major_nc | minor_nc | observation | improvement | strength
Reference auto-generated per type: NCMAJ-x, NCMIN-x, OBS-x, OA-x, STR-x
Creating/updating/deleting findings auto-applies to linked assessment_results.

## action_plan
Writable: name (required), description (HTML), gap_description (HTML), remediation_plan (HTML), priority, target_date, progress_percentage (0-100), owner_id, assignees (M2M user UUIDs), requirements (M2M requirement UUIDs)
- priority: low | medium | high | critical
- status is READ-ONLY - use action_plan_transition tool to change it (see help topic "workflow")
Filters: status, priority, owner_id, requirement_id
Ref prefix: ACTPL

## Special compliance tools
- get_framework_compliance_summary(framework_id) - returns per-section compliance stats
- generate_soa_report(framework_id, title) - Statement of Applicability PDF
- generate_audit_report(assessment_id, title) - Audit report PDF
- list_reports / delete_report(id) - manage generated reports
"""

    TOPIC_RISKS = """\
# Risks Module - Field Reference

## risk_criteria
Defines evaluation scales (likelihood/impact) and risk level thresholds.
Writable: name (required), description (HTML), methodology, status, scopes
- methodology: iso27005 | ebios_rm
- status: draft | active | archived
After creating criteria, add scale_levels and risk_levels.
Filters: status
Ref prefix: RCRT

## scale_level
Writable: criteria_id (required), scale_type (required), level (required, integer 1-5), name (required), description, color
- scale_type: likelihood | impact
Example: create 5 likelihood levels (1=Very Low to 5=Very High) and 5 impact levels.
Filters: criteria_id

## risk_level
Writable: criteria_id (required), level (required, integer), name (required), color (hex, e.g. "#ff0000"), min_score, max_score, treatment_required (bool), description
Example: level 1 "Low" (green, min=1 max=5), level 4 "Critical" (red, min=16 max=25)
Filters: criteria_id

## risk_assessment
Writable: name (required), description (HTML), risk_criteria_id, methodology, assessment_date, assessor_id, status, scopes
- methodology: iso27005 | ebios_rm
- status: draft | in_progress | completed | validated | archived
Filters: status, assessor_id, risk_criteria_id
Ref prefix: RASS

## risk
Writable: name (required), description (HTML), assessment_id (required),
  status, priority, treatment_decision, risk_source_type,
  initial_likelihood (int), initial_impact (int),
  current_likelihood (int), current_impact (int),
  residual_likelihood (int), residual_impact (int),
  risk_owner_id, justification (HTML)
- status: identified | analyzed | evaluated | treatment_planned | treatment_in_progress | treated | accepted | closed | monitoring
- priority: low | medium | high | critical
- treatment_decision: accept | mitigate | transfer | avoid | not_decided
- risk_source_type: iso27005_analysis | ebios_strategic | ebios_operational | incident | audit | compliance | manual
- likelihood/impact values: integers matching scale_level.level (typically 1-5)
Read-only computed: current_risk_level (from criteria matrix)
Filters: assessment_id, status, treatment_decision, priority, risk_owner_id
Ref prefix: RISK

## risk_treatment_plan
Writable: name (required), description (HTML), risk_id (required), owner_id, target_date, status, progress_percentage (0-100), expected_residual_likelihood (int), expected_residual_impact (int)
- status: planned | in_progress | completed | cancelled | overdue
After creating, add treatment_actions.
Filters: risk_id, status, owner_id
Ref prefix: RTPL

## treatment_action
Writable: treatment_plan_id (required), name (required), description (HTML), responsible_id (user UUID), due_date, status, completion_date
- status: planned | in_progress | completed | cancelled
Filters: treatment_plan_id, status

## risk_acceptance
Writable: risk_id (required), accepted_by_id (required), justification (HTML), conditions, valid_until (date), status
- status: active | expired | revoked | renewed
Filters: risk_id, status, accepted_by_id

## threat
Writable: name (required), description (HTML), type, source, category, status, scopes
- type: deliberate | accidental | environmental | other
- source: human_internal | human_external | natural | technical | other
- category: malware | social_engineering | unauthorized_access | denial_of_service | data_breach | physical_attack | espionage | fraud | sabotage | human_error | system_failure | network_failure | power_failure | natural_disaster | fire | water_damage | theft | vandalism | supply_chain | insider_threat | ransomware | apt
- status: active | inactive
Filters: type, source, status
Ref prefix: THRT

## vulnerability
Writable: name (required), description (HTML), category, severity, affected_asset_types (array), affected_assets (M2M support_asset UUIDs), cve_references, remediation_guidance (HTML), is_from_catalog (bool), status, tags, scopes
- category: configuration_weakness | missing_patch | design_flaw | coding_error | weak_authentication | insufficient_logging | lack_of_encryption | physical_vulnerability | organizational_weakness | human_factor | obsolescence | insufficient_backup | network_exposure | third_party_dependency
- severity: low | medium | high | critical
- status: identified | confirmed | mitigated | accepted | closed
Filters: category, severity, status
Ref prefix: VULN

## iso27005_risk
Combines threat + vulnerability + impact for ISO 27005 analysis.
Writable: assessment_id (required), threat_id (required), vulnerability_id (required),
  threat_likelihood (int 1-5), vulnerability_exposure (int 1-5),
  impact_confidentiality (int 1-5), impact_integrity (int 1-5), impact_availability (int 1-5),
  existing_controls (HTML), risk_id (optional, link to a Risk entity), description (HTML)
Read-only computed:
  combined_likelihood = max(threat_likelihood, vulnerability_exposure)
  max_impact = max(impact_confidentiality, impact_integrity, impact_availability)
  risk_level = combined_likelihood * max_impact (mapped to risk_level thresholds)
Filters: assessment_id, threat_id, vulnerability_id
Ref prefix: I27R

## Risk-Requirement linking tools
- list_risk_requirements(risk_id) - list requirements linked to a risk
- list_requirement_risks(requirement_id) - list risks linked to a requirement
- link_risk_requirements(risk_id, requirement_ids) - add links (additive)
- unlink_risk_requirements(risk_id, requirement_ids) - remove links
- set_risk_requirements(risk_id, requirement_ids) - replace all links
"""

    TOPIC_WORKFLOW = """\
# Workflow Reference

## Action Plan Workflow (Kanban)

Status values: new | to_define | to_validate | to_implement | implementation_to_validate | validated | closed | cancelled

### Forward transitions:
  new -> to_define (permission: compliance.action_plan.update)
  to_define -> to_validate (permission: compliance.action_plan.update)
  to_validate -> to_implement (permission: compliance.action_plan.validate)
  to_implement -> implementation_to_validate (permission: compliance.action_plan.implement)
  implementation_to_validate -> validated (permission: compliance.action_plan.validate)
  validated -> closed (permission: compliance.action_plan.close)

### Refusal transitions (comment MANDATORY):
  to_validate -> to_define (permission: compliance.action_plan.validate)
  implementation_to_validate -> to_implement (permission: compliance.action_plan.validate)

### Cancellation (comment recommended):
  Any status except closed/cancelled -> cancelled (permission: compliance.action_plan.cancel)

### Tools:
- action_plan_transition(action_plan_id, target_status, comment)
  Execute a transition. Returns {id, status, reference}.
  Example: action_plan_transition(action_plan_id="<uuid>", target_status="to_define")
  Example with refusal: action_plan_transition(action_plan_id="<uuid>", target_status="to_define", comment="Missing evidence, please complete section 3")

- action_plan_allowed_transitions(action_plan_id)
  Returns current_status and list of allowed next statuses with permission requirements.

- action_plan_transitions(action_plan_id)
  Returns full transition history (who, when, from/to status, comment, is_refusal).

- action_plan_kanban()
  Returns Kanban board: columns grouped by status with action plans and workflow rules.

### Typical action plan lifecycle:
1. create_action_plan(name="Remediate A.8.1", priority="high", owner_id="<uuid>", target_date="2025-06-30", requirements=["<req-uuid>"])
2. action_plan_transition(action_plan_id="<uuid>", target_status="to_define")
3. update_action_plan(id="<uuid>", remediation_plan="<html>", gap_description="<html>")
4. action_plan_transition(action_plan_id="<uuid>", target_status="to_validate")
5. action_plan_transition(action_plan_id="<uuid>", target_status="to_implement")   -- or refuse back to to_define
6. update_action_plan(id="<uuid>", progress_percentage=50)
7. action_plan_transition(action_plan_id="<uuid>", target_status="implementation_to_validate")
8. action_plan_transition(action_plan_id="<uuid>", target_status="validated")   -- or refuse back to to_implement
9. action_plan_transition(action_plan_id="<uuid>", target_status="closed")

## Compliance Assessment Workflow

Status values: draft | planned | in_progress | completed | closed | cancelled

### Transitions:
  draft -> planned
  draft -> cancelled
  planned -> in_progress
  planned -> cancelled
  in_progress -> completed
  completed -> closed

### Assessment lifecycle:
1. create_compliance_assessment(name="ISO 27001 Audit 2025", framework_ids=["<fw-uuid>"], assessor_id="<user-uuid>", status="draft")
   -> Auto-creates assessment_results for every requirement in the linked frameworks
2. update_compliance_assessment(id="<uuid>", status="planned", assessment_start_date="2025-04-01")
3. update_compliance_assessment(id="<uuid>", status="in_progress")
4. For each requirement: update_assessment_result(id="<result-uuid>", compliance_status="compliant", evidence="<html>")
   Or for non-conformities: create_finding(assessment_id="<uuid>", finding_type="major_nc", description="<html>", requirement_ids=["<req-uuid>"])
5. update_compliance_assessment(id="<uuid>", status="completed")
6. generate_audit_report(assessment_id="<uuid>", title="ISO 27001 Audit Report 2025")
7. update_compliance_assessment(id="<uuid>", status="closed")

## Approval Workflow (all approvable entities)

Any entity with approve_* tool follows:
1. Create or update the entity
2. Call approve_{entity}(id="<uuid>") to mark as approved
3. If a major field is later updated, approval resets automatically (is_approved=false, version increments)
4. Re-approve after review
"""

    TOPIC_BATCH = """\
# Batch Creation - Detailed Reference

## Endpoint
All entities support batch_create_{entity}s(items=[...])
Maximum: 500 items per call.

## Behavior
NON-ATOMIC: each item is processed independently.
Valid items are created even if others fail.
Use this for bulk import - do not worry about partial failures.

## Request format
{"items": [{field1: value1, ...}, {field1: value2, ...}, ...]}

## Response format
{
  "status": "completed" | "completed_with_errors",
  "total": N,         // total items submitted
  "created": M,       // successfully created
  "errors": E,        // failed items
  "results": [
    {"index": 0, "status": "created", "id": "<uuid>", "reference": "REQT-1"},
    {"index": 1, "status": "error", "errors": "['name': ['This field is required.']]"},
    {"index": 2, "status": "created", "id": "<uuid>", "reference": "REQT-2"}
  ]
}

## Example: Populate ISO 27001 Annex A

Step 1 - Create framework:
  create_framework(name="ISO/IEC 27001:2022", type="standard", category="information_security")

Step 2 - Create sections:
  batch_create_sections(items=[
    {"framework_id": "<fw-uuid>", "name": "A.5 Organizational controls", "order": 1},
    {"framework_id": "<fw-uuid>", "name": "A.6 People controls", "order": 2},
    {"framework_id": "<fw-uuid>", "name": "A.7 Physical controls", "order": 3},
    {"framework_id": "<fw-uuid>", "name": "A.8 Technological controls", "order": 4}
  ])

Step 3 - Create requirements:
  batch_create_requirements(items=[
    {"framework_id": "<fw-uuid>", "section_id": "<a5-uuid>", "requirement_number": "A.5.1", "name": "Policies for information security", "description": "...", "type": "mandatory", "linked_risks": []},
    {"framework_id": "<fw-uuid>", "section_id": "<a5-uuid>", "requirement_number": "A.5.2", "name": "Information security roles and responsibilities", "description": "...", "type": "mandatory", "linked_risks": []},
    ...
  ])

## Example: Populate threat catalog

  batch_create_threats(items=[
    {"name": "Ransomware attack", "type": "deliberate", "source": "human_external", "category": "ransomware"},
    {"name": "Phishing campaign", "type": "deliberate", "source": "human_external", "category": "social_engineering"},
    {"name": "Power outage", "type": "environmental", "source": "technical", "category": "power_failure"},
    {"name": "Accidental data deletion", "type": "accidental", "source": "human_internal", "category": "human_error"},
    ...
  ])

## Example: Populate risk register

  batch_create_risks(items=[
    {"assessment_id": "<ra-uuid>", "name": "Data breach via phishing", "status": "identified", "priority": "high", "initial_likelihood": 4, "initial_impact": 5, "treatment_decision": "mitigate"},
    {"assessment_id": "<ra-uuid>", "name": "Service disruption from power failure", "status": "identified", "priority": "medium", "initial_likelihood": 2, "initial_impact": 3, "treatment_decision": "transfer"},
    ...
  ])

## Example: Populate suppliers

  batch_create_suppliers(items=[
    {"name": "AWS", "type": 1, "criticality": "critical", "owner_id": "<user-uuid>", "status": "active", "country": "US"},
    {"name": "OVHcloud", "type": 1, "criticality": "high", "owner_id": "<user-uuid>", "status": "active", "country": "FR"},
    ...
  ])
  Note: "type" is an integer SupplierType ID. Use list_supplier_types() first to get IDs.
"""

    TOPIC_PERMISSIONS = """\
# Permissions Reference

## Permission format
All permissions follow: module.feature.action

## Actions
- read: view/list entities
- create: create new entities
- update: modify existing entities
- delete: remove entities
- approve: approve entities (where approval workflow applies)

## Special action plan permissions
- compliance.action_plan.validate: approve or refuse at validation stages
- compliance.action_plan.implement: submit implementation for validation
- compliance.action_plan.close: close a validated action plan
- compliance.action_plan.cancel: cancel an action plan

## Module permissions

### Context (context.*)
context.scope.read/create/update/delete/approve
context.issue.read/create/update/delete/approve
context.stakeholder.read/create/update/delete/approve
context.objective.read/create/update/delete/approve
context.swot.read/create/update/delete/approve
context.role.read/create/update/delete/approve
context.activity.read/create/update/delete/approve
context.site.read/create/update/delete/approve
context.indicator.read/create/update/delete/approve

### Assets (assets.*)
assets.essential_asset.read/create/update/delete/approve
assets.support_asset.read/create/update/delete/approve
assets.dependency.read/create/update/delete
assets.group.read/create/update/delete/approve
assets.supplier.read/create/update/delete/approve
assets.supplier_dependency.read/create/update/delete

### Compliance (compliance.*)
compliance.framework.read/create/update/delete/approve
compliance.section.read/create/update/delete
compliance.requirement.read/create/update/delete/approve
compliance.assessment.read/create/update/delete/approve
compliance.action_plan.read/create/update/delete/approve/validate/implement/close/cancel
compliance.report.read/create/delete

### Risks (risks.*)
risks.criteria.read/create/update/delete
risks.assessment.read/create/update/delete/approve
risks.risk.read/create/update/delete/approve
risks.treatment.read/create/update/delete/approve
risks.acceptance.read/create/update/delete
risks.threat.read/create/update/delete/approve
risks.vulnerability.read/create/update/delete/approve
risks.iso27005.read/create/update/delete

### System
system.config.read/update
system.users.read
system.logs.read

## System roles (predefined groups)
- Super Admin: all permissions
- Admin: all permissions except system config
- RSSI/DPO: read/create/update/approve on all modules
- Auditeur: read on all modules, create/update on compliance
- Contributeur: read/create/update on assigned scopes
- Lecteur: read-only on assigned scopes

Superusers bypass all permission checks.
Use list_permissions() to see all available codenames.
"""

    TOPIC_EXAMPLES = """\
# End-to-End Examples

## Example 1: Full compliance audit workflow

### Step 1: Set up the framework (one-time)
  create_framework(name="ISO/IEC 27001:2022", type="standard", category="information_security", status="active")
  -> returns {id: "<fw-uuid>", reference: "FRMW-1", ...}

  batch_create_sections(items=[
    {"framework_id": "<fw-uuid>", "name": "A.5 Organizational controls", "order": 1},
    {"framework_id": "<fw-uuid>", "name": "A.6 People controls", "order": 2}
  ])
  -> returns section UUIDs

  batch_create_requirements(items=[
    {"framework_id": "<fw-uuid>", "section_id": "<a5-uuid>", "requirement_number": "A.5.1", "name": "Policies for information security", "description": "A set of policies for information security shall be defined, approved by management, published, communicated to and acknowledged by relevant personnel and relevant interested parties.", "type": "mandatory", "linked_risks": []},
    ...93 requirements total...
  ])

### Step 2: Create and run the assessment
  create_compliance_assessment(name="Annual ISO 27001 Audit 2025", framework_ids=["<fw-uuid>"], assessor_id="<auditor-uuid>", status="draft")
  -> auto-creates 93 assessment_results (one per requirement)

  update_compliance_assessment(id="<assess-uuid>", status="planned", assessment_start_date="2025-04-01", assessment_end_date="2025-04-30")
  update_compliance_assessment(id="<assess-uuid>", status="in_progress")

### Step 3: Record assessment results
  list_assessment_results(assessment_id="<assess-uuid>", limit=100)
  -> returns 93 results, each with requirement_id and status "not_assessed"

  For each requirement, update its result:
  update_assessment_result(id="<result-uuid>", compliance_status="compliant", evidence="<p>Policy document v3.2 reviewed. Last update: 2025-01-15.</p>")

  For non-conformities, create findings:
  create_finding(assessment_id="<assess-uuid>", finding_type="major_nc", description="<p>No documented policy for mobile device management.</p>", evidence="<p>Interview with IT manager confirmed no policy exists.</p>", recommendation="<p>Draft and approve a mobile device policy within 30 days.</p>", requirement_ids=["<req-a5.1-uuid>"])

### Step 4: Create remediation action plans
  create_action_plan(name="Draft mobile device policy", gap_description="<p>No documented mobile device management policy.</p>", remediation_plan="<p>1. Draft policy based on ISO 27001 A.8.1<br>2. Review with CISO<br>3. Approve and publish</p>", priority="high", owner_id="<ciso-uuid>", target_date="2025-05-30", requirements=["<req-a5.1-uuid>"])

  action_plan_transition(action_plan_id="<ap-uuid>", target_status="to_define")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="to_validate")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="to_implement")
  update_action_plan(id="<ap-uuid>", progress_percentage=100)
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="implementation_to_validate")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="validated")
  action_plan_transition(action_plan_id="<ap-uuid>", target_status="closed")

### Step 5: Finalize
  update_compliance_assessment(id="<assess-uuid>", status="completed")
  generate_audit_report(assessment_id="<assess-uuid>", title="ISO 27001 Audit Report 2025")
  update_compliance_assessment(id="<assess-uuid>", status="closed")

## Example 2: Full risk assessment workflow

### Step 1: Define risk criteria
  create_risk_criteria(name="Standard 5x5 Matrix", methodology="iso27005", status="active")

  batch_create_scale_levels(items=[
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 1, "name": "Very Low", "description": "Less than once every 5 years", "color": "#4caf50"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 2, "name": "Low", "description": "Once every 2-5 years", "color": "#8bc34a"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 3, "name": "Medium", "description": "Once per year", "color": "#ff9800"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 4, "name": "High", "description": "Once per quarter", "color": "#f44336"},
    {"criteria_id": "<rc-uuid>", "scale_type": "likelihood", "level": 5, "name": "Very High", "description": "Monthly or more", "color": "#b71c1c"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 1, "name": "Negligible", "color": "#4caf50"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 2, "name": "Minor", "color": "#8bc34a"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 3, "name": "Moderate", "color": "#ff9800"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 4, "name": "Major", "color": "#f44336"},
    {"criteria_id": "<rc-uuid>", "scale_type": "impact", "level": 5, "name": "Catastrophic", "color": "#b71c1c"}
  ])

  batch_create_risk_levels(items=[
    {"criteria_id": "<rc-uuid>", "level": 1, "name": "Low", "color": "#4caf50", "min_score": 1, "max_score": 5, "treatment_required": false},
    {"criteria_id": "<rc-uuid>", "level": 2, "name": "Medium", "color": "#ff9800", "min_score": 6, "max_score": 12, "treatment_required": true},
    {"criteria_id": "<rc-uuid>", "level": 3, "name": "High", "color": "#f44336", "min_score": 13, "max_score": 19, "treatment_required": true},
    {"criteria_id": "<rc-uuid>", "level": 4, "name": "Critical", "color": "#b71c1c", "min_score": 20, "max_score": 25, "treatment_required": true}
  ])

### Step 2: Create assessment and risks
  create_risk_assessment(name="Annual Risk Assessment 2025", risk_criteria_id="<rc-uuid>", methodology="iso27005", status="in_progress", assessor_id="<user-uuid>")

  batch_create_risks(items=[
    {"assessment_id": "<ra-uuid>", "name": "Ransomware encrypts production data", "status": "identified", "priority": "critical", "initial_likelihood": 4, "initial_impact": 5, "current_likelihood": 3, "current_impact": 5, "treatment_decision": "mitigate", "risk_owner_id": "<ciso-uuid>"},
    {"assessment_id": "<ra-uuid>", "name": "Employee data leak via phishing", "status": "identified", "priority": "high", "initial_likelihood": 4, "initial_impact": 4, "current_likelihood": 3, "current_impact": 4, "treatment_decision": "mitigate"},
    {"assessment_id": "<ra-uuid>", "name": "Power failure at primary DC", "status": "identified", "priority": "medium", "initial_likelihood": 2, "initial_impact": 4, "current_likelihood": 2, "current_impact": 2, "treatment_decision": "transfer"}
  ])

### Step 3: Create treatment plans
  create_risk_treatment_plan(name="Anti-ransomware measures", risk_id="<risk1-uuid>", owner_id="<it-uuid>", target_date="2025-09-30", status="planned")

  batch_create_treatment_actions(items=[
    {"treatment_plan_id": "<rtp-uuid>", "name": "Deploy EDR on all endpoints", "responsible_id": "<it-uuid>", "due_date": "2025-06-30", "status": "planned"},
    {"treatment_plan_id": "<rtp-uuid>", "name": "Implement immutable backups", "responsible_id": "<it-uuid>", "due_date": "2025-07-31", "status": "planned"},
    {"treatment_plan_id": "<rtp-uuid>", "name": "Conduct ransomware response drill", "responsible_id": "<ciso-uuid>", "due_date": "2025-09-15", "status": "planned"}
  ])

### Step 4: Link risks to requirements
  link_risk_requirements(risk_id="<risk1-uuid>", requirement_ids=["<req-a8.7-uuid>", "<req-a8.13-uuid>"])

### Step 5: Finalize
  update_risk_assessment(id="<ra-uuid>", status="completed")
  approve_risk_assessment(id="<ra-uuid>")
"""

    ALL_TOPICS = {
        "context": TOPIC_CONTEXT,
        "assets": TOPIC_ASSETS,
        "compliance": TOPIC_COMPLIANCE,
        "risks": TOPIC_RISKS,
        "batch": TOPIC_BATCH,
        "workflow": TOPIC_WORKFLOW,
        "permissions": TOPIC_PERMISSIONS,
        "examples": TOPIC_EXAMPLES,
    }

    def help_handler(user, arguments):
        topic = arguments.get("topic", "").strip().lower()
        if not topic:
            return HELP_TEXT

        result = ALL_TOPICS.get(topic)
        if not result:
            for key, value in ALL_TOPICS.items():
                if topic in key or key in topic:
                    result = value
                    break
        if not result:
            available = ", ".join(sorted(ALL_TOPICS.keys()))
            result = f"Unknown topic '{topic}'. Available topics: {available}\n\nCall help without a topic for the full guide."
        return result

    server.register_tool(
        "help",
        "Get usage documentation for the Fairway MCP server. "
        "Call without arguments for the full guide, or with a topic for focused help. "
        "Topics: context, assets, compliance, risks, batch, workflow, permissions, examples",
        {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic: context, assets, compliance, risks, batch, workflow, permissions, examples",
                },
            },
        },
        help_handler,
    )


# ── Context Module ─────────────────────────────────────────

def _register_context_tools(server):
    Scope = _get_model("context", "Scope")
    Issue = _get_model("context", "Issue")
    Stakeholder = _get_model("context", "Stakeholder")
    StakeholderExpectation = _get_model("context", "StakeholderExpectation")
    Objective = _get_model("context", "Objective")
    SwotAnalysis = _get_model("context", "SwotAnalysis")
    SwotItem = _get_model("context", "SwotItem")
    Role = _get_model("context", "Role")
    Responsibility = _get_model("context", "Responsibility")
    Activity = _get_model("context", "Activity")
    Site = _get_model("context", "Site")
    Indicator = _get_model("context", "Indicator")
    IndicatorMeasurement = _get_model("context", "IndicatorMeasurement")
    Tag = _get_model("context", "Tag")

    scope_fields = ["id", "reference", "name", "description", "status",
                    "effective_date", "review_date", "version", "is_approved", "created_at"]
    scope_writable = ["name", "description", "status", "effective_date",
                      "review_date", "parent_scope_id", "manager_ids"]

    _register_crud(server, "scope", Scope, "context.scope",
                   list_fields=scope_fields,
                   writable_fields=scope_writable,
                   search_fields=["name", "description"],
                   filters=["status"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "status": {
                           "type": "string",
                           "description": "Scope status.",
                           "enum": ["draft", "active", "archived"],
                       },
                       "effective_date": {"type": "string", "description": "Effective date (ISO 8601, e.g. 2025-01-15)"},
                       "review_date": {"type": "string", "description": "Review date (ISO 8601, e.g. 2025-06-15)"},
                       "manager_ids": {
                           "type": "array",
                           "items": {"type": "string"},
                           "description": "List of user UUIDs to assign as scope managers.",
                       },
                   },
                   m2m_fields={"manager_ids": "managers"})

    issue_fields = ["id", "reference", "name", "description", "type", "category",
                    "impact_level", "status", "is_approved", "created_at"]
    issue_writable = ["name", "description", "type", "category", "impact_level", "status"]

    _register_crud(server, "issue", Issue, "context.issue",
                   list_fields=issue_fields,
                   writable_fields=issue_writable,
                   search_fields=["name", "description"],
                   filters=["type", "category", "impact_level", "status"],
                   required_fields=["name", "type", "category", "impact_level"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Issue type.",
                           "enum": ["internal", "external"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Issue category.",
                           "enum": [
                               "strategic", "organizational", "human_resources",
                               "technical", "financial", "cultural",
                               "political", "economic", "social", "technological",
                               "legal", "environmental", "competitive", "regulatory",
                           ],
                       },
                       "impact_level": {
                           "type": "string",
                           "description": "Impact level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Issue status.",
                           "enum": ["identified", "active", "monitored", "closed"],
                       },
                   })

    stakeholder_fields = ["id", "reference", "name", "description", "type", "category",
                          "influence_level", "interest_level", "status", "is_approved",
                          "created_at"]
    stakeholder_writable = ["name", "description", "type", "category", "influence_level",
                            "interest_level", "status"]

    _register_crud(server, "stakeholder", Stakeholder, "context.stakeholder",
                   list_fields=stakeholder_fields,
                   writable_fields=stakeholder_writable,
                   search_fields=["name", "description"],
                   filters=["type", "category", "status"],
                   required_fields=["name", "type", "category", "influence_level", "interest_level"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Stakeholder type.",
                           "enum": ["internal", "external"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Stakeholder category.",
                           "enum": [
                               "executive_management", "employees", "customers",
                               "suppliers", "partners", "regulators", "shareholders",
                               "insurers", "public", "competitors", "unions",
                               "auditors", "other",
                           ],
                       },
                       "influence_level": {
                           "type": "string",
                           "description": "Influence level.",
                           "enum": ["low", "medium", "high"],
                       },
                       "interest_level": {
                           "type": "string",
                           "description": "Interest level.",
                           "enum": ["low", "medium", "high"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Stakeholder status.",
                           "enum": ["active", "inactive"],
                       },
                   })

    expectation_fields = ["id", "description", "type", "priority",
                          "stakeholder_id", "created_at"]
    expectation_writable = ["description", "type", "priority", "stakeholder_id"]

    _register_crud(server, "expectation", StakeholderExpectation, "context.expectation",
                   list_fields=expectation_fields,
                   writable_fields=expectation_writable,
                   search_fields=["description"],
                   filters=["stakeholder_id", "type"],
                   scope_filtered=False,
                   required_fields=["description", "type", "priority", "stakeholder_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Expectation type.",
                           "enum": ["requirement", "expectation", "need"],
                       },
                       "priority": {
                           "type": "string",
                           "description": "Priority level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                   })

    objective_fields = ["id", "reference", "name", "description", "category", "type",
                        "status", "target_date", "owner_id", "is_approved", "created_at"]
    objective_writable = ["name", "description", "category", "type", "status",
                          "target_date", "owner_id"]

    _register_crud(server, "objective", Objective, "context.objective",
                   list_fields=objective_fields,
                   writable_fields=objective_writable,
                   search_fields=["name", "description"],
                   filters=["category", "type", "status"],
                   required_fields=["name", "category", "type", "owner_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "owner_id": {"type": "string", "description": "UUID of the objective owner (user)"},
                       "category": {
                           "type": "string",
                           "description": "Objective category.",
                           "enum": [
                               "confidentiality", "integrity", "availability",
                               "compliance", "operational", "strategic",
                           ],
                       },
                       "type": {
                           "type": "string",
                           "description": "Objective type.",
                           "enum": ["security", "compliance", "business", "other"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Objective status.",
                           "enum": ["draft", "active", "achieved", "not_achieved", "cancelled"],
                       },
                       "target_date": {"type": "string", "description": "Target date (ISO 8601, e.g. 2025-12-31)"},
                   })

    swot_fields = ["id", "reference", "name", "description", "analysis_date",
                   "status", "is_approved", "created_at"]
    swot_writable = ["name", "description", "analysis_date", "status"]

    _register_crud(server, "swot_analysis", SwotAnalysis, "context.swot",
                   list_fields=swot_fields,
                   writable_fields=swot_writable,
                   search_fields=["name", "description"],
                   filters=["status"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "analysis_date": {"type": "string", "description": "Analysis date in ISO 8601 format (e.g. 2025-06-15)"},
                       "status": {
                           "type": "string",
                           "description": "SWOT analysis status.",
                           "enum": ["draft", "validated", "archived"],
                       },
                   })

    swot_item_fields = ["id", "quadrant", "description", "impact_level",
                        "order", "swot_analysis_id", "created_at"]
    swot_item_writable = ["quadrant", "description", "impact_level", "order",
                          "swot_analysis_id"]

    _register_crud(server, "swot_item", SwotItem, "context.swot",
                   list_fields=swot_item_fields,
                   writable_fields=swot_item_writable,
                   search_fields=["description"],
                   filters=["swot_analysis_id", "quadrant"],
                   scope_filtered=False,
                   required_fields=["quadrant", "description", "swot_analysis_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "quadrant": {
                           "type": "string",
                           "description": "SWOT quadrant.",
                           "enum": ["strength", "weakness", "opportunity", "threat"],
                       },
                       "impact_level": {
                           "type": "string",
                           "description": "Impact level.",
                           "enum": ["low", "medium", "high"],
                       },
                       "swot_analysis_id": {"type": "string", "description": "UUID of the parent SWOT analysis"},
                   })

    SwotStrategy = _get_model("context", "SwotStrategy")
    swot_strategy_fields = ["id", "quadrant", "description", "order",
                            "swot_analysis_id", "created_at"]
    swot_strategy_writable = ["quadrant", "description", "order",
                              "swot_analysis_id"]

    _register_crud(server, "swot_strategy", SwotStrategy, "context.swot",
                   list_fields=swot_strategy_fields,
                   writable_fields=swot_strategy_writable,
                   search_fields=["description"],
                   filters=["swot_analysis_id", "quadrant"],
                   scope_filtered=False,
                   required_fields=["quadrant", "description", "swot_analysis_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "quadrant": {
                           "type": "string",
                           "description": "Strategy quadrant.",
                           "enum": ["so", "st", "wo", "wt"],
                       },
                       "swot_analysis_id": {"type": "string", "description": "UUID of the parent SWOT analysis"},
                   })

    role_fields = ["id", "reference", "name", "description", "type", "status",
                   "is_approved", "created_at"]
    role_writable = ["name", "description", "type", "status"]

    _register_crud(server, "role", Role, "context.role",
                   list_fields=role_fields,
                   writable_fields=role_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   required_fields=["name", "type"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Role type.",
                           "enum": ["governance", "operational", "support", "control"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Role status.",
                           "enum": ["active", "inactive"],
                       },
                   })

    activity_fields = ["id", "reference", "name", "description", "type", "criticality",
                       "owner_id", "status", "is_approved", "created_at"]
    activity_writable = ["name", "description", "type", "criticality", "owner_id",
                         "status", "parent_activity_id"]

    _register_crud(server, "activity", Activity, "context.activity",
                   list_fields=activity_fields,
                   writable_fields=activity_writable,
                   search_fields=["name", "description"],
                   filters=["type", "criticality", "status"],
                   required_fields=["name", "type", "criticality", "owner_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "owner_id": {"type": "string", "description": "UUID of the activity owner (user)"},
                       "type": {
                           "type": "string",
                           "description": "Activity type.",
                           "enum": ["core_business", "support", "management"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Activity status.",
                           "enum": ["active", "inactive", "planned"],
                       },
                   })

    site_fields = ["id", "reference", "name", "description", "type", "status",
                   "address", "is_approved", "created_at"]
    site_writable = ["name", "description", "type", "status", "address",
                     "parent_site_id"]

    _register_crud(server, "site", Site, "context.site",
                   list_fields=site_fields,
                   writable_fields=site_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Site type.",
                           "enum": [
                               "siege", "bureau", "usine", "entrepot",
                               "datacenter", "site_distant", "autre",
                           ],
                       },
                       "status": {
                           "type": "string",
                           "description": "Site status.",
                           "enum": ["draft", "active", "archived"],
                       },
                   })

    # Tags (simple CRUD, no approve)
    server.register_tool(
        "list_tags",
        "List all tags",
        _list_schema({"search": {"type": "string"}}),
        require_perm("context.scope.read")(
            _list_handler(Tag, ["id", "name", "color", "created_at"], ["name"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "create_tag",
        "Create a tag",
        _obj_schema({"name": {"type": "string"}, "color": {"type": "string"}}, ["name"]),
        require_perm("context.scope.create")(
            _create_handler(Tag, ["name", "color"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "delete_tag",
        "Delete a tag",
        _id_schema(),
        require_perm("context.scope.delete")(
            _delete_handler(Tag, scope_filtered=False)
        ),
    )

    # Indicator (scoped, with approve)
    indicator_fields = ["id", "reference", "name", "description", "indicator_type",
                        "collection_method", "format", "unit", "current_value",
                        "expected_level", "critical_threshold_operator",
                        "critical_threshold_value", "critical_threshold_min",
                        "critical_threshold_max", "review_frequency",
                        "first_review_date", "status", "is_internal",
                        "internal_source", "internal_source_parameter",
                        "is_approved", "created_at"]
    indicator_writable = ["name", "description", "indicator_type", "collection_method",
                          "format", "unit", "expected_level",
                          "critical_threshold_operator", "critical_threshold_value",
                          "critical_threshold_min", "critical_threshold_max",
                          "review_frequency", "first_review_date", "status",
                          "is_internal", "internal_source", "internal_source_parameter"]

    _register_crud(server, "indicator", Indicator, "context.indicator",
                   list_fields=indicator_fields,
                   writable_fields=indicator_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["indicator_type", "status", "format", "collection_method"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "indicator_type": {
                           "type": "string",
                           "description": "Indicator type.",
                           "enum": ["organizational", "technical"],
                       },
                       "collection_method": {
                           "type": "string",
                           "description": "Data collection method.",
                           "enum": ["manual", "api", "internal"],
                       },
                       "format": {
                           "type": "string",
                           "description": "Indicator format.",
                           "enum": ["number", "boolean"],
                       },
                       "review_frequency": {
                           "type": "string",
                           "description": "Review frequency.",
                           "enum": ["daily", "weekly", "monthly", "quarterly", "semi_annual", "annual"],
                       },
                       "critical_threshold_operator": {
                           "type": "string",
                           "description": "Critical threshold operator.",
                           "enum": ["below", "above", "is_false", "is_true"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Indicator status.",
                           "enum": ["active", "inactive", "draft"],
                       },
                       "is_internal": {"type": "boolean", "description": "Whether this is an internal predefined indicator."},
                       "internal_source": {
                           "type": "string",
                           "description": "Predefined indicator source (only for internal indicators).",
                           "enum": [
                               "global_compliance_rate", "framework_compliance_rate",
                               "objective_progress", "risk_treatment_rate",
                               "approved_scopes_rate", "mandatory_roles_coverage",
                           ],
                       },
                   })

    # Indicator measurements (child of Indicator, no approve)
    measurement_fields = ["id", "indicator_id", "value", "recorded_at",
                          "recorded_by_id", "notes"]
    measurement_writable = ["indicator_id", "value", "notes"]

    _register_crud(server, "indicator_measurement", IndicatorMeasurement,
                   "context.indicator",
                   list_fields=measurement_fields,
                   writable_fields=measurement_writable,
                   search_fields=["notes"],
                   filters=["indicator_id"],
                   scope_filtered=False,
                   has_approve=False)

    # Responsibility (child of Role, no approve)
    responsibility_fields = ["id", "role_id", "description", "raci_type",
                             "related_activity_id", "created_at"]
    responsibility_writable = ["role_id", "description", "raci_type",
                               "related_activity_id"]

    _register_crud(server, "responsibility", Responsibility, "context.role",
                   list_fields=responsibility_fields,
                   writable_fields=responsibility_writable,
                   search_fields=["description"],
                   filters=["role_id", "raci_type"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["role_id", "description", "raci_type"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "raci_type": {
                           "type": "string",
                           "description": "RACI responsibility type.",
                           "enum": ["responsible", "accountable", "consulted", "informed"],
                       },
                   })


# ── Assets Module ──────────────────────────────────────────

def _register_assets_tools(server):
    EssentialAsset = _get_model("assets", "EssentialAsset")
    SupportAsset = _get_model("assets", "SupportAsset")
    AssetDependency = _get_model("assets", "AssetDependency")
    AssetGroup = _get_model("assets", "AssetGroup")
    Supplier = _get_model("assets", "Supplier")
    SupplierDependency = _get_model("assets", "SupplierDependency")
    SiteAssetDependency = _get_model("assets", "SiteAssetDependency")
    SiteSupplierDependency = _get_model("assets", "SiteSupplierDependency")
    AssetValuation = _get_model("assets", "AssetValuation")
    SupplierType = _get_model("assets", "SupplierType")
    SupplierTypeRequirement = _get_model("assets", "SupplierTypeRequirement")
    SupplierRequirement = _get_model("assets", "SupplierRequirement")
    SupplierRequirementReview = _get_model("assets", "SupplierRequirementReview")

    ea_fields = ["id", "reference", "name", "description", "type", "category",
                 "status", "confidentiality_level", "integrity_level",
                 "availability_level", "personal_data", "is_approved", "created_at"]
    ea_writable = ["name", "description", "type", "category", "status",
                   "confidentiality_level", "integrity_level", "availability_level",
                   "personal_data", "owner_id", "custodian_id"]

    _register_crud(server, "essential_asset", EssentialAsset, "assets.essential_asset",
                   list_fields=ea_fields,
                   writable_fields=ea_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["type", "category", "status"],
                   required_fields=["name", "type", "category", "owner_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Essential asset type.",
                           "enum": ["business_process", "information"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Essential asset category.",
                           "enum": [
                               "core_process", "support_process", "management_process",
                               "strategic_data", "operational_data", "personal_data",
                               "financial_data", "technical_data", "legal_data",
                               "research_data", "commercial_data",
                           ],
                       },
                       "status": {
                           "type": "string",
                           "description": "Essential asset status.",
                           "enum": ["identified", "active", "under_review", "decommissioned"],
                       },
                       "confidentiality_level": {
                           "type": ["integer", "string"],
                           "description": "Confidentiality level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2.",
                       },
                       "integrity_level": {
                           "type": ["integer", "string"],
                           "description": "Integrity level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2.",
                       },
                       "availability_level": {
                           "type": ["integer", "string"],
                           "description": "Availability level. Accepts integers (0-4) or text labels: 0/negligible, 1/low, 2/medium, 3/high, 4/critical. Default: 2.",
                       },
                       "personal_data": {
                           "type": "boolean",
                           "description": "Whether this asset contains personal data.",
                       },
                       "owner_id": {"type": "string", "description": "UUID of the asset owner (user)"},
                       "custodian_id": {"type": "string", "description": "UUID of the asset custodian (user)"},
                   })

    sa_fields = ["id", "reference", "name", "description", "type", "category",
                 "status", "hostname", "ip_address",
                 "inherited_confidentiality", "inherited_integrity",
                 "inherited_availability", "end_of_life_date", "is_approved", "created_at"]
    sa_writable = ["name", "description", "type", "category", "status",
                   "hostname", "ip_address", "end_of_life_date",
                   "owner_id", "custodian_id", "parent_asset_id"]

    _register_crud(server, "support_asset", SupportAsset, "assets.support_asset",
                   list_fields=sa_fields,
                   writable_fields=sa_writable,
                   search_fields=["reference", "name", "description", "hostname", "ip_address"],
                   filters=["type", "category", "status"],
                   required_fields=["name", "type", "category", "owner_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Support asset type.",
                           "enum": ["hardware", "software", "network", "person", "site", "service", "paper"],
                       },
                       "category": {
                           "type": "string",
                           "description": (
                               "Support asset category. Must match the type. "
                               "Hardware: server, workstation, laptop, mobile_device, network_equipment, storage, peripheral, iot_device, removable_media, other_hardware. "
                               "Software: operating_system, database, application, middleware, security_tool, development_tool, saas_application, other_software. "
                               "Network: lan, wan, wifi, vpn, internet_link, firewall_zone, dmz, other_network. "
                               "Person: internal_staff, contractor, external_provider, administrator, developer, other_person. "
                               "Site: datacenter, office, remote_site, cloud_region, other_site. "
                               "Service: cloud_service, hosting_service, managed_service, telecom_service, outsourced_service, other_service. "
                               "Paper: archive, printed_document, form, other_paper."
                           ),
                       },
                       "status": {
                           "type": "string",
                           "description": "Support asset status.",
                           "enum": ["in_stock", "deployed", "active", "under_maintenance", "decommissioned", "disposed"],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the asset owner (user)"},
                       "custodian_id": {"type": "string", "description": "UUID of the asset custodian (user)"},
                   })

    dep_fields = ["id", "essential_asset_id", "support_asset_id", "dependency_type",
                  "criticality", "is_single_point_of_failure", "created_at"]
    dep_writable = ["essential_asset_id", "support_asset_id", "dependency_type",
                    "criticality", "description"]

    _register_crud(server, "asset_dependency", AssetDependency, "assets.dependency",
                   list_fields=dep_fields,
                   writable_fields=dep_writable,
                   search_fields=[],
                   filters=["essential_asset_id", "support_asset_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["essential_asset_id", "support_asset_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of dependency between essential and support asset.",
                           "enum": ["runs_on", "stored_in", "transmitted_by", "managed_by", "hosted_at", "protected_by", "other"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                   })

    ag_fields = ["id", "name", "description", "type", "status", "is_approved", "created_at"]
    ag_writable = ["name", "description", "type", "status", "owner_id"]

    _register_crud(server, "asset_group", AssetGroup, "assets.group",
                   list_fields=ag_fields,
                   writable_fields=ag_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "status": {
                           "type": "string",
                           "description": "Asset group status.",
                           "enum": ["active", "inactive"],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the group owner (user)"},
                   })

    sup_fields = ["id", "reference", "name", "description", "type", "criticality",
                  "status", "contact_name", "contact_email", "contact_phone",
                  "website", "address", "country",
                  "contract_reference", "contract_start_date", "contract_end_date",
                  "logo", "logo_16", "logo_32", "logo_64",
                  "notes", "is_approved", "created_at"]
    sup_writable = ["name", "description", "type", "criticality", "status",
                    "contact_name", "contact_email", "contact_phone",
                    "website", "address", "country",
                    "contract_reference", "contract_start_date", "contract_end_date",
                    "notes", "owner_id"]

    _sup_field_overrides = {
        "description": _html_field("Description"),
        "notes": _html_field("Notes"),
        "type": {"type": "integer", "description": "ID of a SupplierType. Use list_supplier_types to get valid IDs."},
        "criticality": {
            "type": "string",
            "description": "Supplier criticality.",
            "enum": ["low", "medium", "high", "critical"],
        },
        "status": {
            "type": "string",
            "description": "Supplier status.",
            "enum": ["active", "under_evaluation", "suspended", "archived"],
        },
        "owner_id": {"type": "string", "description": "UUID of the supplier owner (user)"},
    }

    _register_crud(server, "supplier", Supplier, "assets.supplier",
                   list_fields=sup_fields,
                   writable_fields=sup_writable,
                   search_fields=["reference", "name", "description", "contact_name"],
                   filters=["type", "criticality", "status"],
                   required_fields=["name", "owner_id"],
                   field_overrides=_sup_field_overrides)

    # Custom tool: update supplier logo with automatic variant generation
    server.register_tool(
        "update_supplier_logo",
        "Update a supplier's logo. Provide EITHER a base64 data URI via 'logo' OR a public "
        "image URL via 'image_url'. The image is resized to 128x128 and 64x64, 32x32, 16x16 "
        "variants are generated automatically.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "UUID of the supplier"},
                "logo": {"type": "string", "description": "Base64 data URI of the logo image (e.g. 'data:image/png;base64,...')"},
                "image_url": {"type": "string", "description": "Public URL of an image to download as the logo"},
            },
            "required": ["id"],
        },
        require_perm("assets.supplier.update")(
            _update_supplier_logo_handler
        ),
    )

    # Override create_supplier to support image_url
    create_sup_props = {f: _sup_field_overrides.get(f, {"type": "string", "description": f}) for f in sup_writable}
    create_sup_props["image_url"] = {
        "type": "string",
        "description": "Public URL of an image to use as the supplier logo (PNG, JPG, WebP, etc.). "
                       "The image is downloaded, resized to 128x128, and size variants are generated.",
    }
    server.register_tool(
        "create_supplier",
        "Create a new supplier. Optionally provide 'image_url' (a public URL pointing to an "
        "image file) to set the supplier logo. The image will be downloaded, resized to 128x128, "
        "and 64x64, 32x32, 16x16 variants will be generated automatically. "
        "Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL.",
        _obj_schema(create_sup_props),
        require_perm("assets.supplier.create")(
            _create_supplier_handler(Supplier, sup_writable)
        ),
    )

    # Override update_supplier to support image_url
    update_sup_props = {"id": {"type": "string", "description": "UUID of the object to update"}}
    for f in sup_writable:
        update_sup_props[f] = _sup_field_overrides.get(f, {"type": "string", "description": f})
    update_sup_props["image_url"] = {
        "type": "string",
        "description": "Public URL of an image to use as the supplier logo (PNG, JPG, WebP, etc.). "
                       "The image is downloaded, resized to 128x128, and size variants are generated.",
    }
    server.register_tool(
        "update_supplier",
        "Update an existing supplier. Optionally provide 'image_url' (a public URL pointing to "
        "an image file) to set or replace the supplier logo. The image will be downloaded, "
        "resized to 128x128, and 64x64, 32x32, 16x16 variants will be generated automatically. "
        "Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL.",
        _obj_schema(update_sup_props, ["id"]),
        require_perm("assets.supplier.update")(
            _update_supplier_with_logo_handler(Supplier, sup_writable)
        ),
    )

    sd_fields = ["id", "support_asset_id", "supplier_id", "dependency_type",
                 "criticality", "created_at"]
    sd_writable = ["support_asset_id", "supplier_id", "dependency_type",
                   "criticality", "description"]

    _register_crud(server, "supplier_dependency", SupplierDependency, "assets.supplier_dependency",
                   list_fields=sd_fields,
                   writable_fields=sd_writable,
                   search_fields=[],
                   filters=["support_asset_id", "supplier_id"],
                   scope_filtered=False,
                   required_fields=["support_asset_id", "supplier_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of supplier dependency.",
                           "enum": [
                               "provides", "hosts", "manages",
                               "develops", "supports", "licenses", "maintains", "other",
                           ],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                   })

    # Site-asset dependencies (has approve)
    sad_fields = ["id", "reference", "support_asset_id", "site_id", "dependency_type",
                  "criticality", "description", "is_single_point_of_failure",
                  "redundancy_level", "is_approved", "created_at"]
    sad_writable = ["support_asset_id", "site_id", "dependency_type", "criticality",
                    "description", "is_single_point_of_failure", "redundancy_level"]

    _register_crud(server, "site_asset_dependency", SiteAssetDependency, "assets.dependency",
                   list_fields=sad_fields,
                   writable_fields=sad_writable,
                   search_fields=["description"],
                   filters=["support_asset_id", "site_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["support_asset_id", "site_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of site-asset dependency.",
                           "enum": ["located_at", "hosted_at", "deployed_at", "other"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "redundancy_level": {
                           "type": "string",
                           "description": "Redundancy level.",
                           "enum": ["none", "partial", "full"],
                       },
                       "is_single_point_of_failure": {
                           "type": "boolean",
                           "description": "Whether this is a single point of failure.",
                       },
                   })

    # Site-supplier dependencies (has approve)
    ssd_fields = ["id", "reference", "site_id", "supplier_id", "dependency_type",
                  "criticality", "description", "is_single_point_of_failure",
                  "redundancy_level", "is_approved", "created_at"]
    ssd_writable = ["site_id", "supplier_id", "dependency_type", "criticality",
                    "description", "is_single_point_of_failure", "redundancy_level"]

    _register_crud(server, "site_supplier_dependency", SiteSupplierDependency,
                   "assets.supplier_dependency",
                   list_fields=ssd_fields,
                   writable_fields=ssd_writable,
                   search_fields=["description"],
                   filters=["site_id", "supplier_id", "dependency_type", "criticality"],
                   scope_filtered=False,
                   required_fields=["site_id", "supplier_id", "dependency_type", "criticality"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "dependency_type": {
                           "type": "string",
                           "description": "Type of site-supplier dependency.",
                           "enum": ["provides", "hosts", "manages", "develops", "supports", "licenses", "maintains", "other"],
                       },
                       "criticality": {
                           "type": "string",
                           "description": "Criticality level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "redundancy_level": {
                           "type": "string",
                           "description": "Redundancy level.",
                           "enum": ["none", "partial", "full"],
                       },
                       "is_single_point_of_failure": {
                           "type": "boolean",
                           "description": "Whether this is a single point of failure.",
                       },
                   })

    # Asset valuations (no approve)
    av_fields = ["id", "essential_asset_id", "evaluation_date",
                 "confidentiality_level", "integrity_level", "availability_level",
                 "evaluated_by_id", "justification", "context", "created_at"]
    av_writable = ["essential_asset_id", "evaluation_date",
                   "confidentiality_level", "integrity_level", "availability_level",
                   "evaluated_by_id", "justification", "context"]

    _register_crud(server, "asset_valuation", AssetValuation,
                   "assets.essential_asset",
                   list_fields=av_fields,
                   writable_fields=av_writable,
                   search_fields=["justification"],
                   filters=["essential_asset_id"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["essential_asset_id"],
                   field_overrides={
                       "justification": _html_field("Justification"),
                       "context": _html_field("Context"),
                       "confidentiality_level": {
                           "type": "integer",
                           "description": "Confidentiality level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).",
                           "enum": [0, 1, 2, 3, 4],
                       },
                       "integrity_level": {
                           "type": "integer",
                           "description": "Integrity level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).",
                           "enum": [0, 1, 2, 3, 4],
                       },
                       "availability_level": {
                           "type": "integer",
                           "description": "Availability level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).",
                           "enum": [0, 1, 2, 3, 4],
                       },
                       "evaluation_date": {"type": "string", "description": "Evaluation date (ISO 8601, e.g. 2025-01-15)"},
                       "evaluated_by_id": {"type": "string", "description": "UUID of the evaluator (user)"},
                   })

    # Supplier types (config, no approve)
    st_fields = ["id", "name", "description", "created_at"]
    st_writable = ["name", "description"]

    _register_crud(server, "supplier_type", SupplierType, "assets.config",
                   list_fields=st_fields,
                   writable_fields=st_writable,
                   search_fields=["name", "description"],
                   filters=[],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides=_HTML_DESC)

    # Supplier type requirements (config, no approve)
    str_fields = ["id", "supplier_type_id", "title", "description", "created_at"]
    str_writable = ["supplier_type_id", "title", "description"]

    _register_crud(server, "supplier_type_requirement", SupplierTypeRequirement,
                   "assets.config",
                   list_fields=str_fields,
                   writable_fields=str_writable,
                   search_fields=["title", "description"],
                   filters=["supplier_type_id"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides=_HTML_DESC)

    # Supplier requirements (no approve)
    sr_fields = ["id", "supplier_id", "source_type_requirement_id", "requirement_id",
                 "title", "description", "compliance_status", "evidence",
                 "due_date", "verified_at", "verified_by_id", "created_at"]
    sr_writable = ["supplier_id", "source_type_requirement_id", "requirement_id",
                   "title", "description", "compliance_status", "evidence", "due_date"]

    _register_crud(server, "supplier_requirement", SupplierRequirement,
                   "assets.supplier",
                   list_fields=sr_fields,
                   writable_fields=sr_writable,
                   search_fields=["title", "description"],
                   filters=["supplier_id", "compliance_status"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["supplier_id", "title"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "evidence": _html_field("Evidence"),
                       "compliance_status": {
                           "type": "string",
                           "description": "Compliance status of the supplier requirement.",
                           "enum": ["not_assessed", "compliant", "partially_compliant", "non_compliant"],
                       },
                   })

    # Supplier requirement reviews (no approve)
    srr_fields = ["id", "supplier_requirement_id", "review_date", "reviewer_id",
                  "result", "comment", "created_at"]
    srr_writable = ["supplier_requirement_id", "review_date", "reviewer_id",
                    "result", "comment"]

    _register_crud(server, "supplier_requirement_review", SupplierRequirementReview,
                   "assets.supplier",
                   list_fields=srr_fields,
                   writable_fields=srr_writable,
                   search_fields=["comment"],
                   filters=["supplier_requirement_id", "result"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides={
                       "comment": _html_field("Comment"),
                   })


# ── Compliance Module ──────────────────────────────────────

def _register_compliance_tools(server):
    Framework = _get_model("compliance", "Framework")
    Section = _get_model("compliance", "Section")
    Requirement = _get_model("compliance", "Requirement")
    ComplianceAssessment = _get_model("compliance", "ComplianceAssessment")
    AssessmentResult = _get_model("compliance", "AssessmentResult")
    RequirementMapping = _get_model("compliance", "RequirementMapping")
    ComplianceActionPlan = _get_model("compliance", "ComplianceActionPlan")

    fw_fields = ["id", "reference", "name", "short_name", "description", "type",
                 "category", "compliance_level", "status", "logo_32",
                 "is_approved", "created_at"]
    fw_writable = ["name", "short_name", "description", "type", "category", "status",
                   "owner_id", "logo"]

    _register_crud(server, "framework", Framework, "compliance.framework",
                   list_fields=fw_fields,
                   writable_fields=fw_writable,
                   search_fields=["reference", "name", "short_name", "description"],
                   filters=["type", "category", "status"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Framework type.",
                           "enum": [
                               "standard", "law", "regulation", "contract",
                               "internal_policy", "industry_framework", "other",
                           ],
                       },
                       "category": {
                           "type": "string",
                           "description": "Framework category.",
                           "enum": [
                               "information_security", "privacy", "risk_management",
                               "business_continuity", "cloud_security", "sector_specific",
                               "it_governance", "quality", "contractual", "internal", "other",
                           ],
                       },
                       "status": {
                           "type": "string",
                           "description": "Framework status.",
                           "enum": ["draft", "active", "under_review", "deprecated", "archived"],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the framework owner (user)"},
                   })

    # Framework compliance summary (special tool)
    @require_perm("compliance.framework.read")
    def framework_compliance_summary(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            framework = Framework.objects.get(pk=pk)
        except Framework.DoesNotExist:
            return _error("Framework not found.")
        sections = framework.sections.filter(parent_section__isnull=True)
        section_data = [{
            "id": str(s.id), "reference": s.reference,
            "name": s.name, "compliance_level": float(s.compliance_level),
        } for s in sections]
        reqs = framework.requirements.filter(is_applicable=True)
        by_status = {}
        for req in reqs.values("compliance_status"):
            st = req["compliance_status"]
            by_status[st] = by_status.get(st, 0) + 1
        return {
            "compliance_level": float(framework.compliance_level),
            "sections": section_data,
            "by_status": by_status,
            "total_requirements": reqs.count(),
        }

    server.register_tool(
        "get_framework_compliance_summary",
        "Get compliance summary for a framework, including section-level compliance and status distribution",
        _id_schema(),
        framework_compliance_summary,
    )

    sec_fields = ["id", "reference", "name", "description", "order", "compliance_level",
                  "framework_id", "parent_section_id", "created_at"]
    sec_writable = ["name", "description", "order", "framework_id", "parent_section_id"]

    _register_crud(server, "section", Section, "compliance.section",
                   list_fields=sec_fields,
                   writable_fields=sec_writable,
                   search_fields=["reference", "name"],
                   filters=["framework_id", "parent_section_id"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["name", "framework_id"],
                   field_overrides=_HTML_DESC)

    req_fields = ["id", "reference", "requirement_number", "name", "description", "type",
                  "compliance_status", "compliance_level", "priority", "is_applicable",
                  "framework_id", "section_id", "is_approved", "created_at"]
    req_writable = ["requirement_number", "name", "description", "guidance", "type",
                    "compliance_status", "compliance_level",
                    "priority", "is_applicable", "compliance_evidence", "compliance_finding",
                    "framework_id", "section_id", "owner_id"]

    _register_crud(server, "requirement", Requirement, "compliance.requirement",
                   list_fields=req_fields,
                   writable_fields=req_writable,
                   search_fields=["reference", "requirement_number", "name", "description"],
                   filters=["framework_id", "section_id", "compliance_status", "type", "priority"],
                   scope_filtered=False,
                   required_fields=["name", "description", "type", "framework_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "guidance": _html_field("Implementation recommendations"),
                       "compliance_evidence": _html_field("Compliance evidence"),
                       "compliance_finding": _html_field("Finding"),
                       "type": {
                           "type": "string",
                           "description": "Requirement type.",
                           "enum": ["mandatory", "recommended", "optional"],
                       },
                       "compliance_status": {
                           "type": "string",
                           "description": "Compliance status.",
                           "enum": [
                               "not_assessed", "evaluated",
                               "non_compliant", "partially_compliant",
                               "major_non_conformity", "minor_non_conformity",
                               "observation", "improvement_opportunity",
                               "compliant", "strength", "not_applicable",
                           ],
                       },
                       "priority": {
                           "type": "string",
                           "description": "Priority level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "is_applicable": {
                           "type": "boolean",
                           "description": "Whether this requirement is applicable.",
                       },
                       "owner_id": {"type": "string", "description": "UUID of the requirement owner (user)"},
                   })

    ca_fields = ["id", "name", "description", "limitations",
                 "assessment_start_date", "assessment_end_date", "status",
                 "overall_compliance_level", "total_requirements",
                 "compliant_count", "major_non_conformity_count",
                 "minor_non_conformity_count", "observation_count",
                 "improvement_opportunity_count", "strength_count",
                 "not_applicable_count",
                 "is_approved", "created_at"]
    ca_writable = ["name", "description", "limitations",
                   "assessment_start_date", "assessment_end_date",
                   "status", "assessor_id"]

    # Use generic list/get/delete/approve for compliance_assessment
    ca_filter_props = {"status": {"type": "string", "description": "Filter by status"}}
    server.register_tool(
        "list_compliance_assessments",
        "List compliance assessments with optional search and filters",
        _list_schema(ca_filter_props),
        require_perm("compliance.assessment.read")(
            _list_handler(ComplianceAssessment, ca_fields, ["name", "description"], ["status"])
        ),
    )
    server.register_tool(
        "get_compliance_assessment",
        "Get a compliance assessment by ID",
        _id_schema(),
        require_perm("compliance.assessment.read")(
            _get_handler(ComplianceAssessment, ca_fields)
        ),
    )
    server.register_tool(
        "delete_compliance_assessment",
        "Delete a compliance assessment",
        _id_schema(),
        require_perm("compliance.assessment.delete")(
            _delete_handler(ComplianceAssessment)
        ),
    )
    server.register_tool(
        "approve_compliance_assessment",
        "Approve a compliance assessment",
        _id_schema(),
        require_perm("compliance.assessment.approve")(
            _approve_handler(ComplianceAssessment)
        ),
    )

    # Custom create handler with framework_ids M2M support
    def _create_compliance_assessment(user, arguments):
        """Create a new compliance assessment, optionally linking frameworks.

        Parameters
        ----------
        name : str (required)
            Assessment name.
        description : str
            Context and objectives (HTML rich text).
        limitations : str
            Limitations (HTML rich text).
        assessment_start_date : str
            Start date (ISO 8601).
        assessment_end_date : str
            End date (ISO 8601).
        status : str
            Assessment status (draft, planned, in_progress, completed, closed).
        assessor_id : str
            UUID of the lead assessor.
        framework_ids : list[str]
            List of framework UUIDs to link. Assessment results will be
            automatically created for all requirements in these frameworks.
        """
        framework_ids = arguments.pop("framework_ids", None)
        kwargs = {}
        for field_name in ca_writable:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    ComplianceAssessment, field_name, arguments[field_name])
        kwargs["created_by"] = user
        try:
            obj = ComplianceAssessment(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if framework_ids:
            frameworks = Framework.objects.filter(pk__in=framework_ids)
            if frameworks.count() != len(framework_ids):
                found = set(str(f.pk) for f in frameworks)
                missing = [fid for fid in framework_ids if fid not in found]
                return _error(f"Frameworks not found: {missing}")
            obj.frameworks.set(frameworks)
            obj.sync_results(user)
        fields = [f.name for f in ComplianceAssessment._meta.fields]
        return _serialize_obj(obj, fields)

    ca_create_props = {}
    for f in ca_writable:
        ca_create_props[f] = _HTML_DESC.get(f, {"type": "string", "description": f})
    ca_create_props["framework_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of framework UUIDs to link to this assessment",
    }
    server.register_tool(
        "create_compliance_assessment",
        "Create a new compliance assessment",
        _obj_schema(ca_create_props),
        require_perm("compliance.assessment.create")(_create_compliance_assessment),
    )

    # Custom update handler with framework_ids M2M support
    def _update_compliance_assessment(user, arguments):
        """Update a compliance assessment, optionally changing linked frameworks.

        Parameters
        ----------
        id : str (required)
            UUID of the assessment to update.
        framework_ids : list[str]
            Replace the linked frameworks. Assessment results are
            automatically synced (created / removed) to match.

        All other writable fields (name, description, etc.) are optional.
        """
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = ComplianceAssessment.objects.get(pk=pk)
        except ComplianceAssessment.DoesNotExist:
            return _error("ComplianceAssessment not found.")
        qs = _filter_by_scopes(ComplianceAssessment.objects.filter(pk=pk), user)
        if not qs.exists():
            return _error("Access denied: object is outside your allowed scopes.")
        framework_ids = arguments.pop("framework_ids", None)
        new_status = arguments.pop("status", None)
        changed_fields = set()
        for field_name in ca_writable:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    ComplianceAssessment, field_name, arguments[field_name]))
                changed_fields.add(field_name)
        if hasattr(obj, "is_approved") and hasattr(obj, "version"):
            from core.models import VersioningConfig
            if VersioningConfig.is_approval_enabled(ComplianceAssessment):
                major_fields = VersioningConfig.get_major_fields(ComplianceAssessment)
                is_major = major_fields is None or bool(changed_fields & major_fields)
                if is_major:
                    obj.is_approved = False
                    obj.approved_by = None
                    obj.approved_at = None
                    obj.version = (obj.version or 0) + 1
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        # Use transition_to() for status changes to enforce workflow rules
        # and trigger side-effects (e.g. reset EVALUATED on COMPLETED)
        if new_status and new_status != obj.status:
            try:
                obj.transition_to(new_status)
            except ValueError as e:
                return _error(str(e))
        if framework_ids is not None:
            frameworks = Framework.objects.filter(pk__in=framework_ids)
            if frameworks.count() != len(framework_ids):
                found = set(str(f.pk) for f in frameworks)
                missing = [fid for fid in framework_ids if fid not in found]
                return _error(f"Frameworks not found: {missing}")
            obj.frameworks.set(frameworks)
            obj.sync_results(user)
        fields = [f.name for f in ComplianceAssessment._meta.fields]
        return _serialize_obj(obj, fields)

    ca_update_props = {"id": {"type": "string", "description": "UUID of the assessment to update"}}
    for f in ca_writable:
        ca_update_props[f] = _HTML_DESC.get(f, {"type": "string", "description": f})
    ca_update_props["framework_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of framework UUIDs to link (replaces existing links)",
    }
    server.register_tool(
        "update_compliance_assessment",
        "Update an existing compliance assessment",
        _obj_schema(ca_update_props, ["id"]),
        require_perm("compliance.assessment.update")(_update_compliance_assessment),
    )

    ar_fields = ["id", "assessment_id", "requirement_id", "compliance_status",
                 "compliance_level", "finding", "auditor_recommendations",
                 "evidence", "assessed_by_id", "assessed_at"]
    ar_writable = ["assessment_id", "requirement_id", "compliance_status",
                   "compliance_level", "finding", "auditor_recommendations",
                   "evidence", "assessed_by_id", "assessed_at"]
    ar_overrides = {
        "finding": _html_field("Finding"),
        "auditor_recommendations": _html_field("Auditor recommendations"),
        "evidence": _html_field("Evidence"),
        "assessed_by_id": {"type": "string", "description": "UUID of the assessor (user)"},
        "assessed_at": {"type": "string", "description": "Assessment date-time in ISO 8601 format (e.g. 2025-01-15T10:30:00Z)"},
        "compliance_status": {
            "type": "string",
            "description": "Compliance status.",
            "enum": [
                "not_assessed", "evaluated", "major_non_conformity",
                "minor_non_conformity", "observation",
                "improvement_opportunity", "compliant", "strength",
                "not_applicable",
            ],
        },
    }

    # List and get use generic handlers (no side-effects needed)
    ar_filter_props = {
        "assessment_id": {"type": "string", "description": "Filter by assessment_id"},
        "requirement_id": {"type": "string", "description": "Filter by requirement_id"},
        "compliance_status": {"type": "string", "description": "Filter by compliance_status"},
    }
    server.register_tool(
        "list_assessment_results",
        "List assessment results with optional search and filters",
        _list_schema(ar_filter_props),
        require_perm("compliance.assessment.read")(
            _list_handler(AssessmentResult, ar_fields, [],
                          ["assessment_id", "requirement_id", "compliance_status"],
                          scope_filtered=False)
        ),
    )
    server.register_tool(
        "get_assessment_result",
        "Get an assessment result by ID",
        _id_schema(),
        require_perm("compliance.assessment.read")(
            _get_handler(AssessmentResult, ar_fields, scope_filtered=False)
        ),
    )

    # Custom create with recalculate_counts()
    def _create_assessment_result(user, arguments):
        kwargs = {}
        for field_name in ar_writable:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    AssessmentResult, field_name, arguments[field_name])
        try:
            obj = AssessmentResult(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        obj.assessment.recalculate_counts()
        return _serialize_obj(obj, ar_fields)

    ar_create_props = {}
    for f in ar_writable:
        ar_create_props[f] = ar_overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        "create_assessment_result",
        "Create a new assessment result",
        _obj_schema(ar_create_props),
        require_perm("compliance.assessment.create")(_create_assessment_result),
    )

    # Custom update with recalculate_counts()
    def _update_assessment_result(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = AssessmentResult.objects.get(pk=pk)
        except AssessmentResult.DoesNotExist:
            return _error("AssessmentResult not found.")
        for field_name in ar_writable:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    AssessmentResult, field_name, arguments[field_name]))
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        obj.assessment.recalculate_counts()
        return _serialize_obj(obj, ar_fields)

    ar_update_props = {"id": {"type": "string", "description": "UUID of the result to update"}}
    for f in ar_writable:
        ar_update_props[f] = ar_overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        "update_assessment_result",
        "Update an existing assessment result",
        _obj_schema(ar_update_props, ["id"]),
        require_perm("compliance.assessment.update")(_update_assessment_result),
    )

    # Custom delete with recalculate_counts()
    def _delete_assessment_result(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = AssessmentResult.objects.get(pk=pk)
        except AssessmentResult.DoesNotExist:
            return _error("AssessmentResult not found.")
        assessment = obj.assessment
        obj.delete()
        assessment.recalculate_counts()
        return {"deleted": True, "id": str(pk)}

    server.register_tool(
        "delete_assessment_result",
        "Delete an assessment result",
        _id_schema(),
        require_perm("compliance.assessment.delete")(_delete_assessment_result),
    )

    rm_fields = ["id", "source_requirement_id", "target_requirement_id",
                 "mapping_type", "coverage_level", "description", "created_at"]
    rm_writable = ["source_requirement_id", "target_requirement_id",
                   "mapping_type", "coverage_level", "description", "justification"]

    _register_crud(server, "requirement_mapping", RequirementMapping, "compliance.mapping",
                   list_fields=rm_fields,
                   writable_fields=rm_writable,
                   search_fields=["description"],
                   filters=["source_requirement_id", "target_requirement_id", "mapping_type"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["source_requirement_id", "target_requirement_id", "mapping_type"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "justification": _html_field("Justification"),
                       "mapping_type": {
                           "type": "string",
                           "description": "Type of mapping between requirements.",
                           "enum": ["equivalent", "partial_overlap", "includes", "included_by", "related"],
                       },
                       "coverage_level": {
                           "type": "string",
                           "description": "Coverage level of the mapping.",
                           "enum": ["full", "partial", "minimal"],
                       },
                   })

    ap_fields = ["id", "reference", "name", "description", "gap_description",
                 "remediation_plan", "priority", "status",
                 "target_date", "progress_percentage",
                 "owner_id", "is_approved", "created_at"]
    ap_writable = ["name", "description", "gap_description", "remediation_plan",
                   "priority", "target_date",
                   "progress_percentage", "owner_id", "assignees", "requirements"]

    _register_crud(server, "action_plan", ComplianceActionPlan, "compliance.action_plan",
                   list_fields=ap_fields,
                   writable_fields=ap_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "priority"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "gap_description": _html_field("Gap description"),
                       "remediation_plan": _html_field("Remediation plan"),
                       "priority": {
                           "type": "string",
                           "description": "Priority level.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": (
                               "Action plan status. Use action_plan_transition tool to change status "
                               "through the workflow instead of setting directly."
                           ),
                           "enum": [
                               "new", "to_define", "to_validate", "to_implement",
                               "implementation_to_validate", "validated", "closed", "cancelled",
                           ],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the action plan owner (user)"},
                       "target_date": {"type": "string", "description": "Target completion date (ISO 8601, e.g. 2025-12-31)"},
                       "progress_percentage": {"type": "integer", "description": "Progress percentage (0-100)"},
                   })

    # Action plan transition tool
    def _action_plan_transition(user, arguments):
        """Transition an action plan to a new status in the Kanban workflow.

        Workflow (forward):
          new → to_define → to_validate → to_implement
          → implementation_to_validate → validated → closed

        Refusals (backward, comment mandatory):
          to_validate → to_define
          implementation_to_validate → to_implement

        Cancellation (comment recommended):
          Any status except closed/cancelled → cancelled

        Parameters
        ----------
        action_plan_id : str (required)
            UUID of the action plan.
        target_status : str (required)
            Target status. Must be an allowed transition from the current
            status. Use action_plan_allowed_transitions to check first.
        comment : str
            Comment explaining the transition. Mandatory for refusals
            (backward transitions). Recommended for cancellations.
        """
        from compliance.constants import (
            ACTION_PLAN_TRANSITION_PERMISSIONS,
            ActionPlanStatus,
        )

        pk = arguments.get("action_plan_id")
        target = arguments.get("target_status")
        comment = arguments.get("comment", "")
        if not pk or not target:
            raise InvalidParamsError("action_plan_id and target_status are required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            return _error("Action plan not found.")

        # Check per-transition permission (same logic as the UI view)
        transition_key = (ap.status, target)
        if target == ActionPlanStatus.CANCELLED:
            required_perm = "compliance.action_plan.cancel"
        else:
            required_perm = ACTION_PLAN_TRANSITION_PERMISSIONS.get(transition_key)
        if required_perm and not user.is_superuser and not user.has_perm(required_perm):
            return _error(
                f"Permission denied: you need '{required_perm}' to transition "
                f"from '{ap.status}' to '{target}'."
            )

        # Build helpful error context on failure
        allowed = ap.get_allowed_transitions()
        if target not in allowed:
            allowed_str = ", ".join(str(s) for s in allowed) if allowed else "none (terminal status)"
            return _error(
                f"Cannot transition from '{ap.status}' to '{target}'. "
                f"Allowed transitions from '{ap.status}': {allowed_str}."
            )

        try:
            ap.transition_to(target, user, comment)
        except ValueError as e:
            return _error(str(e))
        return {"id": str(ap.pk), "status": ap.status, "reference": ap.reference}

    server.register_tool(
        "action_plan_transition",
        "Transition an action plan to a new Kanban status. "
        "Forward flow: new → to_define → to_validate → to_implement → "
        "implementation_to_validate → validated → closed. "
        "Refusals (require comment): to_validate → to_define, "
        "implementation_to_validate → to_implement. "
        "Cancellation: any non-terminal status → cancelled.",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
            "target_status": {
                "type": "string",
                "description": "Target status to transition to",
                "enum": ["new", "to_define", "to_validate", "to_implement",
                         "implementation_to_validate", "validated", "closed", "cancelled"],
            },
            "comment": {"type": "string", "description": "Comment explaining the transition. Mandatory for refusals (backward transitions). Recommended for cancellations."},
        }, ["action_plan_id", "target_status"]),
        require_perm("compliance.action_plan.update")(_action_plan_transition),
    )

    # Action plan transition history tool
    def _action_plan_transitions(user, arguments):
        """List transition history for an action plan."""
        pk = arguments.get("action_plan_id")
        if not pk:
            raise InvalidParamsError("action_plan_id is required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            return _error("Action plan not found.")
        transitions = ap.transitions.select_related("performed_by").all()[:50]
        return [
            {
                "id": str(t.pk),
                "from_status": t.from_status,
                "to_status": t.to_status,
                "performed_by": t.performed_by.display_name,
                "comment": t.comment,
                "is_refusal": t.is_refusal,
                "created_at": t.created_at.isoformat(),
            }
            for t in transitions
        ]

    server.register_tool(
        "action_plan_transitions",
        "List transition history for an action plan",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
        }, ["action_plan_id"]),
        require_perm("compliance.action_plan.read")(_action_plan_transitions),
    )

    # Action plan kanban tool
    def _action_plan_kanban(user, arguments):
        """Get action plans grouped by status for kanban view.

        Returns a dict with:
        - columns: action plans grouped by status
        - workflow_rules: allowed transitions, refusals, and cancellable statuses
        """
        from compliance.constants import (
            ACTION_PLAN_TRANSITIONS,
            ACTION_PLAN_REFUSAL_TRANSITIONS,
            ACTION_PLAN_CANCELLABLE_STATUSES,
            ActionPlanStatus as APS,
        )
        qs = ComplianceActionPlan.objects.all()
        columns = {}
        for status_choice in APS:
            plans = qs.filter(status=status_choice.value)
            columns[status_choice.value] = [
                {"id": str(p.pk), "reference": p.reference, "name": p.name,
                 "priority": p.priority, "status": p.status,
                 "owner": str(p.owner) if p.owner_id else "",
                 "assignees": [
                     {"id": str(u.pk), "name": u.display_name}
                     for u in p.assignees.all()
                 ],
                 "target_date": str(p.target_date) if p.target_date else "",
                 "progress_percentage": p.progress_percentage,
                 "is_overdue": p.is_overdue}
                for p in plans
            ]
        # Build workflow rules so LLM knows which transitions are valid
        transitions = {}
        for from_s, to_list in ACTION_PLAN_TRANSITIONS.items():
            key = from_s.value if hasattr(from_s, "value") else from_s
            targets = [s.value if hasattr(s, "value") else s for s in to_list]
            # Add cancellation if applicable
            if from_s in ACTION_PLAN_CANCELLABLE_STATUSES:
                targets.append(APS.CANCELLED.value)
            transitions[key] = targets
        refusals = {
            (from_s.value if hasattr(from_s, "value") else from_s): (
                to_s.value if hasattr(to_s, "value") else to_s
            )
            for from_s, to_s in ACTION_PLAN_REFUSAL_TRANSITIONS.items()
        }
        return {
            "columns": columns,
            "workflow_rules": {
                "allowed_transitions": transitions,
                "refusal_transitions": refusals,
                "refusal_transitions_require_comment": True,
            },
        }

    server.register_tool(
        "action_plan_kanban",
        "Get action plans grouped by status for kanban board, "
        "including workflow transition rules",
        _obj_schema({}, []),
        require_perm("compliance.action_plan.read")(_action_plan_kanban),
    )

    # Action plan allowed transitions tool
    def _action_plan_allowed_transitions(user, arguments):
        """Get the list of allowed transitions for a specific action plan.

        Returns the current status, allowed target statuses, which ones
        are refusals (require comment), and which is cancellation.
        Useful to check before calling action_plan_transition.
        """
        from compliance.constants import (
            ACTION_PLAN_REFUSAL_TRANSITIONS,
            ACTION_PLAN_TRANSITION_PERMISSIONS,
            ActionPlanStatus,
        )
        pk = arguments.get("action_plan_id")
        if not pk:
            raise InvalidParamsError("action_plan_id is required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            return _error("Action plan not found.")

        allowed = ap.get_allowed_transitions()
        transitions = []
        for target in allowed:
            target_val = target.value if hasattr(target, "value") else target
            transition_key = (ap.status, target_val)
            if target_val == ActionPlanStatus.CANCELLED:
                perm = "compliance.action_plan.cancel"
            else:
                perm = ACTION_PLAN_TRANSITION_PERMISSIONS.get(transition_key)
            has_perm = user.is_superuser or not perm or user.has_perm(perm)
            is_refusal = ACTION_PLAN_REFUSAL_TRANSITIONS.get(ap.status) == target
            transitions.append({
                "target_status": target_val,
                "label": ActionPlanStatus(target_val).label,
                "is_refusal": is_refusal,
                "is_cancellation": target_val == ActionPlanStatus.CANCELLED,
                "comment_required": is_refusal,
                "required_permission": perm or None,
                "user_has_permission": has_perm,
            })
        return {
            "action_plan_id": str(ap.pk),
            "reference": ap.reference,
            "current_status": ap.status,
            "allowed_transitions": transitions,
        }

    server.register_tool(
        "action_plan_allowed_transitions",
        "Get allowed status transitions for an action plan, "
        "including permission checks and refusal/cancellation flags. "
        "Call this before action_plan_transition to know what is possible.",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
        }, ["action_plan_id"]),
        require_perm("compliance.action_plan.read")(_action_plan_allowed_transitions),
    )

    # ── Action Plan Comments ──
    ActionPlanComment = _get_model("compliance", "ActionPlanComment")

    @require_perm("compliance.action_plan.read")
    def _list_action_plan_comments(user, arguments):
        """List comments on an action plan, including threaded replies."""
        pk = arguments.get("action_plan_id")
        if not pk:
            raise InvalidParamsError("action_plan_id is required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            raise InvalidParamsError("Action plan not found.")
        comments = (
            ap.comments.filter(parent__isnull=True)
            .select_related("author")
            .prefetch_related("replies__author")
        )
        result = []
        for c in comments:
            entry = {
                "id": str(c.id),
                "author": c.author.display_name,
                "content": c.content,
                "created_at": c.created_at.isoformat(),
                "replies": [
                    {
                        "id": str(r.id),
                        "author": r.author.display_name,
                        "content": r.content,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in c.replies.all()
                ],
            }
            result.append(entry)
        return result

    server.register_tool(
        "list_action_plan_comments",
        "List comments on an action plan with threaded replies",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
        }, ["action_plan_id"]),
        _list_action_plan_comments,
    )

    @require_perm("compliance.action_plan.update")
    def _create_action_plan_comment(user, arguments):
        """Create a comment or reply on an action plan."""
        pk = arguments.get("action_plan_id")
        content = arguments.get("content")
        if not pk or not content:
            raise InvalidParamsError("action_plan_id and content are required.")
        try:
            ap = ComplianceActionPlan.objects.get(pk=pk)
        except ComplianceActionPlan.DoesNotExist:
            raise InvalidParamsError("Action plan not found.")

        parent = None
        parent_id = arguments.get("parent_id")
        if parent_id:
            try:
                parent = ActionPlanComment.objects.get(pk=parent_id, action_plan=ap)
            except ActionPlanComment.DoesNotExist:
                raise InvalidParamsError("Parent comment not found.")
            if parent.parent_id is not None:
                parent = parent.parent

        comment = ActionPlanComment.objects.create(
            action_plan=ap,
            author=user,
            content=content,
            parent=parent,
        )
        return {
            "id": str(comment.id),
            "author": user.display_name,
            "content": comment.content,
            "parent_id": str(parent.id) if parent else None,
            "created_at": comment.created_at.isoformat(),
        }

    server.register_tool(
        "create_action_plan_comment",
        "Create a comment or reply on an action plan",
        _obj_schema({
            "action_plan_id": {"type": "string", "description": "UUID of the action plan"},
            "content": {"type": "string", "description": "Comment text"},
            "parent_id": {"type": "string", "description": "UUID of parent comment (for replies, optional)"},
        }, ["action_plan_id", "content"]),
        _create_action_plan_comment,
    )

    Finding = _get_model("compliance", "Finding")
    fi_fields = ["id", "reference", "assessment_id", "finding_type",
                 "description", "recommendation", "evidence",
                 "assessor_id", "created_at"]
    fi_writable = ["assessment_id", "finding_type", "description",
                   "recommendation", "evidence", "assessor_id"]

    fi_field_overrides = {
        "description": _html_field("Finding description"),
        "recommendation": _html_field("Auditor recommendation"),
        "evidence": _html_field("Evidence presented"),
        "assessor_id": {"type": "string", "description": "UUID of the assessor (user)"},
        "finding_type": {
            "type": "string",
            "description": (
                "Type of finding. Allowed values: "
                "major_nc (Major non-conformity, ref NCMAJ-x), "
                "minor_nc (Minor non-conformity, ref NCMIN-x), "
                "observation (Observation, ref OBS-x), "
                "improvement (Improvement opportunity, ref OA-x), "
                "strength (Strength, ref STR-x)"
            ),
            "enum": ["major_nc", "minor_nc", "observation", "improvement", "strength"],
        },
    }

    # Use generic list/get/delete for finding
    fi_filter_props = {
        "assessment_id": {"type": "string", "description": "Filter by assessment_id"},
        "finding_type": {"type": "string", "description": "Filter by finding_type"},
    }
    server.register_tool(
        "list_findings",
        "List findings with optional search and filters",
        _list_schema(fi_filter_props),
        require_perm("compliance.assessment.read")(
            _list_handler(Finding, fi_fields, ["reference", "description"],
                          ["assessment_id", "finding_type"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "get_finding",
        "Get a finding by ID",
        _id_schema(),
        require_perm("compliance.assessment.read")(
            _get_handler(Finding, fi_fields, scope_filtered=False)
        ),
    )
    def _delete_finding(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = Finding.objects.get(pk=pk)
        except Finding.DoesNotExist:
            return _error("Finding not found.")
        assessment = obj.assessment
        obj.delete()
        assessment.apply_findings_to_results()
        return {"deleted": True, "id": str(pk)}

    server.register_tool(
        "delete_finding",
        "Delete a finding",
        _id_schema(),
        require_perm("compliance.assessment.delete")(_delete_finding),
    )

    # Custom create handler with requirement_ids M2M support
    def _create_finding(user, arguments):
        """Create an audit finding, optionally linking requirements.

        Parameters
        ----------
        assessment_id : str (required)
            UUID of the compliance assessment.
        finding_type : str (required)
            Type of finding: major_nc, minor_nc, observation, improvement, strength.
        description : str (required)
            Finding description (HTML rich text).
        recommendation : str
            Auditor recommendation (HTML rich text).
        evidence : str
            Evidence presented (HTML rich text).
        assessor_id : str
            UUID of the assessor (user).
        requirement_ids : list[str]
            List of requirement UUIDs to link to this finding.
        """
        requirement_ids = arguments.pop("requirement_ids", None)
        kwargs = {}
        for field_name in fi_writable:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    Finding, field_name, arguments[field_name])
        kwargs["created_by"] = user
        try:
            obj = Finding(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if requirement_ids:
            reqs = Requirement.objects.filter(pk__in=requirement_ids)
            if reqs.count() != len(requirement_ids):
                found = set(str(r.pk) for r in reqs)
                missing = [rid for rid in requirement_ids if rid not in found]
                return _error(f"Requirements not found: {missing}")
            obj.requirements.set(reqs)
        # Propagate finding to assessment results and recalculate counts
        obj.assessment.apply_findings_to_results()
        fields = [f.name for f in Finding._meta.fields]
        return _serialize_obj(obj, fields)

    fi_create_props = {}
    for f in fi_writable:
        fi_create_props[f] = fi_field_overrides.get(f, {"type": "string", "description": f})
    fi_create_props["requirement_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of requirement UUIDs to link to this finding",
    }
    server.register_tool(
        "create_finding",
        "Create a new audit finding",
        _obj_schema(fi_create_props),
        require_perm("compliance.assessment.create")(_create_finding),
    )

    # Custom update handler with requirement_ids M2M support
    def _update_finding(user, arguments):
        """Update an audit finding, optionally changing linked requirements.

        Parameters
        ----------
        id : str (required)
            UUID of the finding to update.
        requirement_ids : list[str]
            Replace the linked requirements (pass empty list to clear).

        All other writable fields are optional.
        """
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = Finding.objects.get(pk=pk)
        except Finding.DoesNotExist:
            return _error("Finding not found.")
        requirement_ids = arguments.pop("requirement_ids", None)
        changed_fields = set()
        for field_name in fi_writable:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    Finding, field_name, arguments[field_name]))
                changed_fields.add(field_name)
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        if requirement_ids is not None:
            reqs = Requirement.objects.filter(pk__in=requirement_ids)
            if requirement_ids and reqs.count() != len(requirement_ids):
                found = set(str(r.pk) for r in reqs)
                missing = [rid for rid in requirement_ids if rid not in found]
                return _error(f"Requirements not found: {missing}")
            obj.requirements.set(reqs)
        # Propagate finding changes to assessment results and recalculate counts
        obj.assessment.apply_findings_to_results()
        fields = [f.name for f in Finding._meta.fields]
        return _serialize_obj(obj, fields)

    fi_update_props = {"id": {"type": "string", "description": "UUID of the finding to update"}}
    for f in fi_writable:
        fi_update_props[f] = fi_field_overrides.get(f, {"type": "string", "description": f})
    fi_update_props["requirement_ids"] = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of requirement UUIDs to link (replaces existing links)",
    }
    server.register_tool(
        "update_finding",
        "Update an existing audit finding",
        _obj_schema(fi_update_props, ["id"]),
        require_perm("compliance.assessment.update")(_update_finding),
    )


# ── Risks Module ───────────────────────────────────────────

def _register_risks_tools(server):
    RiskAssessment = _get_model("risks", "RiskAssessment")
    RiskCriteria = _get_model("risks", "RiskCriteria")
    ScaleLevel = _get_model("risks", "ScaleLevel")
    RiskLevel = _get_model("risks", "RiskLevel")
    Risk = _get_model("risks", "Risk")
    RiskTreatmentPlan = _get_model("risks", "RiskTreatmentPlan")
    TreatmentAction = _get_model("risks", "TreatmentAction")
    RiskAcceptance = _get_model("risks", "RiskAcceptance")
    Threat = _get_model("risks", "Threat")
    Vulnerability = _get_model("risks", "Vulnerability")
    ISO27005Risk = _get_model("risks", "ISO27005Risk")

    ra_fields = ["id", "reference", "name", "description", "status", "assessment_date",
                 "risk_criteria_id", "is_approved", "created_at"]
    ra_writable = ["name", "description", "status", "assessment_date",
                   "risk_criteria_id", "assessor_id"]

    _register_crud(server, "risk_assessment", RiskAssessment, "risks.assessment",
                   list_fields=ra_fields,
                   writable_fields=ra_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status"],
                   required_fields=["name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "status": {
                           "type": "string",
                           "description": "Risk assessment status.",
                           "enum": ["draft", "in_progress", "completed", "validated", "archived"],
                       },
                       "assessment_date": {"type": "string", "description": "Assessment date (ISO 8601, e.g. 2025-06-15)"},
                       "risk_criteria_id": {"type": "string", "description": "UUID of the risk criteria to use"},
                       "assessor_id": {"type": "string", "description": "UUID of the assessor (user)"},
                   })

    rc_fields = ["id", "name", "description", "risk_matrix",
                 "acceptance_threshold", "is_default", "status", "created_at"]
    rc_writable = ["name", "description", "risk_matrix",
                   "acceptance_threshold", "is_default", "status"]

    _register_crud(server, "risk_criteria", RiskCriteria, "risks.criteria",
                   list_fields=rc_fields,
                   writable_fields=rc_writable,
                   search_fields=["name", "description"],
                   filters=["status"],
                   has_approve=False,
                   field_overrides={
                       "description": _html_field("Description"),
                       "risk_matrix": {
                           "type": "object",
                           "description": (
                               "Risk matrix as JSON object mapping 'likelihood,impact' to risk level. "
                               "Example for a 5x5 matrix: {\"1,1\": 1, \"1,2\": 2, ..., \"5,5\": 5}. "
                               "Can be omitted — the matrix will be auto-built from scale levels "
                               "and risk levels via rebuild_risk_matrix()."
                           ),
                       },
                       "acceptance_threshold": {
                           "type": "integer",
                           "description": "Risk level at or below which risks are automatically acceptable (default 0).",
                       },
                       "is_default": {
                           "type": "boolean",
                           "description": "Whether this is the default risk criteria.",
                       },
                       "status": {
                           "type": "string",
                           "description": "Status of the criteria.",
                           "enum": ["draft", "active", "archived"],
                       },
                   })

    # Scale levels (child of RiskCriteria, no approve)
    sl_fields = ["id", "criteria_id", "scale_type", "level", "name",
                 "description", "color"]
    sl_writable = ["criteria_id", "scale_type", "level", "name",
                   "description", "color"]

    _register_crud(server, "scale_level", ScaleLevel, "risks.criteria",
                   list_fields=sl_fields,
                   writable_fields=sl_writable,
                   search_fields=["name", "description"],
                   filters=["criteria_id", "scale_type"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides={
                       "description": _html_field("Description"),
                       "criteria_id": {
                           "type": "string",
                           "description": "UUID of the parent RiskCriteria.",
                       },
                       "scale_type": {
                           "type": "string",
                           "description": "Type of scale.",
                           "enum": ["likelihood", "impact"],
                       },
                       "level": {
                           "type": "integer",
                           "description": "Numeric level (e.g. 1-5). Must be unique per criteria + scale_type.",
                       },
                   })

    # Risk levels (child of RiskCriteria, no approve)
    rl_fields = ["id", "criteria_id", "level", "name", "description",
                 "color", "requires_treatment"]
    rl_writable = ["criteria_id", "level", "name", "description",
                   "color", "requires_treatment"]

    _register_crud(server, "risk_level", RiskLevel, "risks.criteria",
                   list_fields=rl_fields,
                   writable_fields=rl_writable,
                   search_fields=["name", "description"],
                   filters=["criteria_id", "requires_treatment"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["criteria_id", "level", "name"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "criteria_id": {"type": "string", "description": "UUID of the parent RiskCriteria."},
                       "level": {"type": "integer", "description": "Numeric risk level (e.g. 1-5). Must be unique per criteria."},
                       "color": {"type": "string", "description": "Color hex code (e.g. #ff0000)"},
                       "requires_treatment": {"type": "boolean", "description": "Whether this risk level requires treatment."},
                   })

    risk_fields = ["id", "reference", "name", "description", "status", "priority",
                   "current_risk_level", "assessment_id",
                   "is_approved", "created_at"]
    risk_writable = ["name", "description", "status", "priority",
                     "initial_likelihood", "initial_impact",
                     "current_likelihood", "current_impact",
                     "residual_likelihood", "residual_impact",
                     "treatment_decision", "assessment_id", "risk_owner_id"]

    _register_crud(server, "risk", Risk, "risks.risk",
                   list_fields=risk_fields,
                   writable_fields=risk_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "priority", "assessment_id"],
                   scope_filtered=False,
                   required_fields=["name", "assessment_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "status": {
                           "type": "string",
                           "description": "Risk status.",
                           "enum": [
                               "identified", "analyzed", "evaluated",
                               "treatment_planned", "treatment_in_progress",
                               "treated", "accepted", "closed", "monitoring",
                           ],
                       },
                       "priority": {
                           "type": "string",
                           "description": "Risk priority.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "treatment_decision": {
                           "type": "string",
                           "description": "Treatment decision.",
                           "enum": ["accept", "mitigate", "transfer", "avoid", "not_decided"],
                       },
                       "initial_likelihood": {"type": "integer", "description": "Initial likelihood level (matching scale levels, e.g. 1-5)"},
                       "initial_impact": {"type": "integer", "description": "Initial impact level (matching scale levels, e.g. 1-5)"},
                       "current_likelihood": {"type": "integer", "description": "Current likelihood level (matching scale levels, e.g. 1-5)"},
                       "current_impact": {"type": "integer", "description": "Current impact level (matching scale levels, e.g. 1-5)"},
                       "residual_likelihood": {"type": "integer", "description": "Residual likelihood level (matching scale levels, e.g. 1-5)"},
                       "residual_impact": {"type": "integer", "description": "Residual impact level (matching scale levels, e.g. 1-5)"},
                       "risk_owner_id": {"type": "string", "description": "UUID of the risk owner (user)"},
                   })

    tp_fields = ["id", "reference", "name", "description", "treatment_type", "status",
                 "expected_residual_likelihood", "expected_residual_impact",
                 "cost_estimate", "start_date", "target_date", "completion_date",
                 "progress_percentage", "risk_id", "is_approved", "created_at"]
    tp_writable = ["name", "description", "treatment_type", "status",
                   "expected_residual_likelihood", "expected_residual_impact",
                   "cost_estimate", "start_date", "target_date", "completion_date",
                   "progress_percentage", "risk_id", "owner_id"]

    _register_crud(server, "risk_treatment_plan", RiskTreatmentPlan, "risks.treatment",
                   list_fields=tp_fields,
                   writable_fields=tp_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "risk_id"],
                   scope_filtered=False,
                   required_fields=["name", "risk_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "treatment_type": {
                           "type": "string",
                           "description": "Treatment strategy type.",
                           "enum": ["mitigate", "transfer", "avoid"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Treatment plan status.",
                           "enum": ["planned", "in_progress", "completed", "cancelled", "overdue"],
                       },
                       "expected_residual_likelihood": {"type": "integer", "description": "Expected residual likelihood (matching scale levels, e.g. 1-5)"},
                       "expected_residual_impact": {"type": "integer", "description": "Expected residual impact (matching scale levels, e.g. 1-5)"},
                       "owner_id": {"type": "string", "description": "UUID of the treatment plan owner (user)"},
                   })

    # Treatment actions (child of RiskTreatmentPlan, no approve)
    ta_fields = ["id", "treatment_plan_id", "description", "owner_id",
                 "target_date", "completion_date", "status", "order", "created_at"]
    ta_writable = ["treatment_plan_id", "description", "owner_id",
                   "target_date", "completion_date", "status", "order"]

    _register_crud(server, "treatment_action", TreatmentAction, "risks.treatment",
                   list_fields=ta_fields,
                   writable_fields=ta_writable,
                   search_fields=["description"],
                   filters=["treatment_plan_id", "status"],
                   scope_filtered=False,
                   has_approve=False,
                   required_fields=["treatment_plan_id", "description"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "status": {
                           "type": "string",
                           "description": "Action status.",
                           "enum": ["planned", "in_progress", "completed", "cancelled"],
                       },
                       "owner_id": {"type": "string", "description": "UUID of the action owner (user)"},
                   })

    acc_fields = ["id", "risk_id", "status", "justification", "conditions",
                  "valid_until", "accepted_by_id", "created_at"]
    acc_writable = ["risk_id", "justification", "conditions", "valid_until",
                    "accepted_by_id"]

    _register_crud(server, "risk_acceptance", RiskAcceptance, "risks.acceptance",
                   list_fields=acc_fields,
                   writable_fields=acc_writable,
                   search_fields=["justification"],
                   filters=["risk_id", "status"],
                   scope_filtered=False,
                   has_approve=True,
                   required_fields=["risk_id", "justification"],
                   field_overrides={
                       "justification": _html_field("Justification"),
                       "conditions": _html_field("Conditions"),
                       "status": {
                           "type": "string",
                           "description": "Acceptance status.",
                           "enum": ["active", "expired", "revoked", "renewed"],
                       },
                       "accepted_by_id": {"type": "string", "description": "UUID of the user who accepted the risk"},
                   })

    threat_fields = ["id", "reference", "name", "description", "type",
                     "origin", "category", "typical_likelihood", "status", "created_at"]
    threat_writable = ["name", "description", "type", "origin", "category",
                       "typical_likelihood", "status"]

    _register_crud(server, "threat", Threat, "risks.threat",
                   list_fields=threat_fields,
                   writable_fields=threat_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["type", "status"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "type": {
                           "type": "string",
                           "description": "Threat type.",
                           "enum": ["deliberate", "accidental", "environmental", "other"],
                       },
                       "origin": {
                           "type": "string",
                           "description": "Threat origin.",
                           "enum": ["human_internal", "human_external", "natural", "technical", "other"],
                       },
                       "category": {
                           "type": "string",
                           "description": "Threat category.",
                           "enum": [
                               "malware", "social_engineering", "unauthorized_access",
                               "denial_of_service", "data_breach", "physical_attack",
                               "espionage", "fraud", "sabotage", "human_error",
                               "system_failure", "network_failure", "power_failure",
                               "natural_disaster", "fire", "water_damage", "theft",
                               "vandalism", "supply_chain", "insider_threat",
                               "ransomware", "apt",
                           ],
                       },
                       "typical_likelihood": {
                           "type": "integer",
                           "description": "Typical likelihood level (integer, e.g. 1-5).",
                       },
                       "status": {
                           "type": "string",
                           "description": "Threat status.",
                           "enum": ["active", "inactive"],
                       },
                   })

    vuln_fields = ["id", "reference", "name", "description", "category",
                   "severity", "status", "remediation_guidance", "created_at"]
    vuln_writable = ["name", "description", "category", "severity", "status",
                     "remediation_guidance"]

    _register_crud(server, "vulnerability", Vulnerability, "risks.vulnerability",
                   list_fields=vuln_fields,
                   writable_fields=vuln_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["category", "severity", "status"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "remediation_guidance": _html_field("Remediation guidance"),
                       "category": {
                           "type": "string",
                           "description": "Vulnerability category.",
                           "enum": [
                               "configuration_weakness", "missing_patch", "design_flaw",
                               "coding_error", "weak_authentication", "insufficient_logging",
                               "lack_of_encryption", "physical_vulnerability",
                               "organizational_weakness", "human_factor", "obsolescence",
                               "insufficient_backup", "network_exposure",
                               "third_party_dependency",
                           ],
                       },
                       "severity": {
                           "type": "string",
                           "description": "Vulnerability severity.",
                           "enum": ["low", "medium", "high", "critical"],
                       },
                       "status": {
                           "type": "string",
                           "description": "Vulnerability status.",
                           "enum": ["identified", "confirmed", "mitigated", "accepted", "closed"],
                       },
                   })

    iso_fields = ["id", "assessment_id", "threat_id", "vulnerability_id",
                  "threat_likelihood", "vulnerability_exposure",
                  "combined_likelihood",
                  "impact_confidentiality", "impact_integrity",
                  "impact_availability", "max_impact",
                  "risk_level", "existing_controls", "risk_id",
                  "description", "created_at"]
    iso_writable = ["assessment_id", "threat_id", "vulnerability_id",
                    "threat_likelihood", "vulnerability_exposure",
                    "impact_confidentiality", "impact_integrity",
                    "impact_availability",
                    "existing_controls", "risk_id", "description"]

    _register_crud(server, "iso27005_risk", ISO27005Risk, "risks.iso27005",
                   list_fields=iso_fields,
                   writable_fields=iso_writable,
                   search_fields=["description"],
                   filters=["assessment_id", "threat_id", "vulnerability_id"],
                   scope_filtered=False,
                   has_approve=True,
                   field_overrides={
                       "description": _html_field("Description"),
                       "existing_controls": _html_field("Existing controls"),
                       "threat_likelihood": {
                           "type": "integer",
                           "description": (
                               "Threat likelihood level (integer matching a scale level, e.g. 1-5). "
                               "combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure)."
                           ),
                       },
                       "vulnerability_exposure": {
                           "type": "integer",
                           "description": (
                               "Vulnerability exposure level (integer matching a scale level, e.g. 1-5). "
                               "combined_likelihood is auto-computed as max(threat_likelihood, vulnerability_exposure)."
                           ),
                       },
                       "impact_confidentiality": {
                           "type": "integer",
                           "description": "Confidentiality impact level (integer matching a scale level, e.g. 1-5).",
                       },
                       "impact_integrity": {
                           "type": "integer",
                           "description": "Integrity impact level (integer matching a scale level, e.g. 1-5).",
                       },
                       "impact_availability": {
                           "type": "integer",
                           "description": "Availability impact level (integer matching a scale level, e.g. 1-5).",
                       },
                   })

    # ── Risk ↔ Requirement linking tools ──────────────────────
    #
    # These tools manage the many-to-many relationship between risks and
    # compliance requirements (Risk.linked_requirements / Requirement.linked_risks).
    #
    # Available operations:
    #   - list_risk_requirements     : list all requirements linked to a risk
    #   - list_requirement_risks     : list all risks linked to a requirement
    #   - link_risk_requirements     : attach one or more requirements to a risk
    #   - unlink_risk_requirements   : detach one or more requirements from a risk
    #   - set_risk_requirements      : replace the full set of linked requirements on a risk
    #
    # All operations respect the standard permission model
    # (risks.risk.read / risks.risk.update).

    Requirement = _get_model("compliance", "Requirement")

    req_link_fields = [
        "id", "reference", "requirement_number", "name",
        "compliance_status", "framework_id",
    ]

    risk_link_fields = [
        "id", "reference", "name", "current_risk_level",
        "priority", "status",
    ]

    # -- list_risk_requirements: list requirements linked to a given risk --
    def _list_risk_requirements(user, arguments):
        """Return all compliance requirements linked to a specific risk.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk whose linked requirements should be returned.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "total": <int>, "items": [...]}``.
            Each item contains: id, reference, requirement_number, name,
            compliance_status, and framework_id.
        """
        risk_id = arguments.get("risk_id")
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        reqs = risk.linked_requirements.all()
        items = [_serialize_obj(r, req_link_fields) for r in reqs]
        return {"risk_id": str(risk_id), "total": len(items), "items": items}

    server.register_tool(
        "list_risk_requirements",
        (
            "List all compliance requirements linked to a risk. "
            "Returns requirement id, reference, number, name, compliance_status "
            "and framework_id for each linked requirement."
        ),
        _obj_schema(
            {"risk_id": {"type": "string", "description": "UUID of the risk"}},
            required=["risk_id"],
        ),
        require_perm("risks.risk.read")(_list_risk_requirements),
    )

    # -- list_requirement_risks: list risks linked to a given requirement --
    def _list_requirement_risks(user, arguments):
        """Return all risks linked to a specific compliance requirement.

        Parameters
        ----------
        requirement_id : str (required)
            UUID of the requirement whose linked risks should be returned.

        Returns
        -------
        dict
            ``{"requirement_id": "<uuid>", "total": <int>, "items": [...]}``.
            Each item contains: id, reference, name, current_risk_level,
            priority, and status.
        """
        req_id = arguments.get("requirement_id")
        if not req_id:
            raise InvalidParamsError("requirement_id is required.")
        try:
            req = Requirement.objects.get(pk=req_id)
        except Requirement.DoesNotExist:
            return _error("Requirement not found.")
        risks = req.linked_risks.all()
        items = [_serialize_obj(r, risk_link_fields) for r in risks]
        return {"requirement_id": str(req_id), "total": len(items), "items": items}

    server.register_tool(
        "list_requirement_risks",
        (
            "List all risks linked to a compliance requirement. "
            "Returns risk id, reference, name, current_risk_level, priority "
            "and status for each linked risk."
        ),
        _obj_schema(
            {"requirement_id": {"type": "string", "description": "UUID of the requirement"}},
            required=["requirement_id"],
        ),
        require_perm("compliance.requirement.read")(_list_requirement_risks),
    )

    # -- link_risk_requirements: add requirements to a risk --
    def _link_risk_requirements(user, arguments):
        """Add one or more requirements to a risk's linked requirements.

        This is an *additive* operation: existing links are preserved and
        the supplied requirement_ids are added on top.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk to link requirements to.
        requirement_ids : list[str] (required)
            List of requirement UUIDs to attach.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "added": <int>, "total": <int>}``
            where *added* is the number of newly created links and *total*
            is the resulting count of linked requirements.
        """
        risk_id = arguments.get("risk_id")
        req_ids = arguments.get("requirement_ids", [])
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        if not req_ids:
            raise InvalidParamsError("requirement_ids is required and must be a non-empty list.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        existing = set(str(pk) for pk in risk.linked_requirements.values_list("pk", flat=True))
        reqs = Requirement.objects.filter(pk__in=req_ids)
        if reqs.count() != len(req_ids):
            found = set(str(r.pk) for r in reqs)
            missing = [rid for rid in req_ids if rid not in found]
            return _error(f"Requirements not found: {missing}")
        risk.linked_requirements.add(*reqs)
        added = len(set(req_ids) - existing)
        total = risk.linked_requirements.count()
        return {"risk_id": str(risk_id), "added": added, "total": total}

    server.register_tool(
        "link_risk_requirements",
        (
            "Link one or more compliance requirements to a risk. "
            "This is additive — existing links are preserved. "
            "Provide a risk_id and a list of requirement_ids to attach."
        ),
        _obj_schema(
            {
                "risk_id": {"type": "string", "description": "UUID of the risk"},
                "requirement_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of requirement UUIDs to link to the risk",
                },
            },
            required=["risk_id", "requirement_ids"],
        ),
        require_perm("risks.risk.update")(_link_risk_requirements),
    )

    # -- unlink_risk_requirements: remove requirements from a risk --
    def _unlink_risk_requirements(user, arguments):
        """Remove one or more requirements from a risk's linked requirements.

        Only the specified links are removed; other existing links remain
        untouched.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk to unlink requirements from.
        requirement_ids : list[str] (required)
            List of requirement UUIDs to detach.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "removed": <int>, "total": <int>}``
            where *removed* is the number of links that were actually
            deleted and *total* is the resulting count.
        """
        risk_id = arguments.get("risk_id")
        req_ids = arguments.get("requirement_ids", [])
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        if not req_ids:
            raise InvalidParamsError("requirement_ids is required and must be a non-empty list.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        existing = set(str(pk) for pk in risk.linked_requirements.values_list("pk", flat=True))
        removed = len(existing & set(req_ids))
        risk.linked_requirements.remove(*Requirement.objects.filter(pk__in=req_ids))
        total = risk.linked_requirements.count()
        return {"risk_id": str(risk_id), "removed": removed, "total": total}

    server.register_tool(
        "unlink_risk_requirements",
        (
            "Remove one or more compliance requirements from a risk. "
            "Only the specified links are removed; other links are preserved. "
            "Provide a risk_id and a list of requirement_ids to detach."
        ),
        _obj_schema(
            {
                "risk_id": {"type": "string", "description": "UUID of the risk"},
                "requirement_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of requirement UUIDs to unlink from the risk",
                },
            },
            required=["risk_id", "requirement_ids"],
        ),
        require_perm("risks.risk.update")(_unlink_risk_requirements),
    )

    # -- set_risk_requirements: replace all linked requirements on a risk --
    def _set_risk_requirements(user, arguments):
        """Replace the entire set of linked requirements on a risk.

        All previous links are removed and replaced by the supplied list.
        Pass an empty list to clear all links.

        Parameters
        ----------
        risk_id : str (required)
            UUID of the risk whose requirements should be replaced.
        requirement_ids : list[str] (required)
            Complete list of requirement UUIDs that should be linked.
            Pass ``[]`` to remove all links.

        Returns
        -------
        dict
            ``{"risk_id": "<uuid>", "total": <int>}`` with the resulting
            number of linked requirements.
        """
        risk_id = arguments.get("risk_id")
        req_ids = arguments.get("requirement_ids", [])
        if not risk_id:
            raise InvalidParamsError("risk_id is required.")
        if not isinstance(req_ids, list):
            raise InvalidParamsError("requirement_ids must be a list.")
        try:
            risk = Risk.objects.get(pk=risk_id)
        except Risk.DoesNotExist:
            return _error("Risk not found.")
        if req_ids:
            reqs = Requirement.objects.filter(pk__in=req_ids)
            if reqs.count() != len(req_ids):
                found = set(str(r.pk) for r in reqs)
                missing = [rid for rid in req_ids if rid not in found]
                return _error(f"Requirements not found: {missing}")
            risk.linked_requirements.set(reqs)
        else:
            risk.linked_requirements.clear()
        total = risk.linked_requirements.count()
        return {"risk_id": str(risk_id), "total": total}

    server.register_tool(
        "set_risk_requirements",
        (
            "Replace the full set of linked requirements on a risk. "
            "All previous links are removed and replaced by the supplied list. "
            "Pass an empty requirement_ids list to clear all links."
        ),
        _obj_schema(
            {
                "risk_id": {"type": "string", "description": "UUID of the risk"},
                "requirement_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Complete list of requirement UUIDs to link. "
                        "Pass an empty list to remove all links."
                    ),
                },
            },
            required=["risk_id", "requirement_ids"],
        ),
        require_perm("risks.risk.update")(_set_risk_requirements),
    )

    # ── RiskTreatmentPlan ↔ ComplianceActionPlan linking tools ─
    #
    # These tools manage the many-to-many relationship between risk
    # treatment plans and compliance action plans
    # (RiskTreatmentPlan.related_action_plans /
    #  ComplianceActionPlan.related_treatment_plans).
    #
    # Available operations:
    #   - list_treatment_plan_action_plans : list all action plans linked
    #     to a treatment plan
    #   - link_treatment_plan_action_plans : attach action plans (additive)
    #   - unlink_treatment_plan_action_plans : detach selected action plans
    #   - set_treatment_plan_action_plans : replace the full set of links

    ComplianceActionPlan = _get_model("compliance", "ComplianceActionPlan")

    action_plan_link_fields = [
        "id", "reference", "name", "status", "priority",
        "progress_percentage", "owner_id",
    ]

    def _list_treatment_plan_action_plans(user, arguments):
        """Return all compliance action plans linked to a treatment plan."""
        plan_id = arguments.get("treatment_plan_id")
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        items = [
            _serialize_obj(ap, action_plan_link_fields)
            for ap in plan.related_action_plans.all()
        ]
        return {"treatment_plan_id": str(plan_id), "total": len(items), "items": items}

    server.register_tool(
        "list_treatment_plan_action_plans",
        (
            "List all compliance action plans linked to a risk treatment plan. "
            "Returns action plan id, reference, name, status, priority, "
            "progress_percentage and owner_id for each link."
        ),
        _obj_schema(
            {"treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"}},
            required=["treatment_plan_id"],
        ),
        require_perm("risks.treatment.read")(_list_treatment_plan_action_plans),
    )

    def _link_treatment_plan_action_plans(user, arguments):
        """Attach action plans to a treatment plan. Additive: existing links are preserved."""
        plan_id = arguments.get("treatment_plan_id")
        ap_ids = arguments.get("action_plan_ids", [])
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        if not ap_ids:
            raise InvalidParamsError(
                "action_plan_ids is required and must be a non-empty list."
            )
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        existing = set(
            str(pk) for pk in plan.related_action_plans.values_list("pk", flat=True)
        )
        action_plans = ComplianceActionPlan.objects.filter(pk__in=ap_ids)
        if action_plans.count() != len(ap_ids):
            found = set(str(ap.pk) for ap in action_plans)
            missing = [aid for aid in ap_ids if aid not in found]
            return _error(f"Action plans not found: {missing}")
        plan.related_action_plans.add(*action_plans)
        added = len(set(ap_ids) - existing)
        total = plan.related_action_plans.count()
        return {"treatment_plan_id": str(plan_id), "added": added, "total": total}

    server.register_tool(
        "link_treatment_plan_action_plans",
        (
            "Link one or more compliance action plans to a risk treatment plan. "
            "This is additive - existing links are preserved. "
            "Provide a treatment_plan_id and a list of action_plan_ids to attach."
        ),
        _obj_schema(
            {
                "treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"},
                "action_plan_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of compliance action plan UUIDs to link",
                },
            },
            required=["treatment_plan_id", "action_plan_ids"],
        ),
        require_perm("risks.treatment.update")(_link_treatment_plan_action_plans),
    )

    def _unlink_treatment_plan_action_plans(user, arguments):
        """Remove specified action plans from a treatment plan. Other links remain."""
        plan_id = arguments.get("treatment_plan_id")
        ap_ids = arguments.get("action_plan_ids", [])
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        if not ap_ids:
            raise InvalidParamsError(
                "action_plan_ids is required and must be a non-empty list."
            )
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        existing = set(
            str(pk) for pk in plan.related_action_plans.values_list("pk", flat=True)
        )
        removed = len(existing & set(ap_ids))
        plan.related_action_plans.remove(
            *ComplianceActionPlan.objects.filter(pk__in=ap_ids)
        )
        total = plan.related_action_plans.count()
        return {"treatment_plan_id": str(plan_id), "removed": removed, "total": total}

    server.register_tool(
        "unlink_treatment_plan_action_plans",
        (
            "Remove one or more compliance action plans from a risk treatment plan. "
            "Only the specified links are removed; other links are preserved."
        ),
        _obj_schema(
            {
                "treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"},
                "action_plan_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of compliance action plan UUIDs to unlink",
                },
            },
            required=["treatment_plan_id", "action_plan_ids"],
        ),
        require_perm("risks.treatment.update")(_unlink_treatment_plan_action_plans),
    )

    def _set_treatment_plan_action_plans(user, arguments):
        """Replace the entire set of action plans on a treatment plan."""
        plan_id = arguments.get("treatment_plan_id")
        ap_ids = arguments.get("action_plan_ids", [])
        if not plan_id:
            raise InvalidParamsError("treatment_plan_id is required.")
        if not isinstance(ap_ids, list):
            raise InvalidParamsError("action_plan_ids must be a list.")
        try:
            plan = RiskTreatmentPlan.objects.get(pk=plan_id)
        except RiskTreatmentPlan.DoesNotExist:
            return _error("Treatment plan not found.")
        if ap_ids:
            action_plans = ComplianceActionPlan.objects.filter(pk__in=ap_ids)
            if action_plans.count() != len(ap_ids):
                found = set(str(ap.pk) for ap in action_plans)
                missing = [aid for aid in ap_ids if aid not in found]
                return _error(f"Action plans not found: {missing}")
            plan.related_action_plans.set(action_plans)
        else:
            plan.related_action_plans.clear()
        total = plan.related_action_plans.count()
        return {"treatment_plan_id": str(plan_id), "total": total}

    server.register_tool(
        "set_treatment_plan_action_plans",
        (
            "Replace the full set of compliance action plans linked to a "
            "risk treatment plan. All previous links are removed and replaced "
            "by the supplied list. Pass an empty action_plan_ids list to clear "
            "all links."
        ),
        _obj_schema(
            {
                "treatment_plan_id": {"type": "string", "description": "UUID of the treatment plan"},
                "action_plan_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Complete list of compliance action plan UUIDs to link. "
                        "Pass an empty list to remove all links."
                    ),
                },
            },
            required=["treatment_plan_id", "action_plan_ids"],
        ),
        require_perm("risks.treatment.update")(_set_treatment_plan_action_plans),
    )


# ── Accounts Module ────────────────────────────────────────

def _register_accounts_tools(server):
    User = _get_model("accounts", "User")
    Group = _get_model("accounts", "Group")
    Permission = _get_model("accounts", "Permission")
    AccessLog = _get_model("accounts", "AccessLog")

    # List users
    server.register_tool(
        "list_users",
        "List users with optional search",
        _list_schema({
            "is_active": {"type": "boolean", "description": "Filter by active status"},
        }),
        require_perm("system.users.read")(
            _list_handler(User,
                          ["id", "email", "first_name", "last_name", "job_title",
                           "department", "is_active", "last_login", "created_at"],
                          search_fields=["email", "first_name", "last_name"],
                          filters=["is_active"],
                          scope_filtered=False)
        ),
    )

    # Get user
    server.register_tool(
        "get_user",
        "Get detailed information about a user",
        _id_schema(),
        require_perm("system.users.read")(
            _get_handler(User,
                         ["id", "email", "first_name", "last_name", "job_title",
                          "department", "phone", "language", "timezone",
                          "is_active", "last_login", "created_at", "updated_at"],
                         scope_filtered=False)
        ),
    )

    # Get current user info
    def get_me(user, arguments):
        return _serialize_obj(user, ["id", "email", "first_name", "last_name",
                                     "job_title", "department", "language", "timezone"])

    server.register_tool(
        "get_me",
        "Get information about the currently authenticated user",
        {"type": "object", "properties": {}},
        get_me,
    )

    # List groups
    server.register_tool(
        "list_groups",
        "List all groups",
        _list_schema(),
        require_perm("system.groups.read")(
            _list_handler(Group,
                          ["id", "name", "description", "is_system", "created_at"],
                          search_fields=["name"],
                          scope_filtered=False)
        ),
    )

    # Get group details
    @require_perm("system.groups.read")
    def get_group(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            group = Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            return _error("Group not found.")
        perms = list(group.permissions.values_list("codename", flat=True))
        user_count = group.users.count()
        return {
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "is_system": group.is_system,
            "permissions": perms,
            "user_count": user_count,
            "created_at": group.created_at.isoformat(),
        }

    server.register_tool(
        "get_group",
        "Get group details including permissions",
        _id_schema(),
        get_group,
    )

    # List permissions
    server.register_tool(
        "list_permissions",
        "List all available permissions",
        _list_schema({
            "module": {"type": "string", "description": "Filter by module (context, assets, compliance, risks, system)"},
        }),
        require_perm("system.groups.read")(
            _list_handler(Permission,
                          ["id", "codename", "name", "module", "feature", "action"],
                          search_fields=["codename", "name"],
                          filters=["module", "feature"],
                          scope_filtered=False)
        ),
    )

    # List access logs
    server.register_tool(
        "list_access_logs",
        "List access logs (authentication events)",
        _list_schema({
            "event_type": {"type": "string", "description": "Filter by event type"},
            "user_id": {"type": "string", "description": "Filter by user ID"},
        }),
        require_perm("system.audit_trail.read")(
            _list_handler(AccessLog,
                          ["id", "timestamp", "user_id", "email_attempted",
                           "event_type", "ip_address", "failure_reason"],
                          search_fields=["email_attempted"],
                          filters=["event_type", "user_id"],
                          scope_filtered=False)
        ),
    )


# ── Custom supplier handlers (with image_url support) ─────

def _apply_logo_from_url(obj, image_url):
    """Download image from *image_url*, set logo and variants on *obj*."""
    from helpers.image_utils import download_image_to_data_uri, generate_image_variants

    logo_uri = download_image_to_data_uri(image_url)
    variants = generate_image_variants(logo_uri)
    obj.logo = logo_uri
    obj.logo_16 = variants[16]
    obj.logo_32 = variants[32]
    obj.logo_64 = variants[64]


def _create_supplier_handler(model_class, writable_fields):
    """Create handler for supplier that supports image_url."""
    def handler(user, arguments):
        image_url = arguments.pop("image_url", None)
        kwargs = {}
        for field_name in writable_fields:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    model_class, field_name, arguments[field_name])
        if hasattr(model_class, "created_by"):
            kwargs["created_by"] = user
        try:
            obj = model_class(**kwargs)
            if image_url:
                _apply_logo_from_url(obj, image_url)
            obj.full_clean()
            obj.save()
        except (ValueError, ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _update_supplier_with_logo_handler(model_class, writable_fields):
    """Update handler for supplier that supports image_url."""
    def handler(user, arguments):
        image_url = arguments.pop("image_url", None)
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return _error(f"{model_class.__name__} not found.")
        qs = _filter_by_scopes(model_class.objects.filter(pk=pk), user)
        if not qs.exists():
            return _error("Access denied: object is outside your allowed scopes.")
        changed_fields = set()
        for field_name in writable_fields:
            if field_name in arguments:
                setattr(obj, field_name, _coerce_field_value(
                    model_class, field_name, arguments[field_name]))
                changed_fields.add(field_name)
        if image_url:
            try:
                _apply_logo_from_url(obj, image_url)
            except ValueError as e:
                return _error(str(e))
        # Reset approval on update (respects VersioningConfig)
        if hasattr(obj, "is_approved") and hasattr(obj, "version"):
            from core.models import VersioningConfig
            if VersioningConfig.is_approval_enabled(model_class):
                major_fields = VersioningConfig.get_major_fields(model_class)
                is_major = major_fields is None or bool(changed_fields & major_fields)
                if is_major:
                    obj.is_approved = False
                    obj.approved_by = None
                    obj.approved_at = None
                    obj.version = (obj.version or 0) + 1
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _update_supplier_logo_handler(user, arguments):
    """Update a supplier's logo and generate size variants."""
    from helpers.image_utils import download_image_to_data_uri, generate_image_variants

    pk = arguments.get("id")
    logo_uri = arguments.get("logo")
    image_url = arguments.get("image_url")
    if not pk:
        raise InvalidParamsError("id is required.")
    if not logo_uri and not image_url:
        raise InvalidParamsError("Either 'logo' (base64 data URI) or 'image_url' is required.")

    Supplier = apps.get_model("assets", "Supplier")
    try:
        supplier = Supplier.objects.get(pk=pk)
    except Supplier.DoesNotExist:
        return _error("Supplier not found.")

    qs = _filter_by_scopes(Supplier.objects.filter(pk=pk), user)
    if not qs.exists():
        return _error("Access denied: object is outside your allowed scopes.")

    # Resolve logo data URI from URL if provided.
    if image_url and not logo_uri:
        try:
            logo_uri = download_image_to_data_uri(image_url)
        except ValueError as e:
            return _error(str(e))

    try:
        variants = generate_image_variants(logo_uri)
    except Exception as e:
        return _error(f"Invalid image data: {e}")

    supplier.logo = logo_uri
    supplier.logo_16 = variants[16]
    supplier.logo_32 = variants[32]
    supplier.logo_64 = variants[64]

    # Reset approval on update (respects VersioningConfig)
    if hasattr(supplier, "is_approved") and hasattr(supplier, "version"):
        from core.models import VersioningConfig
        if VersioningConfig.is_approval_enabled(supplier.__class__):
            major_fields = VersioningConfig.get_major_fields(supplier.__class__)
            # Logo change: check if "logo" is a major field
            is_major = major_fields is None or "logo" in major_fields
            if is_major:
                supplier.is_approved = False
                supplier.approved_by = None
                supplier.approved_at = None
                supplier.version = (supplier.version or 0) + 1

    try:
        supplier.full_clean()
        supplier.save()
    except (ValidationError, Exception) as e:
        return _error(str(e))

    fields = [f.name for f in Supplier._meta.fields]
    return _serialize_obj(supplier, fields)


# ── Generic CRUD registration helper ──────────────────────

def _register_crud(server, entity_name, model_class, perm_prefix,
                   list_fields, writable_fields, search_fields=None,
                   filters=None, scope_filtered=True, has_approve=True,
                   field_overrides=None, required_fields=None,
                   m2m_fields=None):
    """Register list, get, create, update, delete (and optionally approve) tools for an entity."""

    display_name = entity_name.replace("_", " ")
    filter_props = {}
    for f in (filters or []):
        filter_props[f] = {"type": "string", "description": f"Filter by {f}"}

    # List
    server.register_tool(
        f"list_{entity_name}s",
        f"List {display_name}s with optional search and filters",
        _list_schema(filter_props),
        require_perm(f"{perm_prefix}.read")(
            _list_handler(model_class, list_fields, search_fields, filters, scope_filtered)
        ),
    )

    # Get
    server.register_tool(
        f"get_{entity_name}",
        f"Get a {display_name} by ID",
        _id_schema(),
        require_perm(f"{perm_prefix}.read")(
            _get_handler(model_class, list_fields, scope_filtered)
        ),
    )

    # Create
    overrides = field_overrides or {}
    create_props = {}
    for f in writable_fields:
        create_props[f] = overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        f"create_{entity_name}",
        f"Create a new {display_name}",
        _obj_schema(create_props, required_fields),
        require_perm(f"{perm_prefix}.create")(
            _create_handler(model_class, writable_fields, scope_filtered, m2m_fields)
        ),
    )

    # Batch Create
    server.register_tool(
        f"batch_create_{entity_name}s",
        f"Create multiple {display_name}s in one call (max 500). "
        f"Non-atomic: valid items are created even if others fail. "
        f"Returns per-item status with created count and errors.",
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": _obj_schema(create_props, required_fields),
                    "description": f"Array of {display_name} objects to create (max 500).",
                },
            },
            "required": ["items"],
        },
        require_perm(f"{perm_prefix}.create")(
            _batch_create_handler(model_class, writable_fields, scope_filtered, m2m_fields)
        ),
    )

    # Update
    update_props = {"id": {"type": "string", "description": "UUID of the object to update"}}
    for f in writable_fields:
        update_props[f] = overrides.get(f, {"type": "string", "description": f})
    server.register_tool(
        f"update_{entity_name}",
        f"Update an existing {display_name}",
        _obj_schema(update_props, ["id"]),
        require_perm(f"{perm_prefix}.update")(
            _update_handler(model_class, writable_fields, scope_filtered, m2m_fields)
        ),
    )

    # Delete
    server.register_tool(
        f"delete_{entity_name}",
        f"Delete a {display_name}",
        _id_schema(),
        require_perm(f"{perm_prefix}.delete")(
            _delete_handler(model_class, scope_filtered)
        ),
    )

    # Approve
    if has_approve:
        server.register_tool(
            f"approve_{entity_name}",
            f"Approve a {display_name}",
            _id_schema(),
            require_perm(f"{perm_prefix}.approve")(
                _approve_handler(model_class, scope_filtered)
            ),
        )


# ── Reports Module ────────────────────────────────────────

def _register_reports_tools(server):
    Report = _get_model("reports", "Report")

    report_fields = [
        "id", "report_type", "name", "status", "file_name",
        "created_at", "created_by",
    ]

    # List reports
    @require_perm("reports.report.read")
    def list_reports(user, arguments):
        qs = Report.objects.all()
        report_type = arguments.get("report_type")
        if report_type:
            qs = qs.filter(report_type=report_type)
        limit = min(int(arguments.get("limit", 50)), 200)
        offset = int(arguments.get("offset", 0))
        return _serialize_qs(qs, report_fields, limit, offset)

    server.register_tool(
        "list_reports",
        "List generated reports, optionally filtered by report_type",
        {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "description": "Filter by report type (e.g. 'soa')",
                },
                "limit": {"type": "integer", "description": "Max results (default 50)"},
                "offset": {"type": "integer", "description": "Offset for pagination"},
            },
        },
        list_reports,
    )

    # Generate SoA report
    @require_perm("reports.report.create")
    def generate_soa_report(user, arguments):
        framework_ids = arguments.get("framework_ids")
        if not framework_ids:
            raise InvalidParamsError("framework_ids is required (list of UUIDs).")

        Framework = _get_model("compliance", "Framework")
        frameworks = Framework.objects.filter(id__in=framework_ids)
        if not frameworks.exists():
            return _error("No frameworks found for given IDs.")

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_soa_pdf

        fw_names = ", ".join(fw.short_name or fw.name for fw in frameworks)
        report_name = f"Statement of Applicability — {fw_names}"

        try:
            filename, pdf_bytes = generate_soa_pdf(frameworks, user)
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(frameworks)
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
            )

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_soa_report",
        "Generate a Statement of Applicability (SoA) PDF report for one or more frameworks",
        {
            "type": "object",
            "properties": {
                "framework_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of framework UUIDs to include in the SoA",
                },
            },
            "required": ["framework_ids"],
        },
        generate_soa_report,
    )

    # Generate audit report
    @require_perm("reports.report.create")
    def generate_audit_report(user, arguments):
        assessment_id = arguments.get("assessment_id")
        if not assessment_id:
            raise InvalidParamsError("assessment_id is required (UUID).")

        ComplianceAssessment = _get_model("compliance", "ComplianceAssessment")
        try:
            assessment = ComplianceAssessment.objects.get(pk=assessment_id)
        except ComplianceAssessment.DoesNotExist:
            return _error("Assessment not found.")

        from compliance.constants import AssessmentStatus
        if assessment.status not in (AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED):
            return _error("The assessment must be completed or closed to generate a report.")

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_audit_report_pdf

        report_name = f"Audit report — {assessment.reference} : {assessment.name}"

        try:
            filename, pdf_bytes = generate_audit_report_pdf(assessment, user)
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                assessment=assessment,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(assessment.frameworks.all())
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
                assessment=assessment,
            )

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_audit_report",
        "Generate an audit report PDF for a completed or closed compliance assessment",
        {
            "type": "object",
            "properties": {
                "assessment_id": {
                    "type": "string",
                    "description": "UUID of the compliance assessment (must be completed or closed)",
                },
            },
            "required": ["assessment_id"],
        },
        generate_audit_report,
    )

    # Generate risk register
    @require_perm("risks.export.read")
    def generate_risk_register(user, arguments):
        """Generate an Excel export of the risk register.

        Parameters
        ----------
        scope_ids : list[str], optional
            Restrict the export to risks whose assessment has at least one of
            these scopes. If omitted, the export is filtered by the user's
            allowed scopes (or unfiltered for superusers).
        assessment_id : str, optional
            Restrict the export to risks belonging to this assessment.
        status : str, optional
            Filter by risk status.
        priority : str, optional
            Filter by risk priority.
        """
        Risk = _get_model("risks", "Risk")
        qs = Risk.objects.all()

        # Scope filtering: explicit scope_ids wins; otherwise apply user scopes.
        scope_ids = arguments.get("scope_ids")
        if scope_ids:
            qs = qs.filter(assessment__scopes__id__in=scope_ids).distinct()
        elif not user.is_superuser:
            user_scopes = user.get_allowed_scope_ids()
            if user_scopes is not None:
                qs = qs.filter(assessment__scopes__id__in=user_scopes).distinct()

        assessment_id = arguments.get("assessment_id")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        priority = arguments.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_risk_register_xlsx

        try:
            filename, content = generate_risk_register_xlsx(qs, user)
            report = Report.objects.create(
                report_type=ReportType.RISK_REGISTER,
                name=f"Risk register - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=content,
                file_name=filename,
            )
        except Exception as exc:
            Report.objects.create(
                report_type=ReportType.RISK_REGISTER,
                name="Risk register",
                status=ReportStatus.FAILED,
                created_by=user,
            )
            return _error(f"Failed to generate risk register: {exc}")

        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_risk_register",
        (
            "Generate an Excel (.xlsx) export of the risk register. "
            "Optional filters: scope_ids, assessment_id, status, priority. "
            "When omitted, scope filtering falls back to the user's allowed "
            "scopes. The generated file is persisted as a Report."
        ),
        {
            "type": "object",
            "properties": {
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict to risks under these scope UUIDs.",
                },
                "assessment_id": {
                    "type": "string",
                    "description": "Restrict to risks under this assessment UUID.",
                },
                "status": {"type": "string", "description": "Filter by risk status."},
                "priority": {"type": "string", "description": "Filter by risk priority."},
            },
        },
        generate_risk_register,
    )

    # Delete report
    @require_perm("reports.report.delete")
    def delete_report(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return _error("Report not found.")
        report.delete()
        return {"deleted": True}

    server.register_tool(
        "delete_report",
        "Delete a generated report",
        _id_schema(),
        delete_report,
    )

    # Generate management review (PPTX)
    @require_perm("reports.report.create")
    def generate_management_review_pptx_tool(user, arguments):
        scope_ids = arguments.get("scope_ids")
        period_start = arguments.get("period_start")
        period_end = arguments.get("period_end")
        from datetime import date as date_type
        if period_start:
            period_start = date_type.fromisoformat(period_start)
        if period_end:
            period_end = date_type.fromisoformat(period_end)
        from reports.constants import ReportStatus, ReportType
        from reports.management_review import generate_management_review_pptx

        report_name = "Management review - Presentation"
        try:
            filename, file_bytes = generate_management_review_pptx(
                user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_PPTX,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_PPTX,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
            )
        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_management_review_pptx",
        "Generate a management review presentation (PowerPoint) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities",
        {
            "type": "object",
            "properties": {
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of scope UUIDs to filter data. Omit to include all data.",
                },
                "period_start": {
                    "type": "string",
                    "description": "Start of the review period (YYYY-MM-DD). Omit to include all past data.",
                },
                "period_end": {
                    "type": "string",
                    "description": "End of the review period (YYYY-MM-DD). Defaults to today.",
                },
            },
        },
        generate_management_review_pptx_tool,
    )

    # Generate management review (DOCX)
    @require_perm("reports.report.create")
    def generate_management_review_docx_tool(user, arguments):
        scope_ids = arguments.get("scope_ids")
        period_start = arguments.get("period_start")
        period_end = arguments.get("period_end")
        from datetime import date as date_type
        if period_start:
            period_start = date_type.fromisoformat(period_start)
        if period_end:
            period_end = date_type.fromisoformat(period_end)
        from reports.constants import ReportStatus, ReportType
        from reports.management_review import generate_management_review_docx

        report_name = "Management review - Minutes"
        try:
            filename, file_bytes = generate_management_review_docx(
                user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_DOCX,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            report = Report.objects.create(
                report_type=ReportType.MANAGEMENT_REVIEW_DOCX,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=user,
            )
        return _serialize_obj(report, report_fields)

    server.register_tool(
        "generate_management_review_docx",
        "Generate a management review meeting minutes document (Word) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities",
        {
            "type": "object",
            "properties": {
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of scope UUIDs to filter data. Omit to include all data.",
                },
                "period_start": {
                    "type": "string",
                    "description": "Start of the review period (YYYY-MM-DD). Omit to include all past data.",
                },
                "period_end": {
                    "type": "string",
                    "description": "End of the review period (YYYY-MM-DD). Defaults to today.",
                },
            },
        },
        generate_management_review_docx_tool,
    )

    # ═══════════════════════════════════════════════════════════════
    # Persistent management reviews (ISO 27001:2022 clause 9.3)
    # ═══════════════════════════════════════════════════════════════

    MR_FIELDS = [
        "id", "reference", "title", "description",
        "frequency", "period_start", "period_end",
        "planned_date", "held_date", "location", "status",
        "facilitator", "approver", "next_review_date",
        "summary", "is_approved", "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.read")
    def list_management_reviews(user, arguments):
        """List management reviews with optional filters."""
        MR = _get_model("reports", "ManagementReview")
        qs = MR.objects.all()
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        scope_id = arguments.get("scope_id")
        if scope_id:
            qs = qs.filter(scopes__id=scope_id)
        qs = qs.order_by("-planned_date")
        return _serialize_qs(
            qs, fields=MR_FIELDS,
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )

    server.register_tool(
        "list_management_reviews",
        "List management reviews (ISO 27001:2022 clause 9.3). Filter by status or scope.",
        {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "planned|in_preparation|held|closed|cancelled"},
                "scope_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_management_reviews,
    )

    @require_perm("reports.management_review.read")
    def get_management_review(user, arguments):
        MR = _get_model("reports", "ManagementReview")
        review_id = arguments.get("id")
        if not review_id:
            return _error("id is required")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error(f"Management review {review_id} not found")
        data = _serialize_obj(review, MR_FIELDS)
        data["decisions_count"] = review.decisions.count()
        data["isms_changes_count"] = review.isms_changes.count()
        data["participants_count"] = review.participants.count()
        data["has_snapshot"] = review.has_snapshot
        return data

    server.register_tool(
        "get_management_review",
        "Get a management review by ID.",
        {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        get_management_review,
    )

    @require_perm("reports.management_review.create")
    def create_management_review(user, arguments):
        MR = _get_model("reports", "ManagementReview")
        User = _get_model("accounts", "User")
        required = ["title", "frequency", "period_start", "period_end", "planned_date", "facilitator_id"]
        for field in required:
            if not arguments.get(field):
                return _error(f"{field} is required")
        try:
            facilitator = User.objects.get(pk=arguments["facilitator_id"])
        except User.DoesNotExist:
            return _error("facilitator not found")
        review = MR.objects.create(
            title=arguments["title"],
            description=arguments.get("description", ""),
            frequency=arguments["frequency"],
            period_start=arguments["period_start"],
            period_end=arguments["period_end"],
            planned_date=arguments["planned_date"],
            location=arguments.get("location", ""),
            facilitator=facilitator,
            created_by=user,
        )
        scope_ids = arguments.get("scope_ids") or []
        if scope_ids:
            review.scopes.set(scope_ids)
        return _serialize_obj(review, MR_FIELDS)

    server.register_tool(
        "create_management_review",
        "Create a management review (ISO 27001:2022 clause 9.3).",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "frequency": {"type": "string", "description": "quarterly|semiannual|annual|exceptional"},
                "period_start": {"type": "string", "description": "YYYY-MM-DD"},
                "period_end": {"type": "string", "description": "YYYY-MM-DD"},
                "planned_date": {"type": "string", "description": "YYYY-MM-DD"},
                "location": {"type": "string"},
                "facilitator_id": {"type": "string"},
                "scope_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "frequency", "period_start", "period_end", "planned_date", "facilitator_id"],
        },
        create_management_review,
    )

    @require_perm("reports.management_review.update")
    def transition_management_review(user, arguments):
        MR = _get_model("reports", "ManagementReview")
        review_id = arguments.get("id")
        target = arguments.get("target_status")
        comment = arguments.get("comment", "")
        if not review_id or not target:
            return _error("id and target_status are required")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error("review not found")
        if target == "closed" and not user.has_perm("reports.management_review.approve"):
            return _error("Closure requires approve permission")
        try:
            review.transition_to(target, user, comment=comment)
        except ValueError as exc:
            return _error(str(exc))
        if review.status == "closed":
            from reports.management_review import gather_management_review_data
            from reports.management_review_views import _serialize_snapshot
            try:
                scope_ids = list(review.scopes.values_list("id", flat=True))
                data = gather_management_review_data(
                    user, scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                )
                review.take_snapshot(_serialize_snapshot(data))
            except Exception:
                pass
        return _serialize_obj(review, MR_FIELDS)

    server.register_tool(
        "transition_management_review",
        "Transition a management review to a new status (planned -> in_preparation -> held -> closed, or cancelled).",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "target_status": {"type": "string"},
                "comment": {"type": "string"},
            },
            "required": ["id", "target_status"],
        },
        transition_management_review,
    )

    @require_perm("reports.management_review.read")
    def export_management_review(user, arguments):
        """Return a base64-encoded export (DOCX or PPTX) of a management review."""
        import base64 as _b64
        MR = _get_model("reports", "ManagementReview")
        review_id = arguments.get("id")
        fmt = arguments.get("format", "docx")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error("review not found")
        scope_ids = list(review.scopes.values_list("id", flat=True))
        from reports.management_review import (
            generate_management_review_docx,
            generate_management_review_pptx,
        )
        gen = generate_management_review_pptx if fmt == "pptx" else generate_management_review_docx
        try:
            filename, data = gen(
                user, scope_ids=scope_ids,
                period_start=review.period_start,
                period_end=review.period_end,
                review=review,
            )
        except Exception as exc:
            return _error(f"Export failed: {exc}")
        return {
            "filename": filename,
            "format": fmt,
            "content_base64": _b64.b64encode(data).decode("ascii"),
            "size_bytes": len(data),
        }

    server.register_tool(
        "export_management_review",
        "Export a management review as DOCX (meeting minutes) or PPTX (presentation). Returns base64-encoded content.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "format": {"type": "string", "description": "docx|pptx", "default": "docx"},
            },
            "required": ["id"],
        },
        export_management_review,
    )

    DECISION_FIELDS = [
        "id", "reference", "review", "category", "input_clause",
        "title", "description", "owner", "due_date", "priority",
        "status", "linked_action_plan", "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.read")
    def list_management_review_decisions(user, arguments):
        D = _get_model("reports", "ManagementReviewDecision")
        qs = D.objects.all()
        review_id = arguments.get("review_id")
        if review_id:
            qs = qs.filter(review_id=review_id)
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return _serialize_qs(qs, fields=DECISION_FIELDS,
                             limit=int(arguments.get("limit", 50)),
                             offset=int(arguments.get("offset", 0)))

    server.register_tool(
        "list_management_review_decisions",
        "List decisions (ISO 27001:2022 clause 9.3.3 outputs). Filter by review or status.",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_management_review_decisions,
    )

    @require_perm("reports.management_review.update")
    def create_management_review_decision(user, arguments):
        D = _get_model("reports", "ManagementReviewDecision")
        MR = _get_model("reports", "ManagementReview")
        User = _get_model("accounts", "User")
        review_id = arguments.get("review_id")
        if not review_id:
            return _error("review_id is required")
        try:
            review = MR.objects.get(pk=review_id)
        except MR.DoesNotExist:
            return _error("review not found")
        owner = None
        if arguments.get("owner_id"):
            try:
                owner = User.objects.get(pk=arguments["owner_id"])
            except User.DoesNotExist:
                return _error("owner not found")
        decision = D.objects.create(
            review=review,
            category=arguments.get("category", "improvement"),
            input_clause=arguments.get("input_clause", ""),
            title=arguments.get("title", ""),
            description=arguments.get("description", ""),
            rationale=arguments.get("rationale", ""),
            owner=owner,
            due_date=arguments.get("due_date") or None,
            priority=arguments.get("priority", "medium"),
            status=arguments.get("status", "pending"),
        )
        return _serialize_obj(decision, DECISION_FIELDS)

    server.register_tool(
        "create_management_review_decision",
        "Record a decision from a management review (ISO 27001:2022 clause 9.3.3).",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "category": {"type": "string", "description": "improvement|isms_change|resource_allocation|risk_acceptance|objective_adjustment|policy_update|other"},
                "input_clause": {"type": "string", "description": "9.3.2 clause letter: a|b|c|d1|d2|d3|d4|e|f|g"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "rationale": {"type": "string"},
                "owner_id": {"type": "string"},
                "due_date": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["review_id", "title", "description"],
        },
        create_management_review_decision,
    )

    @require_perm("reports.management_review.update")
    def promote_decision_to_action_plan(user, arguments):
        """Create a ComplianceActionPlan from a decision and link them."""
        D = _get_model("reports", "ManagementReviewDecision")
        AP = _get_model("compliance", "ComplianceActionPlan")
        decision_id = arguments.get("decision_id")
        if not user.has_perm("compliance.action_plan.create"):
            return _error("Missing compliance.action_plan.create permission")
        try:
            decision = D.objects.get(pk=decision_id)
        except D.DoesNotExist:
            return _error("decision not found")
        if decision.linked_action_plan_id:
            return _error("Decision already linked to an action plan")
        plan = AP.objects.create(
            name=decision.title,
            description=decision.description,
            gap_description=decision.description,
            remediation_plan=decision.rationale or decision.description,
            priority=decision.priority,
            owner=decision.owner or user,
            target_date=decision.due_date,
            originating_review=decision.review,
            created_by=user,
        )
        plan.scopes.set(decision.review.scopes.all())
        decision.linked_action_plan = plan
        if decision.status == "pending":
            decision.status = "in_progress"
        decision.save(update_fields=["linked_action_plan", "status", "updated_at"])
        return {"action_plan_id": str(plan.pk), "action_plan_reference": plan.reference}

    server.register_tool(
        "promote_decision_to_action_plan",
        "Create a ComplianceActionPlan from a management review decision.",
        {
            "type": "object",
            "properties": {"decision_id": {"type": "string"}},
            "required": ["decision_id"],
        },
        promote_decision_to_action_plan,
    )

    ISMS_CHANGE_FIELDS = [
        "id", "reference", "review", "change_type", "title",
        "description", "owner", "status", "target_date", "implemented_at",
        "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.read")
    def list_isms_changes(user, arguments):
        C = _get_model("reports", "IsmsChange")
        qs = C.objects.all()
        review_id = arguments.get("review_id")
        if review_id:
            qs = qs.filter(review_id=review_id)
        return _serialize_qs(qs, fields=ISMS_CHANGE_FIELDS,
                             limit=int(arguments.get("limit", 50)),
                             offset=int(arguments.get("offset", 0)))

    server.register_tool(
        "list_isms_changes",
        "List ISMS changes decided during management reviews (ISO 27001:2022 clause 9.3.3).",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_isms_changes,
    )

    @require_perm("reports.management_review.update")
    def create_isms_change(user, arguments):
        C = _get_model("reports", "IsmsChange")
        MR = _get_model("reports", "ManagementReview")
        User = _get_model("accounts", "User")
        review_id = arguments.get("review_id")
        owner_id = arguments.get("owner_id")
        if not review_id or not owner_id:
            return _error("review_id and owner_id are required")
        try:
            review = MR.objects.get(pk=review_id)
            owner = User.objects.get(pk=owner_id)
        except (MR.DoesNotExist, User.DoesNotExist):
            return _error("review or owner not found")
        change = C.objects.create(
            review=review,
            change_type=arguments.get("change_type", "other"),
            title=arguments.get("title", ""),
            description=arguments.get("description", ""),
            impact_analysis=arguments.get("impact_analysis", ""),
            affected_policies=arguments.get("affected_policies", ""),
            owner=owner,
            status=arguments.get("status", "proposed"),
            target_date=arguments.get("target_date") or None,
        )
        return _serialize_obj(change, ISMS_CHANGE_FIELDS)

    server.register_tool(
        "create_isms_change",
        "Record an ISMS change decided during a management review.",
        {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "change_type": {"type": "string", "description": "scope|policy|control|organization|resource|process|other"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "impact_analysis": {"type": "string"},
                "affected_policies": {"type": "string"},
                "owner_id": {"type": "string"},
                "status": {"type": "string"},
                "target_date": {"type": "string"},
            },
            "required": ["review_id", "title", "description", "owner_id"],
        },
        create_isms_change,
    )

    FEEDBACK_FIELDS = [
        "id", "reference", "stakeholder", "channel", "received_date",
        "subject", "content", "sentiment", "severity", "status",
        "created_at", "updated_at",
    ]

    @require_perm("reports.management_review.update")
    def set_participant_signature(user, arguments):
        """Set a base64 PNG/JPEG signature on a participant.

        Non-eIDAS qualified signature. Any user with management_review.update
        can sign on behalf of participants.
        """
        P = _get_model("reports", "ManagementReviewParticipant")
        participant_id = arguments.get("participant_id")
        data_uri = arguments.get("signature_data_uri", "")
        if not participant_id or not data_uri.startswith("data:image/"):
            return _error("participant_id and a valid signature_data_uri (data:image/...) are required")
        try:
            participant = P.objects.get(pk=participant_id)
        except P.DoesNotExist:
            return _error("participant not found")
        participant.signature_data = data_uri
        participant.attended = True
        participant.save(update_fields=["signature_data", "attended"])
        return {
            "participant_id": str(participant.pk),
            "signed": True,
            "attended": participant.attended,
        }

    server.register_tool(
        "set_participant_signature",
        "Attach a graphical signature (data URI) to a participant for DOCX embedding.",
        {
            "type": "object",
            "properties": {
                "participant_id": {"type": "string"},
                "signature_data_uri": {
                    "type": "string",
                    "description": "Data URI, e.g. data:image/png;base64,iVBORw0KGgo...",
                },
            },
            "required": ["participant_id", "signature_data_uri"],
        },
        set_participant_signature,
    )

    @require_perm("context.stakeholder_feedback.read")
    def list_stakeholder_feedback(user, arguments):
        F = _get_model("context", "StakeholderFeedback")
        qs = F.objects.all()
        stakeholder_id = arguments.get("stakeholder_id")
        if stakeholder_id:
            qs = qs.filter(stakeholder_id=stakeholder_id)
        status_filter = arguments.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return _serialize_qs(qs, fields=FEEDBACK_FIELDS,
                             limit=int(arguments.get("limit", 50)),
                             offset=int(arguments.get("offset", 0)))

    server.register_tool(
        "list_stakeholder_feedback",
        "List formal stakeholder feedback (ISO 27001:2022 clause 9.3.2.e).",
        {
            "type": "object",
            "properties": {
                "stakeholder_id": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
        },
        list_stakeholder_feedback,
    )

    @require_perm("context.stakeholder_feedback.create")
    def create_stakeholder_feedback(user, arguments):
        F = _get_model("context", "StakeholderFeedback")
        S = _get_model("context", "Stakeholder")
        stakeholder_id = arguments.get("stakeholder_id")
        if not stakeholder_id:
            return _error("stakeholder_id is required")
        try:
            stakeholder = S.objects.get(pk=stakeholder_id)
        except S.DoesNotExist:
            return _error("stakeholder not found")
        feedback = F.objects.create(
            stakeholder=stakeholder,
            channel=arguments.get("channel", "other"),
            received_date=arguments.get("received_date"),
            subject=arguments.get("subject", ""),
            content=arguments.get("content", ""),
            sentiment=arguments.get("sentiment", ""),
            severity=arguments.get("severity", ""),
            status=arguments.get("status", "new"),
            response=arguments.get("response", ""),
            created_by=user,
        )
        scope_ids = arguments.get("scope_ids") or []
        if scope_ids:
            feedback.scopes.set(scope_ids)
        return _serialize_obj(feedback, FEEDBACK_FIELDS)

    server.register_tool(
        "create_stakeholder_feedback",
        "Record formal feedback from an interested party (ISO 27001:2022 clause 9.3.2.e).",
        {
            "type": "object",
            "properties": {
                "stakeholder_id": {"type": "string"},
                "channel": {"type": "string", "description": "survey|meeting|complaint|email|audit|incident|other"},
                "received_date": {"type": "string"},
                "subject": {"type": "string"},
                "content": {"type": "string"},
                "sentiment": {"type": "string"},
                "severity": {"type": "string"},
                "status": {"type": "string"},
                "response": {"type": "string"},
                "scope_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["stakeholder_id", "received_date", "subject", "content"],
        },
        create_stakeholder_feedback,
    )

    # ── Company Settings ───────────────────────────────────

    company_fields = ["id", "name", "address", "updated_at"]

    @require_perm("system.config.read")
    def get_company_settings(user, arguments):
        CompanySettings = _get_model("accounts", "CompanySettings")
        instance = CompanySettings.get()
        return _serialize_obj(instance, company_fields)

    server.register_tool(
        "get_company_settings",
        "Get the company settings (name, address)",
        {"type": "object", "properties": {}},
        get_company_settings,
    )

    @require_perm("system.config.update")
    def update_company_settings(user, arguments):
        CompanySettings = _get_model("accounts", "CompanySettings")
        instance = CompanySettings.get()
        if "name" in arguments:
            instance.name = arguments["name"]
        if "address" in arguments:
            instance.address = arguments["address"]
        instance.save()
        return _serialize_obj(instance, company_fields)

    server.register_tool(
        "update_company_settings",
        "Update company settings (name and/or address)",
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Company name",
                },
                "address": {
                    "type": "string",
                    "description": "Company address (multi-line)",
                },
            },
        },
        update_company_settings,
    )
