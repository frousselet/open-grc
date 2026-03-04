"""
MCP tool definitions covering all Open GRC API functionality.

Each tool maps to one or more API endpoints and performs operations
using the Django ORM directly, respecting the user's permissions.

Schemas include full type information, enum values, and descriptions
to enable LLM clients to use the API correctly without external docs.
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


def _create_handler(model_class, writable_fields, scope_filtered=True):
    """Create a generic create handler."""
    def handler(user, arguments):
        kwargs = {}
        for field_name in writable_fields:
            if field_name in arguments:
                kwargs[field_name] = arguments[field_name]
        if hasattr(model_class, "created_by"):
            kwargs["created_by"] = user
        try:
            obj = model_class(**kwargs)
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        fields = [f.name for f in model_class._meta.fields]
        return _serialize_obj(obj, fields)
    return handler


def _update_handler(model_class, writable_fields, scope_filtered=True):
    """Create a generic update handler."""
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
        for field_name in writable_fields:
            if field_name in arguments:
                setattr(obj, field_name, arguments[field_name])
        # Reset approval on update (like ApprovableAPIMixin)
        if hasattr(obj, "is_approved"):
            obj.is_approved = False
            obj.approved_by = None
            obj.approved_at = None
        if hasattr(obj, "version"):
            obj.version = (obj.version or 0) + 1
        try:
            obj.full_clean()
            obj.save()
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


# ── Tool registration ──────────────────────────────────────

def register_all_tools(server):
    """Register all MCP tools on the given McpServer instance."""
    _register_context_tools(server)
    _register_assets_tools(server)
    _register_compliance_tools(server)
    _register_risks_tools(server)
    _register_accounts_tools(server)
    _register_helpers_tools(server)


# ── Generic CRUD registration helper ──────────────────────

def _register_crud(server, entity_name, model_class, perm_prefix,
                   list_fields, writable_fields, search_fields=None,
                   filters=None, scope_filtered=True, has_approve=True,
                   field_schemas=None, filter_schemas=None,
                   required_create_fields=None, entity_description=None):
    """Register list, get, create, update, delete (and optionally approve) tools.

    Args:
        field_schemas: dict mapping field names to JSON Schema property dicts.
                       Used for create/update schemas.
        filter_schemas: dict mapping filter names to JSON Schema property dicts.
                       Used for list schema filter parameters.
        required_create_fields: list of field names required for create.
        entity_description: detailed description of the entity for tool docs.
    """
    display_name = entity_name.replace("_", " ")
    desc = entity_description or display_name

    # Build list schema
    list_props = {
        "search": {"type": "string", "description": "Full-text search across name, description, and reference fields."},
        "limit": {"type": "integer", "description": "Maximum number of items to return (default 25, max 100).", "default": 25, "minimum": 1, "maximum": 100},
        "offset": {"type": "integer", "description": "Number of items to skip for pagination (default 0).", "default": 0, "minimum": 0},
    }
    if filter_schemas:
        list_props.update(filter_schemas)
    elif filters:
        for f in filters:
            fs = field_schemas.get(f, {}) if field_schemas else {}
            list_props[f] = fs if fs else {"type": "string", "description": f"Filter by {f}"}

    list_schema = {"type": "object", "properties": list_props}

    # List
    server.register_tool(
        f"list_{entity_name}s",
        f"List {desc}s with optional search and filters. Returns paginated results. "
        f"Supports full-text search and filtering by specific fields.",
        list_schema,
        require_perm(f"{perm_prefix}.read")(
            _list_handler(model_class, list_fields, search_fields, filters, scope_filtered)
        ),
    )

    # Get
    server.register_tool(
        f"get_{entity_name}",
        f"Get a single {desc} by its UUID. Returns all fields.",
        _id_schema(),
        require_perm(f"{perm_prefix}.read")(
            _get_handler(model_class, list_fields, scope_filtered)
        ),
    )

    # Create
    create_props = {}
    for f in writable_fields:
        if field_schemas and f in field_schemas:
            create_props[f] = field_schemas[f]
        else:
            create_props[f] = {"type": "string", "description": f}

    server.register_tool(
        f"create_{entity_name}",
        f"Create a new {desc}. The 'created_by' field is automatically set to the current user. "
        f"A unique reference is generated automatically.",
        _obj_schema(create_props, required_create_fields),
        require_perm(f"{perm_prefix}.create")(
            _create_handler(model_class, writable_fields, scope_filtered)
        ),
    )

    # Update
    update_props = {"id": {"type": "string", "description": "UUID of the object to update"}}
    for f in writable_fields:
        if field_schemas and f in field_schemas:
            update_props[f] = field_schemas[f]
        else:
            update_props[f] = {"type": "string", "description": f}

    server.register_tool(
        f"update_{entity_name}",
        f"Update an existing {desc}. Only provide fields that need to change. "
        f"Updating resets approval status (is_approved=false) and increments version.",
        _obj_schema(update_props, ["id"]),
        require_perm(f"{perm_prefix}.update")(
            _update_handler(model_class, writable_fields, scope_filtered)
        ),
    )

    # Delete
    server.register_tool(
        f"delete_{entity_name}",
        f"Permanently delete a {desc} by its UUID.",
        _id_schema(),
        require_perm(f"{perm_prefix}.delete")(
            _delete_handler(model_class, scope_filtered)
        ),
    )

    # Approve
    if has_approve:
        server.register_tool(
            f"approve_{entity_name}",
            f"Approve a {desc}. Sets is_approved=true, records the approver and timestamp.",
            _id_schema(),
            require_perm(f"{perm_prefix}.approve")(
                _approve_handler(model_class, scope_filtered)
            ),
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

    # ── Scope ──────────────────────────────────────────────
    _register_crud(
        server, "scope", Scope, "context.scope",
        list_fields=["id", "reference", "name", "description", "status",
                      "boundaries", "geographic_scope", "organizational_scope",
                      "technical_scope", "effective_date", "review_date",
                      "parent_scope_id", "icon", "version", "is_approved",
                      "created_at", "updated_at"],
        writable_fields=["name", "description", "status", "boundaries",
                          "justification_exclusions", "geographic_scope",
                          "organizational_scope", "technical_scope",
                          "effective_date", "review_date", "parent_scope_id", "icon"],
        search_fields=["name", "description", "reference"],
        filters=["status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the ISMS scope (e.g. 'Headquarters IT', 'Cloud Services')."},
            "description": {"type": "string", "description": "Detailed description of what the scope covers."},
            "status": {"type": "string", "description": "Current lifecycle status of the scope.", "enum": ["draft", "active", "archived"]},
            "boundaries": {"type": "string", "description": "Explicit boundaries and exclusions of the scope."},
            "justification_exclusions": {"type": "string", "description": "Justification for any exclusions from the scope."},
            "geographic_scope": {"type": "string", "description": "Geographic coverage (countries, regions, sites)."},
            "organizational_scope": {"type": "string", "description": "Organizational units, departments, or teams included."},
            "technical_scope": {"type": "string", "description": "Technical systems, networks, or applications included."},
            "effective_date": {"type": "string", "format": "date", "description": "Date when the scope becomes effective (YYYY-MM-DD)."},
            "review_date": {"type": "string", "format": "date", "description": "Next scheduled review date (YYYY-MM-DD)."},
            "parent_scope_id": {"type": "string", "description": "UUID of the parent scope for hierarchical organization. Null for root scopes."},
            "icon": {"type": "string", "description": "Bootstrap Icons class name (e.g. 'bi-building', 'bi-globe', 'bi-shield-lock')."},
        },
        filter_schemas={
            "status": {"type": "string", "description": "Filter by lifecycle status.", "enum": ["draft", "active", "archived"]},
        },
        required_create_fields=["name", "description"],
        entity_description="scope (defines the boundaries of the ISMS - Information Security Management System)",
    )

    # ── Issue ──────────────────────────────────────────────
    _register_crud(
        server, "issue", Issue, "context.issue",
        list_fields=["id", "reference", "name", "description", "type", "category",
                      "impact_level", "trend", "source", "status",
                      "review_date", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "category",
                          "impact_level", "trend", "source", "status", "review_date"],
        search_fields=["name", "description", "reference"],
        filters=["type", "category", "impact_level", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Title of the internal or external issue."},
            "description": {"type": "string", "description": "Detailed description of the issue and its context."},
            "type": {"type": "string", "description": "Whether the issue is internal or external to the organization.", "enum": ["internal", "external"]},
            "category": {
                "type": "string",
                "description": "Category of the issue. Internal issues: strategic, organizational, human_resources, technical, financial, cultural. External issues: political, economic, social, technological, legal, environmental, competitive, regulatory.",
                "enum": ["strategic", "organizational", "human_resources", "technical", "financial", "cultural",
                         "political", "economic", "social", "technological", "legal", "environmental", "competitive", "regulatory"],
            },
            "impact_level": {"type": "string", "description": "Assessed level of impact on the organization.", "enum": ["low", "medium", "high", "critical"]},
            "trend": {"type": "string", "description": "Current trend of the issue.", "enum": ["improving", "stable", "degrading"]},
            "source": {"type": "string", "description": "Source or origin of the issue (free text)."},
            "status": {"type": "string", "description": "Current status of the issue.", "enum": ["identified", "active", "monitored", "closed"]},
            "review_date": {"type": "string", "format": "date", "description": "Next scheduled review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by issue type.", "enum": ["internal", "external"]},
            "category": {"type": "string", "description": "Filter by category.", "enum": ["strategic", "organizational", "human_resources", "technical", "financial", "cultural", "political", "economic", "social", "technological", "legal", "environmental", "competitive", "regulatory"]},
            "impact_level": {"type": "string", "description": "Filter by impact level.", "enum": ["low", "medium", "high", "critical"]},
            "status": {"type": "string", "description": "Filter by issue status.", "enum": ["identified", "active", "monitored", "closed"]},
        },
        required_create_fields=["name", "type", "category", "impact_level"],
        entity_description="issue (internal or external context issue per ISO 27001 clause 4.1)",
    )

    # ── Stakeholder ────────────────────────────────────────
    _register_crud(
        server, "stakeholder", Stakeholder, "context.stakeholder",
        list_fields=["id", "reference", "name", "type", "category",
                      "description", "contact_name", "contact_email",
                      "influence_level", "interest_level", "status",
                      "review_date", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "type", "category", "description",
                          "contact_name", "contact_email", "contact_phone",
                          "influence_level", "interest_level", "status", "review_date"],
        search_fields=["name", "description", "reference", "contact_name"],
        filters=["type", "category", "influence_level", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the interested party / stakeholder."},
            "type": {"type": "string", "description": "Whether this stakeholder is internal or external.", "enum": ["internal", "external"]},
            "category": {
                "type": "string",
                "description": "Category of the stakeholder.",
                "enum": ["executive_management", "employees", "customers", "suppliers", "partners",
                         "regulators", "shareholders", "insurers", "public", "competitors",
                         "unions", "auditors", "other"],
            },
            "description": {"type": "string", "description": "Detailed description of the stakeholder."},
            "contact_name": {"type": "string", "description": "Name of the primary contact person."},
            "contact_email": {"type": "string", "format": "email", "description": "Email of the primary contact."},
            "contact_phone": {"type": "string", "description": "Phone number of the primary contact."},
            "influence_level": {"type": "string", "description": "Level of influence this stakeholder has.", "enum": ["low", "medium", "high"]},
            "interest_level": {"type": "string", "description": "Level of interest this stakeholder has.", "enum": ["low", "medium", "high"]},
            "status": {"type": "string", "description": "Current status.", "enum": ["active", "inactive"]},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by internal/external type.", "enum": ["internal", "external"]},
            "category": {"type": "string", "description": "Filter by stakeholder category.", "enum": ["executive_management", "employees", "customers", "suppliers", "partners", "regulators", "shareholders", "insurers", "public", "competitors", "unions", "auditors", "other"]},
            "influence_level": {"type": "string", "description": "Filter by influence level.", "enum": ["low", "medium", "high"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "inactive"]},
        },
        required_create_fields=["name", "type", "category", "influence_level", "interest_level"],
        entity_description="stakeholder (interested party per ISO 27001 clause 4.2)",
    )

    # ── Stakeholder Expectation ────────────────────────────
    _register_crud(
        server, "expectation", StakeholderExpectation, "context.expectation",
        list_fields=["id", "stakeholder_id", "description", "type",
                      "priority", "is_applicable", "created_at", "updated_at"],
        writable_fields=["stakeholder_id", "description", "type",
                          "priority", "is_applicable"],
        search_fields=["description"],
        filters=["stakeholder_id", "type", "priority"],
        field_schemas={
            "stakeholder_id": {"type": "string", "description": "UUID of the parent stakeholder."},
            "description": {"type": "string", "description": "Description of the expectation, requirement, or need."},
            "type": {"type": "string", "description": "Type of expectation.", "enum": ["requirement", "expectation", "need"]},
            "priority": {"type": "string", "description": "Priority level.", "enum": ["low", "medium", "high", "critical"]},
            "is_applicable": {"type": "boolean", "description": "Whether this expectation is applicable to the ISMS."},
        },
        filter_schemas={
            "stakeholder_id": {"type": "string", "description": "Filter by parent stakeholder UUID."},
            "type": {"type": "string", "description": "Filter by expectation type.", "enum": ["requirement", "expectation", "need"]},
            "priority": {"type": "string", "description": "Filter by priority.", "enum": ["low", "medium", "high", "critical"]},
        },
        required_create_fields=["stakeholder_id", "description", "type", "priority"],
        scope_filtered=False,
        has_approve=False,
        entity_description="stakeholder expectation (requirement, expectation, or need from an interested party)",
    )

    # ── Objective ──────────────────────────────────────────
    _register_crud(
        server, "objective", Objective, "context.objective",
        list_fields=["id", "reference", "name", "description", "category", "type",
                      "target_value", "current_value", "unit", "measurement_frequency",
                      "target_date", "owner_id", "status", "progress_percentage",
                      "parent_objective_id", "review_date",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "category", "type",
                          "target_value", "current_value", "unit",
                          "measurement_method", "measurement_frequency",
                          "target_date", "owner_id", "status",
                          "progress_percentage", "parent_objective_id", "review_date"],
        search_fields=["name", "description", "reference"],
        filters=["category", "type", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Title of the security or business objective."},
            "description": {"type": "string", "description": "Detailed description of the objective."},
            "category": {"type": "string", "description": "Security category.", "enum": ["confidentiality", "integrity", "availability", "compliance", "operational", "strategic"]},
            "type": {"type": "string", "description": "Objective type.", "enum": ["security", "compliance", "business", "other"]},
            "target_value": {"type": "string", "description": "Target value to achieve (e.g. '95%', '100')."},
            "current_value": {"type": "string", "description": "Current measured value."},
            "unit": {"type": "string", "description": "Unit of measure (e.g. '%', 'days', 'count')."},
            "measurement_method": {"type": "string", "description": "How the objective is measured."},
            "measurement_frequency": {"type": "string", "description": "How often the objective is measured.", "enum": ["daily", "weekly", "monthly", "quarterly", "semi_annual", "annual"]},
            "target_date": {"type": "string", "format": "date", "description": "Target achievement date (YYYY-MM-DD)."},
            "owner_id": {"type": "string", "description": "UUID of the user who owns this objective."},
            "status": {"type": "string", "description": "Current status. Note: 'achieved' requires progress_percentage=100.", "enum": ["draft", "active", "achieved", "not_achieved", "cancelled"]},
            "progress_percentage": {"type": "integer", "description": "Progress towards the objective (0-100).", "minimum": 0, "maximum": 100},
            "parent_objective_id": {"type": "string", "description": "UUID of the parent objective for hierarchical decomposition."},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "category": {"type": "string", "description": "Filter by category.", "enum": ["confidentiality", "integrity", "availability", "compliance", "operational", "strategic"]},
            "type": {"type": "string", "description": "Filter by type.", "enum": ["security", "compliance", "business", "other"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "active", "achieved", "not_achieved", "cancelled"]},
        },
        required_create_fields=["name", "category", "type", "owner_id"],
        entity_description="objective (security or business objective per ISO 27001 clause 6.2)",
    )

    # ── SWOT Analysis ──────────────────────────────────────
    _register_crud(
        server, "swot_analysis", SwotAnalysis, "context.swot",
        list_fields=["id", "reference", "name", "description", "analysis_date",
                      "status", "validated_by_id", "validated_at", "review_date",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "analysis_date", "status", "review_date"],
        search_fields=["name", "description", "reference"],
        filters=["status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the SWOT analysis."},
            "description": {"type": "string", "description": "Description or context of the analysis."},
            "analysis_date": {"type": "string", "format": "date", "description": "Date when the analysis was performed (YYYY-MM-DD)."},
            "status": {"type": "string", "description": "Status of the analysis.", "enum": ["draft", "validated", "archived"]},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "validated", "archived"]},
        },
        required_create_fields=["name", "analysis_date"],
        entity_description="SWOT analysis (Strengths, Weaknesses, Opportunities, Threats)",
    )

    # ── SWOT Item ──────────────────────────────────────────
    _register_crud(
        server, "swot_item", SwotItem, "context.swot",
        list_fields=["id", "swot_analysis_id", "quadrant", "description",
                      "impact_level", "order", "created_at", "updated_at"],
        writable_fields=["swot_analysis_id", "quadrant", "description",
                          "impact_level", "order"],
        search_fields=["description"],
        filters=["swot_analysis_id", "quadrant"],
        field_schemas={
            "swot_analysis_id": {"type": "string", "description": "UUID of the parent SWOT analysis."},
            "quadrant": {"type": "string", "description": "Which SWOT quadrant this item belongs to.", "enum": ["strength", "weakness", "opportunity", "threat"]},
            "description": {"type": "string", "description": "Description of the SWOT item."},
            "impact_level": {"type": "string", "description": "Assessed impact level.", "enum": ["low", "medium", "high"]},
            "order": {"type": "integer", "description": "Display order within the quadrant.", "minimum": 0},
        },
        filter_schemas={
            "swot_analysis_id": {"type": "string", "description": "Filter by parent SWOT analysis UUID."},
            "quadrant": {"type": "string", "description": "Filter by quadrant.", "enum": ["strength", "weakness", "opportunity", "threat"]},
        },
        required_create_fields=["swot_analysis_id", "quadrant", "description", "impact_level"],
        scope_filtered=False,
        has_approve=False,
        entity_description="SWOT item (individual strength, weakness, opportunity, or threat entry)",
    )

    # ── Role ───────────────────────────────────────────────
    _register_crud(
        server, "role", Role, "context.role",
        list_fields=["id", "reference", "name", "description", "type",
                      "is_mandatory", "source_standard", "status",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "is_mandatory",
                          "source_standard", "status"],
        search_fields=["name", "description", "reference"],
        filters=["type", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Title of the role (e.g. 'CISO', 'DPO', 'IT Security Officer')."},
            "description": {"type": "string", "description": "Detailed description of the role's responsibilities."},
            "type": {"type": "string", "description": "Category of the role.", "enum": ["governance", "operational", "support", "control"]},
            "is_mandatory": {"type": "boolean", "description": "Whether this role must be assigned to at least one user."},
            "source_standard": {"type": "string", "description": "Standard requiring this role (e.g. 'ISO 27001', 'GDPR')."},
            "status": {"type": "string", "description": "Current status.", "enum": ["active", "inactive"]},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by role type.", "enum": ["governance", "operational", "support", "control"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "inactive"]},
        },
        required_create_fields=["name", "type"],
        entity_description="role (organizational security role, e.g. CISO, DPO)",
    )

    # ── Responsibility ─────────────────────────────────────
    _register_crud(
        server, "responsibility", Responsibility, "context.role",
        list_fields=["id", "role_id", "description", "raci_type",
                      "related_activity_id", "created_at", "updated_at"],
        writable_fields=["role_id", "description", "raci_type",
                          "related_activity_id"],
        search_fields=["description"],
        filters=["role_id", "raci_type"],
        field_schemas={
            "role_id": {"type": "string", "description": "UUID of the parent role."},
            "description": {"type": "string", "description": "Description of the responsibility."},
            "raci_type": {"type": "string", "description": "RACI matrix type for this responsibility.", "enum": ["responsible", "accountable", "consulted", "informed"]},
            "related_activity_id": {"type": "string", "description": "UUID of the related business activity (optional)."},
        },
        filter_schemas={
            "role_id": {"type": "string", "description": "Filter by parent role UUID."},
            "raci_type": {"type": "string", "description": "Filter by RACI type.", "enum": ["responsible", "accountable", "consulted", "informed"]},
        },
        required_create_fields=["role_id", "description", "raci_type"],
        scope_filtered=False,
        has_approve=False,
        entity_description="responsibility (RACI assignment linking a role to an activity)",
    )

    # ── Activity ───────────────────────────────────────────
    _register_crud(
        server, "activity", Activity, "context.activity",
        list_fields=["id", "reference", "name", "description", "type",
                      "criticality", "owner_id", "parent_activity_id",
                      "status", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "criticality",
                          "owner_id", "parent_activity_id", "status"],
        search_fields=["name", "description", "reference"],
        filters=["type", "criticality", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the business activity."},
            "description": {"type": "string", "description": "Detailed description of the activity."},
            "type": {"type": "string", "description": "Type of activity.", "enum": ["core_business", "support", "management"]},
            "criticality": {"type": "string", "description": "Criticality level for BIA (Business Impact Analysis).", "enum": ["low", "medium", "high", "critical"]},
            "owner_id": {"type": "string", "description": "UUID of the user who owns this activity."},
            "parent_activity_id": {"type": "string", "description": "UUID of the parent activity for hierarchical decomposition."},
            "status": {"type": "string", "description": "Current status.", "enum": ["active", "inactive", "planned"]},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by activity type.", "enum": ["core_business", "support", "management"]},
            "criticality": {"type": "string", "description": "Filter by criticality.", "enum": ["low", "medium", "high", "critical"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "inactive", "planned"]},
        },
        required_create_fields=["name", "type", "criticality", "owner_id"],
        entity_description="activity (business activity or process for BIA)",
    )

    # ── Site ───────────────────────────────────────────────
    _register_crud(
        server, "site", Site, "context.site",
        list_fields=["id", "reference", "name", "description", "type",
                      "address", "parent_site_id", "status",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "address",
                          "parent_site_id", "status"],
        search_fields=["name", "description", "reference", "address"],
        filters=["type", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the site or location."},
            "description": {"type": "string", "description": "Description of the site."},
            "type": {"type": "string", "description": "Type of site.", "enum": ["siege", "bureau", "usine", "entrepot", "datacenter", "site_distant", "autre"]},
            "address": {"type": "string", "description": "Full physical address of the site."},
            "parent_site_id": {"type": "string", "description": "UUID of the parent site for hierarchical organization."},
            "status": {"type": "string", "description": "Current status.", "enum": ["draft", "active", "archived"]},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by site type.", "enum": ["siege", "bureau", "usine", "entrepot", "datacenter", "site_distant", "autre"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "active", "archived"]},
        },
        required_create_fields=["name"],
        scope_filtered=False,
        entity_description="site (physical location: headquarters, office, datacenter, etc.)",
    )

    # Tags (simple CRUD, no approve)
    server.register_tool(
        "list_tags",
        "List all tags used for categorizing and filtering objects across the platform.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search tags by name."},
                "limit": {"type": "integer", "description": "Max items (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
        },
        require_perm("context.scope.read")(
            _list_handler(Tag, ["id", "name", "color", "created_at"], ["name"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "create_tag",
        "Create a new tag for categorizing objects.",
        _obj_schema({
            "name": {"type": "string", "description": "Tag name (must be unique)."},
            "color": {"type": "string", "description": "Hex color code (e.g. '#ff5733')."},
        }, ["name"]),
        require_perm("context.scope.create")(
            _create_handler(Tag, ["name", "color"], scope_filtered=False)
        ),
    )
    server.register_tool(
        "delete_tag",
        "Delete a tag by its UUID.",
        _id_schema(),
        require_perm("context.scope.delete")(
            _delete_handler(Tag, scope_filtered=False)
        ),
    )

    # ── Indicator ──────────────────────────────────────────
    _register_crud(
        server, "indicator", Indicator, "context.indicator",
        list_fields=["id", "reference", "name", "description", "indicator_type",
                      "collection_method", "format", "unit", "current_value",
                      "expected_level", "critical_threshold_operator",
                      "critical_threshold_value", "critical_threshold_min",
                      "critical_threshold_max", "review_frequency",
                      "first_review_date", "status", "is_internal",
                      "internal_source", "internal_source_parameter",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "indicator_type", "collection_method",
                          "format", "unit", "expected_level",
                          "critical_threshold_operator", "critical_threshold_value",
                          "critical_threshold_min", "critical_threshold_max",
                          "review_frequency", "first_review_date", "status",
                          "is_internal", "internal_source", "internal_source_parameter"],
        search_fields=["reference", "name", "description"],
        filters=["indicator_type", "status", "format", "collection_method"],
        field_schemas={
            "name": {"type": "string", "description": "Title of the indicator."},
            "description": {"type": "string", "description": "Detailed description."},
            "indicator_type": {"type": "string", "description": "Type of indicator.", "enum": ["organizational", "technical"]},
            "collection_method": {"type": "string", "description": "How data is collected.", "enum": ["manual", "api", "internal"]},
            "format": {"type": "string", "description": "Data format of the indicator value.", "enum": ["number", "boolean"]},
            "unit": {"type": "string", "description": "Unit of measure (only for number format, e.g. '%', 'days')."},
            "expected_level": {"type": "string", "description": "Expected/target value."},
            "critical_threshold_operator": {"type": "string", "description": "Operator for critical threshold evaluation. For numbers: 'below'/'above'. For booleans: 'is_false'/'is_true'.", "enum": ["below", "above", "is_false", "is_true"]},
            "critical_threshold_value": {"type": "string", "description": "Threshold value (for number format only)."},
            "critical_threshold_min": {"type": "number", "description": "Minimum threshold - critical if value falls below (number format only)."},
            "critical_threshold_max": {"type": "number", "description": "Maximum threshold - critical if value exceeds (number format only)."},
            "review_frequency": {"type": "string", "description": "How often the indicator is reviewed.", "enum": ["daily", "weekly", "monthly", "quarterly", "semi_annual", "annual"]},
            "first_review_date": {"type": "string", "format": "date", "description": "First review date (YYYY-MM-DD). Must be today or in the future on creation."},
            "status": {"type": "string", "description": "Current status.", "enum": ["active", "inactive", "draft"]},
            "is_internal": {"type": "boolean", "description": "Whether this is a predefined Open GRC indicator."},
            "internal_source": {"type": "string", "description": "Predefined data source (only when is_internal=true).", "enum": ["global_compliance_rate", "framework_compliance_rate", "objective_progress", "risk_treatment_rate", "approved_scopes_rate", "mandatory_roles_coverage"]},
            "internal_source_parameter": {"type": "string", "description": "Optional parameter for the source (e.g. framework UUID for framework_compliance_rate)."},
        },
        filter_schemas={
            "indicator_type": {"type": "string", "description": "Filter by indicator type.", "enum": ["organizational", "technical"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "inactive", "draft"]},
            "format": {"type": "string", "description": "Filter by data format.", "enum": ["number", "boolean"]},
            "collection_method": {"type": "string", "description": "Filter by collection method.", "enum": ["manual", "api", "internal"]},
        },
        required_create_fields=["name", "indicator_type", "review_frequency", "first_review_date"],
        entity_description="indicator (security or operational KPI/metric)",
    )

    # ── Indicator Measurement ──────────────────────────────
    _register_crud(
        server, "indicator_measurement", IndicatorMeasurement, "context.indicator",
        list_fields=["id", "indicator_id", "value", "recorded_at",
                      "recorded_by_id", "notes"],
        writable_fields=["indicator_id", "value", "notes"],
        search_fields=["notes"],
        filters=["indicator_id"],
        field_schemas={
            "indicator_id": {"type": "string", "description": "UUID of the parent indicator."},
            "value": {"type": "string", "description": "Measured value (string representation of number or boolean)."},
            "notes": {"type": "string", "description": "Optional notes about this measurement."},
        },
        filter_schemas={
            "indicator_id": {"type": "string", "description": "Filter by parent indicator UUID."},
        },
        required_create_fields=["indicator_id", "value"],
        scope_filtered=False,
        has_approve=False,
        entity_description="indicator measurement (a single data point recorded for an indicator)",
    )


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

    # ── Essential Asset ────────────────────────────────────
    _register_crud(
        server, "essential_asset", EssentialAsset, "assets.essential_asset",
        list_fields=["id", "reference", "name", "description", "type", "category",
                      "owner_id", "custodian_id",
                      "confidentiality_level", "integrity_level", "availability_level",
                      "data_classification", "personal_data",
                      "max_tolerable_downtime", "recovery_time_objective", "recovery_point_objective",
                      "status", "review_date", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "category",
                          "owner_id", "custodian_id",
                          "confidentiality_level", "integrity_level", "availability_level",
                          "confidentiality_justification", "integrity_justification",
                          "availability_justification",
                          "max_tolerable_downtime", "recovery_time_objective",
                          "recovery_point_objective",
                          "data_classification", "personal_data",
                          "regulatory_constraints", "status", "review_date"],
        search_fields=["reference", "name", "description"],
        filters=["type", "category", "status", "data_classification"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the essential asset (business process or information asset)."},
            "description": {"type": "string", "description": "Detailed description."},
            "type": {"type": "string", "description": "Type of essential asset.", "enum": ["business_process", "information"]},
            "category": {
                "type": "string",
                "description": "Category. For business_process: core_process, support_process, management_process. For information: strategic_data, operational_data, personal_data, financial_data, technical_data, legal_data, research_data, commercial_data.",
                "enum": ["core_process", "support_process", "management_process",
                         "strategic_data", "operational_data", "personal_data",
                         "financial_data", "technical_data", "legal_data",
                         "research_data", "commercial_data"],
            },
            "owner_id": {"type": "string", "description": "UUID of the asset owner (user)."},
            "custodian_id": {"type": "string", "description": "UUID of the asset custodian (user). Optional."},
            "confidentiality_level": {"type": "integer", "description": "DIC confidentiality level.", "enum": [0, 1, 2, 3, 4], "minimum": 0, "maximum": 4},
            "integrity_level": {"type": "integer", "description": "DIC integrity level.", "enum": [0, 1, 2, 3, 4], "minimum": 0, "maximum": 4},
            "availability_level": {"type": "integer", "description": "DIC availability level.", "enum": [0, 1, 2, 3, 4], "minimum": 0, "maximum": 4},
            "confidentiality_justification": {"type": "string", "description": "Justification for the confidentiality rating."},
            "integrity_justification": {"type": "string", "description": "Justification for the integrity rating."},
            "availability_justification": {"type": "string", "description": "Justification for the availability rating."},
            "max_tolerable_downtime": {"type": "string", "description": "Maximum tolerable downtime (MTD), e.g. '4 hours', '24 hours'."},
            "recovery_time_objective": {"type": "string", "description": "Recovery time objective (RTO)."},
            "recovery_point_objective": {"type": "string", "description": "Recovery point objective (RPO)."},
            "data_classification": {"type": "string", "description": "Data classification level.", "enum": ["public", "internal", "confidential", "restricted", "secret"]},
            "personal_data": {"type": "boolean", "description": "Whether this asset contains personal data (GDPR)."},
            "regulatory_constraints": {"type": "string", "description": "Applicable regulatory constraints."},
            "status": {"type": "string", "description": "Lifecycle status.", "enum": ["identified", "active", "under_review", "decommissioned"]},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by asset type.", "enum": ["business_process", "information"]},
            "category": {"type": "string", "description": "Filter by category.", "enum": ["core_process", "support_process", "management_process", "strategic_data", "operational_data", "personal_data", "financial_data", "technical_data", "legal_data", "research_data", "commercial_data"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["identified", "active", "under_review", "decommissioned"]},
            "data_classification": {"type": "string", "description": "Filter by data classification.", "enum": ["public", "internal", "confidential", "restricted", "secret"]},
        },
        required_create_fields=["name", "type", "category", "owner_id"],
        entity_description="essential asset (business process or information asset with DIC valuation)",
    )

    # ── Support Asset ──────────────────────────────────────
    _register_crud(
        server, "support_asset", SupportAsset, "assets.support_asset",
        list_fields=["id", "reference", "name", "description", "type", "category",
                      "owner_id", "custodian_id",
                      "hostname", "ip_address", "operating_system",
                      "location", "manufacturer", "model_name",
                      "exposure_level", "environment",
                      "inherited_confidentiality", "inherited_integrity",
                      "inherited_availability",
                      "end_of_life_date", "parent_asset_id",
                      "status", "review_date", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "category",
                          "owner_id", "custodian_id",
                          "location", "manufacturer", "model_name",
                          "serial_number", "software_version",
                          "ip_address", "hostname", "operating_system",
                          "acquisition_date", "end_of_life_date",
                          "warranty_expiry_date", "contract_reference",
                          "exposure_level", "environment",
                          "parent_asset_id", "status", "review_date"],
        search_fields=["reference", "name", "description", "hostname", "ip_address"],
        filters=["type", "category", "status", "exposure_level", "environment"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the support asset."},
            "description": {"type": "string", "description": "Description."},
            "type": {"type": "string", "description": "Asset type.", "enum": ["hardware", "software", "network", "person", "site", "service", "paper"]},
            "category": {
                "type": "string",
                "description": "Asset category (must match the type). Hardware: server, workstation, laptop, mobile_device, network_equipment, storage, peripheral, iot_device, removable_media, other_hardware. Software: operating_system, database, application, middleware, security_tool, development_tool, saas_application, other_software. Network: lan, wan, wifi, vpn, internet_link, firewall_zone, dmz, other_network. Person: internal_staff, contractor, external_provider, administrator, developer, other_person. Site: datacenter, office, remote_site, cloud_region, other_site. Service: cloud_service, hosting_service, managed_service, telecom_service, outsourced_service, other_service. Paper: archive, printed_document, form, other_paper.",
                "enum": ["server", "workstation", "laptop", "mobile_device", "network_equipment",
                         "storage", "peripheral", "iot_device", "removable_media", "other_hardware",
                         "operating_system", "database", "application", "middleware",
                         "security_tool", "development_tool", "saas_application", "other_software",
                         "lan", "wan", "wifi", "vpn", "internet_link",
                         "firewall_zone", "dmz", "other_network",
                         "internal_staff", "contractor", "external_provider",
                         "administrator", "developer", "other_person",
                         "datacenter", "office", "remote_site", "cloud_region", "other_site",
                         "cloud_service", "hosting_service", "managed_service",
                         "telecom_service", "outsourced_service", "other_service",
                         "archive", "printed_document", "form", "other_paper"],
            },
            "owner_id": {"type": "string", "description": "UUID of the asset owner (user)."},
            "custodian_id": {"type": "string", "description": "UUID of the asset custodian (user). Optional."},
            "location": {"type": "string", "description": "Physical location description."},
            "manufacturer": {"type": "string", "description": "Manufacturer or vendor name."},
            "model_name": {"type": "string", "description": "Model name or version."},
            "serial_number": {"type": "string", "description": "Serial number."},
            "software_version": {"type": "string", "description": "Software version."},
            "ip_address": {"type": "string", "description": "IP address (IPv4 or IPv6)."},
            "hostname": {"type": "string", "description": "Hostname or FQDN."},
            "operating_system": {"type": "string", "description": "Operating system name and version."},
            "acquisition_date": {"type": "string", "format": "date", "description": "Acquisition date (YYYY-MM-DD)."},
            "end_of_life_date": {"type": "string", "format": "date", "description": "End of life date (YYYY-MM-DD)."},
            "warranty_expiry_date": {"type": "string", "format": "date", "description": "Warranty expiry date (YYYY-MM-DD)."},
            "contract_reference": {"type": "string", "description": "Reference to associated contract."},
            "exposure_level": {"type": "string", "description": "Network exposure level.", "enum": ["internal", "exposed", "internet_facing", "dmz"]},
            "environment": {"type": "string", "description": "Deployment environment.", "enum": ["production", "staging", "development", "test", "disaster_recovery"]},
            "parent_asset_id": {"type": "string", "description": "UUID of the parent support asset."},
            "status": {"type": "string", "description": "Lifecycle status.", "enum": ["in_stock", "deployed", "active", "under_maintenance", "decommissioned", "disposed"]},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by asset type.", "enum": ["hardware", "software", "network", "person", "site", "service", "paper"]},
            "category": {"type": "string", "description": "Filter by category."},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["in_stock", "deployed", "active", "under_maintenance", "decommissioned", "disposed"]},
            "exposure_level": {"type": "string", "description": "Filter by exposure level.", "enum": ["internal", "exposed", "internet_facing", "dmz"]},
            "environment": {"type": "string", "description": "Filter by environment.", "enum": ["production", "staging", "development", "test", "disaster_recovery"]},
        },
        required_create_fields=["name", "type", "category", "owner_id"],
        entity_description="support asset (hardware, software, network, person, site, service, or paper asset)",
    )

    # ── Asset Dependency ───────────────────────────────────
    _register_crud(
        server, "asset_dependency", AssetDependency, "assets.dependency",
        list_fields=["id", "reference", "essential_asset_id", "support_asset_id",
                      "dependency_type", "criticality", "description",
                      "is_single_point_of_failure", "redundancy_level",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["essential_asset_id", "support_asset_id",
                          "dependency_type", "criticality", "description",
                          "is_single_point_of_failure", "redundancy_level"],
        search_fields=["description"],
        filters=["essential_asset_id", "support_asset_id", "dependency_type", "criticality"],
        field_schemas={
            "essential_asset_id": {"type": "string", "description": "UUID of the essential asset."},
            "support_asset_id": {"type": "string", "description": "UUID of the support asset."},
            "dependency_type": {"type": "string", "description": "Nature of the dependency.", "enum": ["runs_on", "stored_in", "transmitted_by", "managed_by", "hosted_at", "protected_by", "other"]},
            "criticality": {"type": "string", "description": "Criticality of this dependency.", "enum": ["low", "medium", "high", "critical"]},
            "description": {"type": "string", "description": "Description of the dependency."},
            "is_single_point_of_failure": {"type": "boolean", "description": "Whether this asset is a single point of failure (SPOF)."},
            "redundancy_level": {"type": "string", "description": "Level of redundancy.", "enum": ["none", "partial", "full"]},
        },
        filter_schemas={
            "essential_asset_id": {"type": "string", "description": "Filter by essential asset UUID."},
            "support_asset_id": {"type": "string", "description": "Filter by support asset UUID."},
            "dependency_type": {"type": "string", "description": "Filter by dependency type.", "enum": ["runs_on", "stored_in", "transmitted_by", "managed_by", "hosted_at", "protected_by", "other"]},
            "criticality": {"type": "string", "description": "Filter by criticality.", "enum": ["low", "medium", "high", "critical"]},
        },
        required_create_fields=["essential_asset_id", "support_asset_id", "dependency_type", "criticality"],
        scope_filtered=False,
        entity_description="asset dependency (link between an essential asset and a support asset)",
    )

    # ── Asset Group ────────────────────────────────────────
    _register_crud(
        server, "asset_group", AssetGroup, "assets.group",
        list_fields=["id", "reference", "name", "description", "type",
                      "owner_id", "status", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "owner_id", "status"],
        search_fields=["name", "description"],
        filters=["type", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the asset group."},
            "description": {"type": "string", "description": "Description."},
            "type": {"type": "string", "description": "Type of support assets in this group.", "enum": ["hardware", "software", "network", "person", "site", "service", "paper"]},
            "owner_id": {"type": "string", "description": "UUID of the group owner (user)."},
            "status": {"type": "string", "description": "Group status.", "enum": ["active", "inactive"]},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by asset type.", "enum": ["hardware", "software", "network", "person", "site", "service", "paper"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "inactive"]},
        },
        required_create_fields=["name", "type"],
        entity_description="asset group (logical grouping of support assets by type)",
    )

    # ── Supplier ───────────────────────────────────────────
    _register_crud(
        server, "supplier", Supplier, "assets.supplier",
        list_fields=["id", "reference", "name", "description", "type_id",
                      "criticality", "status",
                      "contact_name", "contact_email", "contact_phone",
                      "website", "country",
                      "contract_start_date", "contract_end_date",
                      "owner_id", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type_id", "criticality",
                          "contact_name", "contact_email", "contact_phone",
                          "website", "address", "country",
                          "contract_reference", "contract_start_date",
                          "contract_end_date", "owner_id", "status", "notes"],
        search_fields=["reference", "name", "description", "contact_name"],
        filters=["type_id", "criticality", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Supplier name."},
            "description": {"type": "string", "description": "Description."},
            "type_id": {"type": "integer", "description": "ID of the supplier type (from supplier_type entity)."},
            "criticality": {"type": "string", "description": "Supplier criticality.", "enum": ["low", "medium", "high", "critical"]},
            "contact_name": {"type": "string", "description": "Primary contact name."},
            "contact_email": {"type": "string", "format": "email", "description": "Contact email."},
            "contact_phone": {"type": "string", "description": "Contact phone."},
            "website": {"type": "string", "format": "uri", "description": "Supplier website URL."},
            "address": {"type": "string", "description": "Physical address."},
            "country": {"type": "string", "description": "Country."},
            "contract_reference": {"type": "string", "description": "Contract reference number."},
            "contract_start_date": {"type": "string", "format": "date", "description": "Contract start date (YYYY-MM-DD)."},
            "contract_end_date": {"type": "string", "format": "date", "description": "Contract end date (YYYY-MM-DD)."},
            "owner_id": {"type": "string", "description": "UUID of the supplier owner (user)."},
            "status": {"type": "string", "description": "Supplier status.", "enum": ["active", "under_evaluation", "suspended", "archived"]},
            "notes": {"type": "string", "description": "Additional notes."},
        },
        filter_schemas={
            "type_id": {"type": "integer", "description": "Filter by supplier type ID."},
            "criticality": {"type": "string", "description": "Filter by criticality.", "enum": ["low", "medium", "high", "critical"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "under_evaluation", "suspended", "archived"]},
        },
        required_create_fields=["name", "owner_id"],
        entity_description="supplier (third-party vendor with contract and criticality tracking)",
    )

    # ── Supplier Dependency ────────────────────────────────
    _register_crud(
        server, "supplier_dependency", SupplierDependency, "assets.supplier_dependency",
        list_fields=["id", "reference", "support_asset_id", "supplier_id",
                      "dependency_type", "criticality", "description",
                      "is_single_point_of_failure", "redundancy_level",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["support_asset_id", "supplier_id", "dependency_type",
                          "criticality", "description",
                          "is_single_point_of_failure", "redundancy_level"],
        search_fields=["description"],
        filters=["support_asset_id", "supplier_id", "dependency_type"],
        field_schemas={
            "support_asset_id": {"type": "string", "description": "UUID of the support asset."},
            "supplier_id": {"type": "string", "description": "UUID of the supplier."},
            "dependency_type": {"type": "string", "description": "Nature of the supplier dependency.", "enum": ["hosted_by", "provided_by", "maintained_by", "developed_by", "operated_by", "monitored_by", "other"]},
            "criticality": {"type": "string", "description": "Criticality of this dependency.", "enum": ["low", "medium", "high", "critical"]},
            "description": {"type": "string", "description": "Description."},
            "is_single_point_of_failure": {"type": "boolean", "description": "Whether this is a SPOF."},
            "redundancy_level": {"type": "string", "description": "Redundancy level.", "enum": ["none", "partial", "full"]},
        },
        filter_schemas={
            "support_asset_id": {"type": "string", "description": "Filter by support asset UUID."},
            "supplier_id": {"type": "string", "description": "Filter by supplier UUID."},
            "dependency_type": {"type": "string", "description": "Filter by dependency type.", "enum": ["hosted_by", "provided_by", "maintained_by", "developed_by", "operated_by", "monitored_by", "other"]},
        },
        required_create_fields=["support_asset_id", "supplier_id", "dependency_type", "criticality"],
        scope_filtered=False,
        entity_description="supplier dependency (link between a support asset and a supplier)",
    )

    # ── Site-Asset Dependency ──────────────────────────────
    _register_crud(
        server, "site_asset_dependency", SiteAssetDependency, "assets.dependency",
        list_fields=["id", "reference", "support_asset_id", "site_id",
                      "dependency_type", "criticality", "description",
                      "is_single_point_of_failure", "redundancy_level",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["support_asset_id", "site_id", "dependency_type",
                          "criticality", "description",
                          "is_single_point_of_failure", "redundancy_level"],
        search_fields=["description"],
        filters=["support_asset_id", "site_id", "dependency_type", "criticality"],
        field_schemas={
            "support_asset_id": {"type": "string", "description": "UUID of the support asset."},
            "site_id": {"type": "string", "description": "UUID of the site."},
            "dependency_type": {"type": "string", "description": "Nature of the site-asset dependency.", "enum": ["located_at", "hosted_at", "deployed_at", "other"]},
            "criticality": {"type": "string", "description": "Criticality.", "enum": ["low", "medium", "high", "critical"]},
            "description": {"type": "string", "description": "Description."},
            "is_single_point_of_failure": {"type": "boolean", "description": "Whether this is a SPOF."},
            "redundancy_level": {"type": "string", "description": "Redundancy level.", "enum": ["none", "partial", "full"]},
        },
        filter_schemas={
            "support_asset_id": {"type": "string", "description": "Filter by support asset UUID."},
            "site_id": {"type": "string", "description": "Filter by site UUID."},
            "dependency_type": {"type": "string", "description": "Filter by type.", "enum": ["located_at", "hosted_at", "deployed_at", "other"]},
            "criticality": {"type": "string", "description": "Filter by criticality.", "enum": ["low", "medium", "high", "critical"]},
        },
        required_create_fields=["support_asset_id", "site_id", "dependency_type", "criticality"],
        scope_filtered=False,
        entity_description="site-asset dependency (link between a support asset and a physical site)",
    )

    # ── Site-Supplier Dependency ───────────────────────────
    _register_crud(
        server, "site_supplier_dependency", SiteSupplierDependency,
        "assets.supplier_dependency",
        list_fields=["id", "reference", "site_id", "supplier_id",
                      "dependency_type", "criticality", "description",
                      "is_single_point_of_failure", "redundancy_level",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["site_id", "supplier_id", "dependency_type",
                          "criticality", "description",
                          "is_single_point_of_failure", "redundancy_level"],
        search_fields=["description"],
        filters=["site_id", "supplier_id", "dependency_type", "criticality"],
        field_schemas={
            "site_id": {"type": "string", "description": "UUID of the site."},
            "supplier_id": {"type": "string", "description": "UUID of the supplier."},
            "dependency_type": {"type": "string", "description": "Nature of the site-supplier dependency.", "enum": ["maintained_by", "managed_by", "powered_by", "secured_by", "other"]},
            "criticality": {"type": "string", "description": "Criticality.", "enum": ["low", "medium", "high", "critical"]},
            "description": {"type": "string", "description": "Description."},
            "is_single_point_of_failure": {"type": "boolean", "description": "Whether this is a SPOF."},
            "redundancy_level": {"type": "string", "description": "Redundancy level.", "enum": ["none", "partial", "full"]},
        },
        filter_schemas={
            "site_id": {"type": "string", "description": "Filter by site UUID."},
            "supplier_id": {"type": "string", "description": "Filter by supplier UUID."},
            "dependency_type": {"type": "string", "description": "Filter by type.", "enum": ["maintained_by", "managed_by", "powered_by", "secured_by", "other"]},
            "criticality": {"type": "string", "description": "Filter by criticality.", "enum": ["low", "medium", "high", "critical"]},
        },
        required_create_fields=["site_id", "supplier_id", "dependency_type", "criticality"],
        scope_filtered=False,
        entity_description="site-supplier dependency (link between a site and a supplier)",
    )

    # ── Asset Valuation ────────────────────────────────────
    _register_crud(
        server, "asset_valuation", AssetValuation, "assets.essential_asset",
        list_fields=["id", "essential_asset_id", "evaluation_date",
                      "confidentiality_level", "integrity_level", "availability_level",
                      "evaluated_by_id", "justification", "context", "created_at"],
        writable_fields=["essential_asset_id", "evaluation_date",
                          "confidentiality_level", "integrity_level", "availability_level",
                          "evaluated_by_id", "justification", "context"],
        search_fields=["justification"],
        filters=["essential_asset_id"],
        field_schemas={
            "essential_asset_id": {"type": "string", "description": "UUID of the essential asset being valued."},
            "evaluation_date": {"type": "string", "format": "date", "description": "Date of the evaluation (YYYY-MM-DD)."},
            "confidentiality_level": {"type": "integer", "description": "DIC confidentiality level (0=Negligible, 1=Low, 2=Medium, 3=High, 4=Critical).", "enum": [0, 1, 2, 3, 4]},
            "integrity_level": {"type": "integer", "description": "DIC integrity level (0-4).", "enum": [0, 1, 2, 3, 4]},
            "availability_level": {"type": "integer", "description": "DIC availability level (0-4).", "enum": [0, 1, 2, 3, 4]},
            "evaluated_by_id": {"type": "string", "description": "UUID of the evaluator (user)."},
            "justification": {"type": "string", "description": "Justification for the DIC levels assigned."},
            "context": {"type": "string", "description": "Context or circumstances of the evaluation."},
        },
        filter_schemas={
            "essential_asset_id": {"type": "string", "description": "Filter by essential asset UUID."},
        },
        required_create_fields=["essential_asset_id", "evaluation_date", "confidentiality_level", "integrity_level", "availability_level", "evaluated_by_id"],
        scope_filtered=False,
        has_approve=False,
        entity_description="asset valuation (historical DIC evaluation record for an essential asset)",
    )

    # ── Supplier Type ──────────────────────────────────────
    _register_crud(
        server, "supplier_type", SupplierType, "assets.config",
        list_fields=["id", "reference", "name", "description", "created_at", "updated_at"],
        writable_fields=["name", "description"],
        search_fields=["name", "description"],
        filters=[],
        field_schemas={
            "name": {"type": "string", "description": "Name of the supplier type (must be unique)."},
            "description": {"type": "string", "description": "Description of what this supplier type entails."},
        },
        required_create_fields=["name"],
        scope_filtered=False,
        has_approve=False,
        entity_description="supplier type (configurable category for suppliers, e.g. 'Cloud Provider', 'SaaS Vendor')",
    )

    # ── Supplier Type Requirement ──────────────────────────
    _register_crud(
        server, "supplier_type_requirement", SupplierTypeRequirement, "assets.config",
        list_fields=["id", "supplier_type_id", "title", "description", "created_at", "updated_at"],
        writable_fields=["supplier_type_id", "title", "description"],
        search_fields=["title", "description"],
        filters=["supplier_type_id"],
        field_schemas={
            "supplier_type_id": {"type": "integer", "description": "ID of the parent supplier type."},
            "title": {"type": "string", "description": "Title of the requirement."},
            "description": {"type": "string", "description": "Detailed description."},
        },
        filter_schemas={
            "supplier_type_id": {"type": "integer", "description": "Filter by supplier type ID."},
        },
        required_create_fields=["supplier_type_id", "title"],
        scope_filtered=False,
        has_approve=False,
        entity_description="supplier type requirement (a requirement template for suppliers of a given type)",
    )

    # ── Supplier Requirement ───────────────────────────────
    _register_crud(
        server, "supplier_requirement", SupplierRequirement, "assets.supplier",
        list_fields=["id", "supplier_id", "source_type_requirement_id",
                      "requirement_id", "title", "description",
                      "compliance_status", "evidence", "due_date",
                      "verified_at", "verified_by_id", "created_at", "updated_at"],
        writable_fields=["supplier_id", "source_type_requirement_id",
                          "requirement_id", "title", "description",
                          "compliance_status", "evidence", "due_date"],
        search_fields=["title", "description"],
        filters=["supplier_id", "compliance_status"],
        field_schemas={
            "supplier_id": {"type": "string", "description": "UUID of the supplier."},
            "source_type_requirement_id": {"type": "integer", "description": "ID of the source supplier type requirement (optional)."},
            "requirement_id": {"type": "string", "description": "UUID of a linked compliance requirement (optional)."},
            "title": {"type": "string", "description": "Title of the requirement."},
            "description": {"type": "string", "description": "Description."},
            "compliance_status": {"type": "string", "description": "Current compliance status.", "enum": ["not_assessed", "compliant", "partially_compliant", "non_compliant"]},
            "evidence": {"type": "string", "description": "Compliance evidence text."},
            "due_date": {"type": "string", "format": "date", "description": "Due date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "supplier_id": {"type": "string", "description": "Filter by supplier UUID."},
            "compliance_status": {"type": "string", "description": "Filter by compliance status.", "enum": ["not_assessed", "compliant", "partially_compliant", "non_compliant"]},
        },
        required_create_fields=["supplier_id", "title"],
        scope_filtered=False,
        has_approve=False,
        entity_description="supplier requirement (specific compliance requirement applied to a supplier)",
    )

    # ── Supplier Requirement Review ────────────────────────
    _register_crud(
        server, "supplier_requirement_review", SupplierRequirementReview, "assets.supplier",
        list_fields=["id", "supplier_requirement_id", "review_date",
                      "reviewer_id", "result", "comment", "created_at", "updated_at"],
        writable_fields=["supplier_requirement_id", "review_date",
                          "reviewer_id", "result", "comment"],
        search_fields=["comment"],
        filters=["supplier_requirement_id", "result"],
        field_schemas={
            "supplier_requirement_id": {"type": "integer", "description": "ID of the supplier requirement being reviewed."},
            "review_date": {"type": "string", "format": "date", "description": "Date of the review (YYYY-MM-DD)."},
            "reviewer_id": {"type": "string", "description": "UUID of the reviewer (user)."},
            "result": {"type": "string", "description": "Review result.", "enum": ["not_assessed", "compliant", "partially_compliant", "non_compliant"]},
            "comment": {"type": "string", "description": "Written justification for the assessment."},
        },
        filter_schemas={
            "supplier_requirement_id": {"type": "integer", "description": "Filter by supplier requirement ID."},
            "result": {"type": "string", "description": "Filter by result.", "enum": ["not_assessed", "compliant", "partially_compliant", "non_compliant"]},
        },
        required_create_fields=["supplier_requirement_id", "review_date"],
        scope_filtered=False,
        has_approve=False,
        entity_description="supplier requirement review (audit trail entry for supplier requirement compliance assessment)",
    )


# ── Compliance Module ──────────────────────────────────────

def _register_compliance_tools(server):
    Framework = _get_model("compliance", "Framework")
    Section = _get_model("compliance", "Section")
    Requirement = _get_model("compliance", "Requirement")
    ComplianceAssessment = _get_model("compliance", "ComplianceAssessment")
    AssessmentResult = _get_model("compliance", "AssessmentResult")
    RequirementMapping = _get_model("compliance", "RequirementMapping")
    ComplianceActionPlan = _get_model("compliance", "ComplianceActionPlan")

    # ── Framework ──────────────────────────────────────────
    _register_crud(
        server, "framework", Framework, "compliance.framework",
        list_fields=["id", "reference", "name", "short_name", "description",
                      "type", "category", "framework_version",
                      "publication_date", "effective_date", "expiry_date",
                      "issuing_body", "jurisdiction",
                      "is_mandatory", "is_applicable",
                      "compliance_level", "last_assessment_date",
                      "owner_id", "status", "review_date",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "short_name", "description", "type", "category",
                          "framework_version", "publication_date", "effective_date",
                          "expiry_date", "issuing_body", "jurisdiction", "url",
                          "is_mandatory", "is_applicable", "applicability_justification",
                          "owner_id", "status", "review_date"],
        search_fields=["reference", "name", "short_name", "description"],
        filters=["type", "category", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Full name of the framework (e.g. 'ISO/IEC 27001:2022')."},
            "short_name": {"type": "string", "description": "Short name (e.g. 'ISO 27001')."},
            "description": {"type": "string", "description": "Description of the framework."},
            "type": {"type": "string", "description": "Type of framework.", "enum": ["standard", "law", "regulation", "contract", "internal_policy", "industry_framework", "other"]},
            "category": {"type": "string", "description": "Domain category.", "enum": ["information_security", "privacy", "risk_management", "business_continuity", "cloud_security", "sector_specific", "it_governance", "quality", "contractual", "internal", "other"]},
            "framework_version": {"type": "string", "description": "Version of the framework (e.g. '2022')."},
            "publication_date": {"type": "string", "format": "date", "description": "Publication date (YYYY-MM-DD)."},
            "effective_date": {"type": "string", "format": "date", "description": "Effective date (YYYY-MM-DD)."},
            "expiry_date": {"type": "string", "format": "date", "description": "Expiry date (YYYY-MM-DD)."},
            "issuing_body": {"type": "string", "description": "Organization that published the framework (e.g. 'ISO', 'NIST')."},
            "jurisdiction": {"type": "string", "description": "Geographic jurisdiction (e.g. 'France', 'EU', 'International')."},
            "url": {"type": "string", "format": "uri", "description": "URL to the framework's official page."},
            "is_mandatory": {"type": "boolean", "description": "Whether compliance with this framework is mandatory."},
            "is_applicable": {"type": "boolean", "description": "Whether this framework is applicable to the organization."},
            "applicability_justification": {"type": "string", "description": "Justification for applicability decision."},
            "owner_id": {"type": "string", "description": "UUID of the framework owner (user)."},
            "status": {"type": "string", "description": "Lifecycle status.", "enum": ["draft", "active", "under_review", "deprecated", "archived"]},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by framework type.", "enum": ["standard", "law", "regulation", "contract", "internal_policy", "industry_framework", "other"]},
            "category": {"type": "string", "description": "Filter by category.", "enum": ["information_security", "privacy", "risk_management", "business_continuity", "cloud_security", "sector_specific", "it_governance", "quality", "contractual", "internal", "other"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "active", "under_review", "deprecated", "archived"]},
        },
        required_create_fields=["name", "type", "category", "owner_id"],
        scope_filtered=False,
        entity_description="framework (compliance framework, standard, law, or regulation)",
    )

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
        "Get compliance summary for a framework. Returns the overall compliance level (0-100%), "
        "top-level section compliance levels, requirement counts by compliance status "
        "(not_assessed, non_compliant, partially_compliant, compliant, not_applicable), "
        "and total applicable requirements.",
        _id_schema(),
        framework_compliance_summary,
    )

    # ── Section ────────────────────────────────────────────
    _register_crud(
        server, "section", Section, "compliance.section",
        list_fields=["id", "reference", "name", "description", "order",
                      "compliance_level", "framework_id", "parent_section_id",
                      "created_at", "updated_at"],
        writable_fields=["name", "description", "order",
                          "framework_id", "parent_section_id"],
        search_fields=["reference", "name"],
        filters=["framework_id", "parent_section_id"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the section (e.g. 'A.5 Information Security Policies')."},
            "description": {"type": "string", "description": "Description of the section."},
            "order": {"type": "integer", "description": "Display order within the parent.", "minimum": 0},
            "framework_id": {"type": "string", "description": "UUID of the parent framework."},
            "parent_section_id": {"type": "string", "description": "UUID of the parent section (for nested sections). Null for top-level sections."},
        },
        filter_schemas={
            "framework_id": {"type": "string", "description": "Filter by parent framework UUID."},
            "parent_section_id": {"type": "string", "description": "Filter by parent section UUID. Use null or omit for top-level sections."},
        },
        required_create_fields=["name", "framework_id"],
        scope_filtered=False,
        has_approve=False,
        entity_description="section (hierarchical section within a compliance framework)",
    )

    # ── Requirement ────────────────────────────────────────
    _register_crud(
        server, "requirement", Requirement, "compliance.requirement",
        list_fields=["id", "reference", "requirement_number", "name",
                      "description", "guidance", "type", "category",
                      "is_applicable", "applicability_justification",
                      "compliance_status", "compliance_level",
                      "compliance_evidence", "compliance_gaps",
                      "priority", "target_date", "order",
                      "framework_id", "section_id",
                      "owner_id", "status",
                      "last_assessment_date", "last_assessed_by_id",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["requirement_number", "name", "description", "guidance",
                          "type", "category",
                          "is_applicable", "applicability_justification",
                          "compliance_status", "compliance_level",
                          "compliance_evidence", "compliance_gaps",
                          "priority", "target_date", "order",
                          "framework_id", "section_id", "owner_id", "status"],
        search_fields=["reference", "requirement_number", "name", "description"],
        filters=["framework_id", "section_id", "compliance_status", "type", "priority", "status"],
        field_schemas={
            "requirement_number": {"type": "string", "description": "Official requirement number (e.g. 'A.5.1.1', '6.1.2'). Must be unique within the framework."},
            "name": {"type": "string", "description": "Title of the requirement."},
            "description": {"type": "string", "description": "Full text of the requirement."},
            "guidance": {"type": "string", "description": "Implementation guidance."},
            "type": {"type": "string", "description": "Requirement type.", "enum": ["mandatory", "recommended", "optional"]},
            "category": {"type": "string", "description": "Requirement category.", "enum": ["organizational", "technical", "physical", "legal", "human", "other"]},
            "is_applicable": {"type": "boolean", "description": "Whether this requirement is applicable."},
            "applicability_justification": {"type": "string", "description": "Justification for applicability decision."},
            "compliance_status": {"type": "string", "description": "Current compliance status.", "enum": ["not_assessed", "non_compliant", "partially_compliant", "compliant", "not_applicable"]},
            "compliance_level": {"type": "integer", "description": "Compliance level percentage (0-100).", "minimum": 0, "maximum": 100},
            "compliance_evidence": {"type": "string", "description": "Evidence of compliance."},
            "compliance_gaps": {"type": "string", "description": "Identified compliance gaps."},
            "priority": {"type": "string", "description": "Priority.", "enum": ["low", "medium", "high", "critical"]},
            "target_date": {"type": "string", "format": "date", "description": "Target compliance date (YYYY-MM-DD)."},
            "order": {"type": "integer", "description": "Display order within the section.", "minimum": 0},
            "framework_id": {"type": "string", "description": "UUID of the parent framework."},
            "section_id": {"type": "string", "description": "UUID of the parent section (optional)."},
            "owner_id": {"type": "string", "description": "UUID of the requirement owner (user)."},
            "status": {"type": "string", "description": "Requirement lifecycle status.", "enum": ["active", "deprecated", "superseded"]},
        },
        filter_schemas={
            "framework_id": {"type": "string", "description": "Filter by framework UUID."},
            "section_id": {"type": "string", "description": "Filter by section UUID."},
            "compliance_status": {"type": "string", "description": "Filter by compliance status.", "enum": ["not_assessed", "non_compliant", "partially_compliant", "compliant", "not_applicable"]},
            "type": {"type": "string", "description": "Filter by requirement type.", "enum": ["mandatory", "recommended", "optional"]},
            "priority": {"type": "string", "description": "Filter by priority.", "enum": ["low", "medium", "high", "critical"]},
            "status": {"type": "string", "description": "Filter by lifecycle status.", "enum": ["active", "deprecated", "superseded"]},
        },
        required_create_fields=["name", "description", "type", "framework_id"],
        scope_filtered=False,
        entity_description="requirement (compliance requirement within a framework)",
    )

    # ── Compliance Assessment ──────────────────────────────
    _register_crud(
        server, "compliance_assessment", ComplianceAssessment, "compliance.assessment",
        list_fields=["id", "reference", "name", "description",
                      "assessment_date", "status",
                      "overall_compliance_level", "total_requirements",
                      "compliant_count", "partially_compliant_count",
                      "non_compliant_count", "not_assessed_count",
                      "framework_id", "assessor_id",
                      "validated_by_id", "validated_at",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "assessment_date", "status",
                          "methodology", "framework_id", "assessor_id"],
        search_fields=["name", "description", "reference"],
        filters=["framework_id", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the compliance assessment."},
            "description": {"type": "string", "description": "Description."},
            "assessment_date": {"type": "string", "format": "date", "description": "Date of the assessment (YYYY-MM-DD)."},
            "status": {"type": "string", "description": "Assessment status.", "enum": ["draft", "in_progress", "completed", "validated", "archived"]},
            "methodology": {"type": "string", "description": "Assessment methodology used (free text)."},
            "framework_id": {"type": "string", "description": "UUID of the framework being assessed."},
            "assessor_id": {"type": "string", "description": "UUID of the lead assessor (user)."},
        },
        filter_schemas={
            "framework_id": {"type": "string", "description": "Filter by framework UUID."},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "in_progress", "completed", "validated", "archived"]},
        },
        required_create_fields=["name", "assessment_date", "framework_id", "assessor_id"],
        entity_description="compliance assessment (formal assessment of a framework's requirements)",
    )

    # ── Assessment Result ──────────────────────────────────
    _register_crud(
        server, "assessment_result", AssessmentResult, "compliance.assessment",
        list_fields=["id", "assessment_id", "requirement_id",
                      "compliance_status", "compliance_level",
                      "evidence", "gaps", "observations",
                      "assessed_by_id", "assessed_at",
                      "created_at", "updated_at"],
        writable_fields=["assessment_id", "requirement_id",
                          "compliance_status", "compliance_level",
                          "evidence", "gaps", "observations",
                          "assessed_by_id", "assessed_at"],
        search_fields=["evidence", "gaps"],
        filters=["assessment_id", "requirement_id", "compliance_status"],
        field_schemas={
            "assessment_id": {"type": "string", "description": "UUID of the parent compliance assessment."},
            "requirement_id": {"type": "string", "description": "UUID of the requirement being assessed."},
            "compliance_status": {"type": "string", "description": "Compliance status for this requirement.", "enum": ["not_assessed", "non_compliant", "partially_compliant", "compliant", "not_applicable"]},
            "compliance_level": {"type": "integer", "description": "Compliance level percentage (0-100).", "minimum": 0, "maximum": 100},
            "evidence": {"type": "string", "description": "Evidence of compliance."},
            "gaps": {"type": "string", "description": "Identified gaps."},
            "observations": {"type": "string", "description": "Assessor observations."},
            "assessed_by_id": {"type": "string", "description": "UUID of the assessor (user)."},
            "assessed_at": {"type": "string", "format": "date-time", "description": "Timestamp of assessment (ISO 8601)."},
        },
        filter_schemas={
            "assessment_id": {"type": "string", "description": "Filter by assessment UUID."},
            "requirement_id": {"type": "string", "description": "Filter by requirement UUID."},
            "compliance_status": {"type": "string", "description": "Filter by compliance status.", "enum": ["not_assessed", "non_compliant", "partially_compliant", "compliant", "not_applicable"]},
        },
        required_create_fields=["assessment_id", "requirement_id", "assessed_by_id", "assessed_at"],
        scope_filtered=False,
        has_approve=False,
        entity_description="assessment result (individual requirement result within a compliance assessment)",
    )

    # ── Requirement Mapping ────────────────────────────────
    _register_crud(
        server, "requirement_mapping", RequirementMapping, "compliance.mapping",
        list_fields=["id", "source_requirement_id", "target_requirement_id",
                      "mapping_type", "coverage_level", "description",
                      "justification", "created_by_id", "created_at", "updated_at"],
        writable_fields=["source_requirement_id", "target_requirement_id",
                          "mapping_type", "coverage_level", "description",
                          "justification"],
        search_fields=["description", "justification"],
        filters=["source_requirement_id", "target_requirement_id", "mapping_type"],
        field_schemas={
            "source_requirement_id": {"type": "string", "description": "UUID of the source requirement."},
            "target_requirement_id": {"type": "string", "description": "UUID of the target requirement. Must be from a different framework than the source."},
            "mapping_type": {"type": "string", "description": "Type of mapping relationship.", "enum": ["equivalent", "partial_overlap", "includes", "included_by", "related"]},
            "coverage_level": {"type": "string", "description": "Level of coverage.", "enum": ["full", "partial", "minimal"]},
            "description": {"type": "string", "description": "Description of the mapping."},
            "justification": {"type": "string", "description": "Justification for the mapping."},
        },
        filter_schemas={
            "source_requirement_id": {"type": "string", "description": "Filter by source requirement UUID."},
            "target_requirement_id": {"type": "string", "description": "Filter by target requirement UUID."},
            "mapping_type": {"type": "string", "description": "Filter by mapping type.", "enum": ["equivalent", "partial_overlap", "includes", "included_by", "related"]},
        },
        required_create_fields=["source_requirement_id", "target_requirement_id", "mapping_type"],
        scope_filtered=False,
        has_approve=False,
        entity_description="requirement mapping (cross-framework mapping between requirements)",
    )

    # ── Action Plan ────────────────────────────────────────
    _register_crud(
        server, "action_plan", ComplianceActionPlan, "compliance.action_plan",
        list_fields=["id", "reference", "name", "description", "priority",
                      "status", "start_date", "target_date", "completion_date",
                      "progress_percentage", "cost_estimate",
                      "gap_description", "remediation_plan",
                      "requirement_id", "assessment_id", "owner_id",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "priority", "status",
                          "start_date", "target_date", "completion_date",
                          "progress_percentage", "cost_estimate",
                          "gap_description", "remediation_plan",
                          "requirement_id", "assessment_id", "owner_id"],
        search_fields=["reference", "name", "description"],
        filters=["status", "priority", "requirement_id", "assessment_id"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the action plan."},
            "description": {"type": "string", "description": "Description."},
            "priority": {"type": "string", "description": "Priority level.", "enum": ["low", "medium", "high", "critical"]},
            "status": {"type": "string", "description": "Current status.", "enum": ["planned", "in_progress", "completed", "cancelled", "overdue"]},
            "start_date": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)."},
            "target_date": {"type": "string", "format": "date", "description": "Target completion date (YYYY-MM-DD)."},
            "completion_date": {"type": "string", "format": "date", "description": "Actual completion date (YYYY-MM-DD)."},
            "progress_percentage": {"type": "integer", "description": "Progress (0-100%).", "minimum": 0, "maximum": 100},
            "cost_estimate": {"type": "number", "description": "Estimated cost (decimal, up to 12 digits)."},
            "gap_description": {"type": "string", "description": "Description of the compliance gap to be addressed."},
            "remediation_plan": {"type": "string", "description": "Detailed remediation plan."},
            "requirement_id": {"type": "string", "description": "UUID of the related compliance requirement."},
            "assessment_id": {"type": "string", "description": "UUID of the source compliance assessment."},
            "owner_id": {"type": "string", "description": "UUID of the action plan owner (user)."},
        },
        filter_schemas={
            "status": {"type": "string", "description": "Filter by status.", "enum": ["planned", "in_progress", "completed", "cancelled", "overdue"]},
            "priority": {"type": "string", "description": "Filter by priority.", "enum": ["low", "medium", "high", "critical"]},
            "requirement_id": {"type": "string", "description": "Filter by requirement UUID."},
            "assessment_id": {"type": "string", "description": "Filter by assessment UUID."},
        },
        required_create_fields=["name", "gap_description", "remediation_plan", "priority", "target_date", "owner_id"],
        entity_description="action plan (remediation plan to address a compliance gap)",
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

    # ── Risk Assessment ────────────────────────────────────
    _register_crud(
        server, "risk_assessment", RiskAssessment, "risks.assessment",
        list_fields=["id", "reference", "name", "description",
                      "methodology", "status", "assessment_date",
                      "assessor_id", "risk_criteria_id",
                      "validated_by_id", "validated_at",
                      "next_review_date", "summary",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "methodology", "status",
                          "assessment_date", "assessor_id", "risk_criteria_id",
                          "next_review_date", "summary"],
        search_fields=["reference", "name", "description"],
        filters=["methodology", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the risk assessment."},
            "description": {"type": "string", "description": "Description."},
            "methodology": {"type": "string", "description": "Risk assessment methodology.", "enum": ["iso27005", "ebios_rm"]},
            "status": {"type": "string", "description": "Assessment status.", "enum": ["draft", "in_progress", "completed", "validated", "archived"]},
            "assessment_date": {"type": "string", "format": "date", "description": "Date of the assessment (YYYY-MM-DD)."},
            "assessor_id": {"type": "string", "description": "UUID of the lead assessor (user)."},
            "risk_criteria_id": {"type": "string", "description": "UUID of the risk criteria used for this assessment."},
            "next_review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
            "summary": {"type": "string", "description": "Executive summary of the assessment results."},
        },
        filter_schemas={
            "methodology": {"type": "string", "description": "Filter by methodology.", "enum": ["iso27005", "ebios_rm"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "in_progress", "completed", "validated", "archived"]},
        },
        required_create_fields=["name"],
        entity_description="risk assessment (formal risk analysis using ISO 27005 or EBIOS RM methodology)",
    )

    # ── Risk Criteria ──────────────────────────────────────
    _register_crud(
        server, "risk_criteria", RiskCriteria, "risks.criteria",
        list_fields=["id", "reference", "name", "description",
                      "risk_matrix", "acceptance_threshold",
                      "is_default", "status", "created_at", "updated_at"],
        writable_fields=["name", "description", "acceptance_threshold",
                          "is_default", "status"],
        search_fields=["name", "description"],
        filters=["status", "is_default"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the risk criteria set."},
            "description": {"type": "string", "description": "Description."},
            "acceptance_threshold": {"type": "integer", "description": "Risk level at or below which risks are considered acceptable.", "minimum": 0},
            "is_default": {"type": "boolean", "description": "Whether this is the default criteria set."},
            "status": {"type": "string", "description": "Status.", "enum": ["draft", "active", "archived"]},
        },
        filter_schemas={
            "status": {"type": "string", "description": "Filter by status.", "enum": ["draft", "active", "archived"]},
            "is_default": {"type": "boolean", "description": "Filter by default criteria."},
        },
        required_create_fields=["name"],
        has_approve=False,
        entity_description="risk criteria (risk matrix configuration with scales and acceptance threshold)",
    )

    # ── Scale Level ────────────────────────────────────────
    _register_crud(
        server, "scale_level", ScaleLevel, "risks.criteria",
        list_fields=["id", "criteria_id", "scale_type", "level",
                      "name", "description", "color"],
        writable_fields=["criteria_id", "scale_type", "level",
                          "name", "description", "color"],
        search_fields=["name", "description"],
        filters=["criteria_id", "scale_type"],
        field_schemas={
            "criteria_id": {"type": "string", "description": "UUID of the parent risk criteria."},
            "scale_type": {"type": "string", "description": "Which scale this level belongs to.", "enum": ["likelihood", "impact"]},
            "level": {"type": "integer", "description": "Numeric level (e.g. 1-5). Must be unique per criteria + scale_type.", "minimum": 1},
            "name": {"type": "string", "description": "Human-readable name (e.g. 'Very unlikely', 'Negligible')."},
            "description": {"type": "string", "description": "Description of what this level means."},
            "color": {"type": "string", "description": "Hex color code (e.g. '#4caf50')."},
        },
        filter_schemas={
            "criteria_id": {"type": "string", "description": "Filter by risk criteria UUID."},
            "scale_type": {"type": "string", "description": "Filter by scale type.", "enum": ["likelihood", "impact"]},
        },
        required_create_fields=["criteria_id", "scale_type", "level", "name"],
        scope_filtered=False,
        has_approve=False,
        entity_description="scale level (likelihood or impact scale level within a risk criteria set)",
    )

    # ── Risk Level ─────────────────────────────────────────
    _register_crud(
        server, "risk_level", RiskLevel, "risks.criteria",
        list_fields=["id", "criteria_id", "level", "name",
                      "description", "color", "requires_treatment"],
        writable_fields=["criteria_id", "level", "name",
                          "description", "color", "requires_treatment"],
        search_fields=["name", "description"],
        filters=["criteria_id", "requires_treatment"],
        field_schemas={
            "criteria_id": {"type": "string", "description": "UUID of the parent risk criteria."},
            "level": {"type": "integer", "description": "Numeric level. Must be unique per criteria.", "minimum": 1},
            "name": {"type": "string", "description": "Name (e.g. 'Low', 'Moderate', 'High')."},
            "description": {"type": "string", "description": "Description."},
            "color": {"type": "string", "description": "Hex color code."},
            "requires_treatment": {"type": "boolean", "description": "Whether risks at this level require treatment."},
        },
        filter_schemas={
            "criteria_id": {"type": "string", "description": "Filter by risk criteria UUID."},
            "requires_treatment": {"type": "boolean", "description": "Filter by whether treatment is required."},
        },
        required_create_fields=["criteria_id", "level", "name"],
        scope_filtered=False,
        has_approve=False,
        entity_description="risk level (named risk level within a risk criteria set, e.g. Low, Medium, High)",
    )

    # ── Risk ───────────────────────────────────────────────
    _register_crud(
        server, "risk", Risk, "risks.risk",
        list_fields=["id", "reference", "name", "description",
                      "risk_source", "status", "priority",
                      "initial_likelihood", "initial_impact", "initial_risk_level",
                      "current_likelihood", "current_impact", "current_risk_level",
                      "residual_likelihood", "residual_impact", "residual_risk_level",
                      "treatment_decision", "treatment_justification",
                      "assessment_id", "risk_owner_id",
                      "review_date", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "risk_source", "status", "priority",
                          "initial_likelihood", "initial_impact",
                          "current_likelihood", "current_impact",
                          "residual_likelihood", "residual_impact",
                          "treatment_decision", "treatment_justification",
                          "assessment_id", "risk_owner_id", "review_date"],
        search_fields=["reference", "name", "description"],
        filters=["status", "priority", "treatment_decision", "assessment_id"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the risk."},
            "description": {"type": "string", "description": "Description."},
            "risk_source": {"type": "string", "description": "How the risk was identified.", "enum": ["iso27005_analysis", "ebios_strategic", "ebios_operational", "incident", "audit", "compliance", "manual"]},
            "status": {"type": "string", "description": "Current risk status.", "enum": ["identified", "analyzed", "evaluated", "treatment_planned", "treatment_in_progress", "treated", "accepted", "closed", "monitoring"]},
            "priority": {"type": "string", "description": "Risk priority.", "enum": ["low", "medium", "high", "critical"]},
            "initial_likelihood": {"type": "integer", "description": "Initial likelihood level (from the risk criteria scale, typically 1-5).", "minimum": 1},
            "initial_impact": {"type": "integer", "description": "Initial impact level (from the risk criteria scale, typically 1-5).", "minimum": 1},
            "current_likelihood": {"type": "integer", "description": "Current likelihood level.", "minimum": 1},
            "current_impact": {"type": "integer", "description": "Current impact level.", "minimum": 1},
            "residual_likelihood": {"type": "integer", "description": "Residual likelihood after treatment.", "minimum": 1},
            "residual_impact": {"type": "integer", "description": "Residual impact after treatment.", "minimum": 1},
            "treatment_decision": {"type": "string", "description": "Risk treatment decision.", "enum": ["accept", "mitigate", "transfer", "avoid", "not_decided"]},
            "treatment_justification": {"type": "string", "description": "Justification for the treatment decision."},
            "assessment_id": {"type": "string", "description": "UUID of the parent risk assessment."},
            "risk_owner_id": {"type": "string", "description": "UUID of the risk owner (user)."},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
        },
        filter_schemas={
            "status": {"type": "string", "description": "Filter by risk status.", "enum": ["identified", "analyzed", "evaluated", "treatment_planned", "treatment_in_progress", "treated", "accepted", "closed", "monitoring"]},
            "priority": {"type": "string", "description": "Filter by priority.", "enum": ["low", "medium", "high", "critical"]},
            "treatment_decision": {"type": "string", "description": "Filter by treatment decision.", "enum": ["accept", "mitigate", "transfer", "avoid", "not_decided"]},
            "assessment_id": {"type": "string", "description": "Filter by risk assessment UUID."},
        },
        required_create_fields=["name", "assessment_id"],
        scope_filtered=False,
        entity_description="risk (identified risk in the risk register with likelihood/impact ratings)",
    )

    # ── Risk Treatment Plan ────────────────────────────────
    _register_crud(
        server, "risk_treatment_plan", RiskTreatmentPlan, "risks.treatment",
        list_fields=["id", "reference", "name", "description",
                      "treatment_type", "status",
                      "expected_residual_likelihood", "expected_residual_impact",
                      "cost_estimate", "start_date", "target_date",
                      "completion_date", "progress_percentage",
                      "risk_id", "owner_id",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "treatment_type", "status",
                          "expected_residual_likelihood", "expected_residual_impact",
                          "cost_estimate", "start_date", "target_date",
                          "completion_date", "progress_percentage",
                          "risk_id", "owner_id"],
        search_fields=["reference", "name", "description"],
        filters=["status", "treatment_type", "risk_id"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the treatment plan."},
            "description": {"type": "string", "description": "Description."},
            "treatment_type": {"type": "string", "description": "Type of risk treatment.", "enum": ["mitigate", "transfer", "avoid"]},
            "status": {"type": "string", "description": "Plan status.", "enum": ["planned", "in_progress", "completed", "cancelled", "overdue"]},
            "expected_residual_likelihood": {"type": "integer", "description": "Expected residual likelihood after treatment.", "minimum": 1},
            "expected_residual_impact": {"type": "integer", "description": "Expected residual impact after treatment.", "minimum": 1},
            "cost_estimate": {"type": "number", "description": "Estimated cost."},
            "start_date": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)."},
            "target_date": {"type": "string", "format": "date", "description": "Target completion date (YYYY-MM-DD)."},
            "completion_date": {"type": "string", "format": "date", "description": "Actual completion date (YYYY-MM-DD)."},
            "progress_percentage": {"type": "integer", "description": "Progress (0-100%).", "minimum": 0, "maximum": 100},
            "risk_id": {"type": "string", "description": "UUID of the risk being treated."},
            "owner_id": {"type": "string", "description": "UUID of the plan owner (user)."},
        },
        filter_schemas={
            "status": {"type": "string", "description": "Filter by status.", "enum": ["planned", "in_progress", "completed", "cancelled", "overdue"]},
            "treatment_type": {"type": "string", "description": "Filter by treatment type.", "enum": ["mitigate", "transfer", "avoid"]},
            "risk_id": {"type": "string", "description": "Filter by risk UUID."},
        },
        required_create_fields=["name", "treatment_type", "risk_id"],
        scope_filtered=False,
        entity_description="risk treatment plan (plan to mitigate, transfer, or avoid a risk)",
    )

    # ── Treatment Action ───────────────────────────────────
    _register_crud(
        server, "treatment_action", TreatmentAction, "risks.treatment",
        list_fields=["id", "treatment_plan_id", "description",
                      "owner_id", "target_date", "completion_date",
                      "status", "order", "created_at", "updated_at"],
        writable_fields=["treatment_plan_id", "description", "owner_id",
                          "target_date", "completion_date", "status", "order"],
        search_fields=["description"],
        filters=["treatment_plan_id", "status"],
        field_schemas={
            "treatment_plan_id": {"type": "string", "description": "UUID of the parent treatment plan."},
            "description": {"type": "string", "description": "Description of the action."},
            "owner_id": {"type": "string", "description": "UUID of the action owner (user)."},
            "target_date": {"type": "string", "format": "date", "description": "Target date (YYYY-MM-DD)."},
            "completion_date": {"type": "string", "format": "date", "description": "Actual completion date (YYYY-MM-DD)."},
            "status": {"type": "string", "description": "Action status.", "enum": ["planned", "in_progress", "completed", "cancelled"]},
            "order": {"type": "integer", "description": "Execution order.", "minimum": 0},
        },
        filter_schemas={
            "treatment_plan_id": {"type": "string", "description": "Filter by treatment plan UUID."},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["planned", "in_progress", "completed", "cancelled"]},
        },
        required_create_fields=["treatment_plan_id", "description"],
        scope_filtered=False,
        has_approve=False,
        entity_description="treatment action (individual action within a risk treatment plan)",
    )

    # ── Risk Acceptance ────────────────────────────────────
    _register_crud(
        server, "risk_acceptance", RiskAcceptance, "risks.acceptance",
        list_fields=["id", "reference", "risk_id", "status",
                      "risk_level_at_acceptance",
                      "justification", "conditions", "valid_until",
                      "review_date", "accepted_by_id", "accepted_at",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["risk_id", "justification", "conditions",
                          "valid_until", "review_date", "accepted_by_id"],
        search_fields=["justification", "conditions"],
        filters=["risk_id", "status"],
        field_schemas={
            "risk_id": {"type": "string", "description": "UUID of the accepted risk."},
            "justification": {"type": "string", "description": "Justification for accepting the risk."},
            "conditions": {"type": "string", "description": "Conditions under which the acceptance is valid."},
            "valid_until": {"type": "string", "format": "date", "description": "Acceptance expiry date (YYYY-MM-DD)."},
            "review_date": {"type": "string", "format": "date", "description": "Next review date (YYYY-MM-DD)."},
            "accepted_by_id": {"type": "string", "description": "UUID of the user who accepted the risk."},
        },
        filter_schemas={
            "risk_id": {"type": "string", "description": "Filter by risk UUID."},
            "status": {"type": "string", "description": "Filter by acceptance status.", "enum": ["active", "expired", "revoked", "renewed"]},
        },
        required_create_fields=["risk_id", "justification"],
        scope_filtered=False,
        has_approve=False,
        entity_description="risk acceptance (formal acceptance of a risk with justification and conditions)",
    )

    # ── Threat ─────────────────────────────────────────────
    _register_crud(
        server, "threat", Threat, "risks.threat",
        list_fields=["id", "reference", "name", "description",
                      "type", "origin", "category",
                      "typical_likelihood", "is_from_catalog",
                      "status", "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "type", "origin",
                          "category", "typical_likelihood",
                          "is_from_catalog", "status"],
        search_fields=["reference", "name", "description"],
        filters=["type", "origin", "category", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the threat."},
            "description": {"type": "string", "description": "Description."},
            "type": {"type": "string", "description": "Threat type.", "enum": ["deliberate", "accidental", "environmental", "other"]},
            "origin": {"type": "string", "description": "Threat origin.", "enum": ["human_internal", "human_external", "natural", "technical", "other"]},
            "category": {
                "type": "string",
                "description": "Threat category.",
                "enum": ["malware", "social_engineering", "unauthorized_access", "denial_of_service",
                         "data_breach", "physical_attack", "espionage", "fraud", "sabotage",
                         "human_error", "system_failure", "network_failure", "power_failure",
                         "natural_disaster", "fire", "water_damage", "theft", "vandalism",
                         "supply_chain", "insider_threat", "ransomware", "apt"],
            },
            "typical_likelihood": {"type": "integer", "description": "Typical likelihood level (from risk criteria scale).", "minimum": 1},
            "is_from_catalog": {"type": "boolean", "description": "Whether this threat comes from a predefined catalog."},
            "status": {"type": "string", "description": "Status.", "enum": ["active", "inactive"]},
        },
        filter_schemas={
            "type": {"type": "string", "description": "Filter by threat type.", "enum": ["deliberate", "accidental", "environmental", "other"]},
            "origin": {"type": "string", "description": "Filter by origin.", "enum": ["human_internal", "human_external", "natural", "technical", "other"]},
            "category": {"type": "string", "description": "Filter by category.", "enum": ["malware", "social_engineering", "unauthorized_access", "denial_of_service", "data_breach", "physical_attack", "espionage", "fraud", "sabotage", "human_error", "system_failure", "network_failure", "power_failure", "natural_disaster", "fire", "water_damage", "theft", "vandalism", "supply_chain", "insider_threat", "ransomware", "apt"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["active", "inactive"]},
        },
        required_create_fields=["name", "type"],
        entity_description="threat (threat to information security, e.g. malware, social engineering, natural disaster)",
    )

    # ── Vulnerability ──────────────────────────────────────
    _register_crud(
        server, "vulnerability", Vulnerability, "risks.vulnerability",
        list_fields=["id", "reference", "name", "description",
                      "category", "severity",
                      "cve_references", "remediation_guidance",
                      "is_from_catalog", "status",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["name", "description", "category", "severity",
                          "affected_asset_types", "cve_references",
                          "remediation_guidance", "is_from_catalog", "status"],
        search_fields=["reference", "name", "description"],
        filters=["category", "severity", "status"],
        field_schemas={
            "name": {"type": "string", "description": "Name of the vulnerability."},
            "description": {"type": "string", "description": "Description."},
            "category": {
                "type": "string",
                "description": "Vulnerability category.",
                "enum": ["configuration_weakness", "missing_patch", "design_flaw", "coding_error",
                         "weak_authentication", "insufficient_logging", "lack_of_encryption",
                         "physical_vulnerability", "organizational_weakness", "human_factor",
                         "obsolescence", "insufficient_backup", "network_exposure",
                         "third_party_dependency"],
            },
            "severity": {"type": "string", "description": "Severity level.", "enum": ["low", "medium", "high", "critical"]},
            "affected_asset_types": {"type": "array", "description": "JSON array of affected asset types.", "items": {"type": "string"}},
            "cve_references": {"type": "array", "description": "JSON array of CVE references (e.g. ['CVE-2024-1234']).", "items": {"type": "string"}},
            "remediation_guidance": {"type": "string", "description": "Guidance for remediation."},
            "is_from_catalog": {"type": "boolean", "description": "Whether from a predefined catalog."},
            "status": {"type": "string", "description": "Status.", "enum": ["identified", "confirmed", "mitigated", "accepted", "closed"]},
        },
        filter_schemas={
            "category": {"type": "string", "description": "Filter by category.", "enum": ["configuration_weakness", "missing_patch", "design_flaw", "coding_error", "weak_authentication", "insufficient_logging", "lack_of_encryption", "physical_vulnerability", "organizational_weakness", "human_factor", "obsolescence", "insufficient_backup", "network_exposure", "third_party_dependency"]},
            "severity": {"type": "string", "description": "Filter by severity.", "enum": ["low", "medium", "high", "critical"]},
            "status": {"type": "string", "description": "Filter by status.", "enum": ["identified", "confirmed", "mitigated", "accepted", "closed"]},
        },
        required_create_fields=["name"],
        entity_description="vulnerability (weakness that could be exploited by a threat)",
    )

    # ── ISO 27005 Risk ─────────────────────────────────────
    _register_crud(
        server, "iso27005_risk", ISO27005Risk, "risks.iso27005",
        list_fields=["id", "reference", "assessment_id", "threat_id", "vulnerability_id",
                      "threat_likelihood", "vulnerability_exposure",
                      "combined_likelihood", "max_impact",
                      "impact_confidentiality", "impact_integrity", "impact_availability",
                      "risk_level", "existing_controls",
                      "risk_id", "description",
                      "is_approved", "created_at", "updated_at"],
        writable_fields=["assessment_id", "threat_id", "vulnerability_id",
                          "threat_likelihood", "vulnerability_exposure",
                          "combined_likelihood",
                          "impact_confidentiality", "impact_integrity", "impact_availability",
                          "max_impact", "existing_controls",
                          "risk_id", "description"],
        search_fields=["description", "existing_controls"],
        filters=["assessment_id", "threat_id", "vulnerability_id"],
        field_schemas={
            "assessment_id": {"type": "string", "description": "UUID of the parent risk assessment."},
            "threat_id": {"type": "string", "description": "UUID of the threat."},
            "vulnerability_id": {"type": "string", "description": "UUID of the vulnerability."},
            "threat_likelihood": {"type": "integer", "description": "Likelihood rating of the threat.", "minimum": 1},
            "vulnerability_exposure": {"type": "integer", "description": "Exposure rating of the vulnerability.", "minimum": 1},
            "combined_likelihood": {"type": "integer", "description": "Combined likelihood (auto-calculated if not provided).", "minimum": 1},
            "impact_confidentiality": {"type": "integer", "description": "Impact on confidentiality.", "minimum": 1},
            "impact_integrity": {"type": "integer", "description": "Impact on integrity.", "minimum": 1},
            "impact_availability": {"type": "integer", "description": "Impact on availability.", "minimum": 1},
            "max_impact": {"type": "integer", "description": "Maximum of the three impact dimensions (auto-calculated).", "minimum": 1},
            "existing_controls": {"type": "string", "description": "Description of existing controls."},
            "risk_id": {"type": "string", "description": "UUID of the associated risk in the risk register."},
            "description": {"type": "string", "description": "Additional description."},
        },
        filter_schemas={
            "assessment_id": {"type": "string", "description": "Filter by risk assessment UUID."},
            "threat_id": {"type": "string", "description": "Filter by threat UUID."},
            "vulnerability_id": {"type": "string", "description": "Filter by vulnerability UUID."},
        },
        required_create_fields=["assessment_id", "threat_id", "vulnerability_id"],
        scope_filtered=False,
        has_approve=False,
        entity_description="ISO 27005 risk scenario (threat × vulnerability analysis per ISO 27005)",
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
        "List platform users with optional search and filters. Returns user profile information.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search across email, first name, and last name."},
                "is_active": {"type": "boolean", "description": "Filter by active status. True = active users, False = disabled users."},
                "limit": {"type": "integer", "description": "Max items (default 25, max 100).", "default": 25, "minimum": 1, "maximum": 100},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0, "minimum": 0},
            },
        },
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
        "Get detailed information about a user by UUID.",
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
        "Get information about the currently authenticated user. No parameters needed.",
        {"type": "object", "properties": {}},
        get_me,
    )

    # List groups
    server.register_tool(
        "list_groups",
        "List all user groups (roles) on the platform. Groups define permission sets.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by group name."},
                "limit": {"type": "integer", "description": "Max items (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
        },
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
        "Get group details including its assigned permissions (as codenames) and user count.",
        _id_schema(),
        get_group,
    )

    # List permissions
    server.register_tool(
        "list_permissions",
        "List all available permissions. Permissions follow the format 'module.feature.action'. "
        "Modules: context, assets, compliance, risks, system. "
        "Actions: create, read, update, delete, approve, access, assess, validate.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by codename or name."},
                "module": {"type": "string", "description": "Filter by module.", "enum": ["context", "assets", "compliance", "risks", "system"]},
                "feature": {"type": "string", "description": "Filter by feature (e.g. 'scope', 'framework', 'risk')."},
                "limit": {"type": "integer", "description": "Max items (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
        },
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
        "List authentication and access events. Tracks login/logout, token refreshes, "
        "password changes, account locks, and passkey events.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by email attempted."},
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type.",
                    "enum": ["login_success", "login_failed", "logout", "token_refresh",
                             "password_change", "account_locked", "account_unlocked",
                             "passkey_login_success", "passkey_login_failed",
                             "passkey_registered", "passkey_deleted"],
                },
                "user_id": {"type": "string", "description": "Filter by user UUID."},
                "limit": {"type": "integer", "description": "Max items (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
        },
        require_perm("system.audit_trail.read")(
            _list_handler(AccessLog,
                          ["id", "timestamp", "user_id", "email_attempted",
                           "event_type", "ip_address", "failure_reason"],
                          search_fields=["email_attempted"],
                          filters=["event_type", "user_id"],
                          scope_filtered=False)
        ),
    )


# ── Helpers Module ─────────────────────────────────────────

def _register_helpers_tools(server):
    HelpContent = _get_model("helpers", "HelpContent")

    # List help contents
    server.register_tool(
        "list_help_contents",
        "List contextual help content entries. Help content is keyed by page/feature "
        "and language, providing in-app guidance and documentation.",
        {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by key, title, or content."},
                "language": {"type": "string", "description": "Filter by ISO 639-1 language code (e.g. 'fr', 'en')."},
                "limit": {"type": "integer", "description": "Max items (default 25, max 100).", "default": 25},
                "offset": {"type": "integer", "description": "Pagination offset.", "default": 0},
            },
        },
        require_perm("context.config.read")(
            _list_handler(HelpContent,
                          ["id", "key", "language", "title", "body", "updated_at"],
                          search_fields=["key", "title", "body"],
                          filters=["language"],
                          scope_filtered=False)
        ),
    )

    # Get help content
    server.register_tool(
        "get_help_content",
        "Get a specific help content entry by its ID.",
        _id_schema(),
        require_perm("context.config.read")(
            _get_handler(HelpContent,
                         ["id", "key", "language", "title", "body", "updated_at"],
                         scope_filtered=False)
        ),
    )

    # Get help content by key and language
    @require_perm("context.config.read")
    def get_help_by_key(user, arguments):
        key = arguments.get("key")
        language = arguments.get("language", "fr")
        if not key:
            raise InvalidParamsError("key is required.")
        try:
            obj = HelpContent.objects.get(key=key, language=language)
        except HelpContent.DoesNotExist:
            return _error(f"Help content not found for key='{key}', language='{language}'.")
        return _serialize_obj(obj, ["id", "key", "language", "title", "body", "updated_at"])

    server.register_tool(
        "get_help_by_key",
        "Get help content by its unique key and language. "
        "Keys follow the pattern 'context.scope_list', 'compliance.framework_detail', etc.",
        {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Unique identifier of the page or feature (e.g. 'context.scope_list')."},
                "language": {"type": "string", "description": "ISO 639-1 language code (default 'fr').", "default": "fr"},
            },
            "required": ["key"],
        },
        get_help_by_key,
    )

    # Create help content
    server.register_tool(
        "create_help_content",
        "Create a new help content entry. The key+language combination must be unique.",
        {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Unique identifier (e.g. 'context.scope_list')."},
                "language": {"type": "string", "description": "ISO 639-1 language code (e.g. 'fr', 'en').", "default": "fr"},
                "title": {"type": "string", "description": "Help content title."},
                "body": {"type": "string", "description": "Help content body (supports HTML/Markdown)."},
            },
            "required": ["key", "title", "body"],
        },
        require_perm("context.config.update")(
            _create_handler(HelpContent, ["key", "language", "title", "body"], scope_filtered=False)
        ),
    )

    # Update help content
    @require_perm("context.config.update")
    def update_help_content(user, arguments):
        pk = arguments.get("id")
        if not pk:
            raise InvalidParamsError("id is required.")
        try:
            obj = HelpContent.objects.get(pk=pk)
        except HelpContent.DoesNotExist:
            return _error("Help content not found.")
        for field in ["key", "language", "title", "body"]:
            if field in arguments:
                setattr(obj, field, arguments[field])
        try:
            obj.full_clean()
            obj.save()
        except (ValidationError, Exception) as e:
            return _error(str(e))
        return _serialize_obj(obj, ["id", "key", "language", "title", "body", "updated_at"])

    server.register_tool(
        "update_help_content",
        "Update an existing help content entry. Only provide fields that need to change.",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "UUID or ID of the help content to update."},
                "key": {"type": "string", "description": "Unique identifier."},
                "language": {"type": "string", "description": "ISO 639-1 language code."},
                "title": {"type": "string", "description": "Title."},
                "body": {"type": "string", "description": "Content body."},
            },
            "required": ["id"],
        },
        update_help_content,
    )

    # Delete help content
    server.register_tool(
        "delete_help_content",
        "Delete a help content entry by its ID.",
        _id_schema(),
        require_perm("context.config.update")(
            _delete_handler(HelpContent, scope_filtered=False)
        ),
    )
