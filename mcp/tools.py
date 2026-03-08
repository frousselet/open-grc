"""
MCP tool definitions covering all Open GRC API functionality.

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
        DecimalField, JSONField,
    )
    int_types = (IntegerField, PositiveIntegerField, PositiveSmallIntegerField,
                 SmallIntegerField, BigIntegerField)
    if isinstance(field, int_types):
        try:
            return int(value)
        except (ValueError, TypeError):
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


def _create_handler(model_class, writable_fields, scope_filtered=True):
    """Create a generic create handler."""
    def handler(user, arguments):
        kwargs = {}
        for field_name in writable_fields:
            if field_name in arguments:
                kwargs[field_name] = _coerce_field_value(
                    model_class, field_name, arguments[field_name])
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
                setattr(obj, field_name, _coerce_field_value(
                    model_class, field_name, arguments[field_name]))
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
    _register_context_tools(server)
    _register_assets_tools(server)
    _register_compliance_tools(server)
    _register_risks_tools(server)
    _register_accounts_tools(server)


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

    scope_fields = ["id", "reference", "name", "description", "status", "type",
                    "effective_date", "review_date", "version", "is_approved", "created_at"]
    scope_writable = ["name", "description", "status", "type", "effective_date",
                      "review_date", "parent_scope_id"]

    _register_crud(server, "scope", Scope, "context.scope",
                   list_fields=scope_fields,
                   writable_fields=scope_writable,
                   search_fields=["name", "description"],
                   filters=["status", "type"],
                   field_overrides={"description": _html_field("Description")})

    issue_fields = ["id", "reference", "name", "description", "category", "severity",
                    "status", "is_approved", "created_at"]
    issue_writable = ["name", "description", "category", "severity", "status"]

    _register_crud(server, "issue", Issue, "context.issue",
                   list_fields=issue_fields,
                   writable_fields=issue_writable,
                   search_fields=["name", "description"],
                   filters=["category", "severity", "status"],
                   field_overrides=_HTML_DESC)

    stakeholder_fields = ["id", "reference", "name", "description", "type", "influence_level",
                          "status", "is_approved", "created_at"]
    stakeholder_writable = ["name", "description", "type", "influence_level", "status"]

    _register_crud(server, "stakeholder", Stakeholder, "context.stakeholder",
                   list_fields=stakeholder_fields,
                   writable_fields=stakeholder_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   field_overrides=_HTML_DESC)

    expectation_fields = ["id", "reference", "name", "description", "type", "priority",
                          "stakeholder_id", "created_at"]
    expectation_writable = ["name", "description", "type", "priority", "stakeholder_id"]

    _register_crud(server, "expectation", StakeholderExpectation, "context.expectation",
                   list_fields=expectation_fields,
                   writable_fields=expectation_writable,
                   search_fields=["name", "description"],
                   filters=["stakeholder_id", "type"],
                   scope_filtered=False,
                   field_overrides=_HTML_DESC)

    objective_fields = ["id", "reference", "name", "description", "type", "priority",
                        "status", "target_date", "is_approved", "created_at"]
    objective_writable = ["name", "description", "type", "priority", "status", "target_date"]

    _register_crud(server, "objective", Objective, "context.objective",
                   list_fields=objective_fields,
                   writable_fields=objective_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status", "priority"],
                   field_overrides=_HTML_DESC)

    swot_fields = ["id", "reference", "name", "description", "status", "is_approved", "created_at"]
    swot_writable = ["name", "description", "status"]

    _register_crud(server, "swot_analysis", SwotAnalysis, "context.swot",
                   list_fields=swot_fields,
                   writable_fields=swot_writable,
                   search_fields=["name", "description"],
                   filters=["status"],
                   field_overrides=_HTML_DESC)

    swot_item_fields = ["id", "reference", "type", "title", "description", "impact",
                        "priority", "order", "analysis_id", "created_at"]
    swot_item_writable = ["type", "title", "description", "impact", "priority", "order", "analysis_id"]

    _register_crud(server, "swot_item", SwotItem, "context.swot",
                   list_fields=swot_item_fields,
                   writable_fields=swot_item_writable,
                   search_fields=["title", "description"],
                   filters=["analysis_id", "type"],
                   scope_filtered=False,
                   field_overrides=_HTML_DESC)

    role_fields = ["id", "reference", "name", "description", "type", "status",
                   "is_approved", "created_at"]
    role_writable = ["name", "description", "type", "status"]

    _register_crud(server, "role", Role, "context.role",
                   list_fields=role_fields,
                   writable_fields=role_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   field_overrides=_HTML_DESC)

    activity_fields = ["id", "reference", "name", "description", "type", "status",
                       "is_approved", "created_at"]
    activity_writable = ["name", "description", "type", "status", "parent_activity_id"]

    _register_crud(server, "activity", Activity, "context.activity",
                   list_fields=activity_fields,
                   writable_fields=activity_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   field_overrides=_HTML_DESC)

    site_fields = ["id", "reference", "name", "description", "type", "status",
                   "address", "city", "country", "is_approved", "created_at"]
    site_writable = ["name", "description", "type", "status", "address", "city",
                     "country", "parent_site_id"]

    _register_crud(server, "site", Site, "context.site",
                   list_fields=site_fields,
                   writable_fields=site_writable,
                   search_fields=["name", "description", "city"],
                   filters=["type", "status", "country"],
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)


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
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

    ag_fields = ["id", "name", "description", "type", "status", "is_approved", "created_at"]
    ag_writable = ["name", "description", "type", "status", "owner_id"]

    _register_crud(server, "asset_group", AssetGroup, "assets.group",
                   list_fields=ag_fields,
                   writable_fields=ag_writable,
                   search_fields=["name", "description"],
                   filters=["type", "status"],
                   field_overrides=_HTML_DESC)

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

    _register_crud(server, "supplier", Supplier, "assets.supplier",
                   list_fields=sup_fields,
                   writable_fields=sup_writable,
                   search_fields=["reference", "name", "description", "contact_name"],
                   filters=["type", "criticality", "status"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "notes": _html_field("Notes"),
                   })

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
    _sup_html = {"description": _html_field("Description"), "notes": _html_field("Notes")}
    create_sup_props = {f: _sup_html.get(f, {"type": "string", "description": f}) for f in sup_writable}
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
        update_sup_props[f] = _sup_html.get(f, {"type": "string", "description": f})
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
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

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
                   field_overrides={
                       "justification": _html_field("Justification"),
                       "context": _html_field("Context"),
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
                   field_overrides={
                       "description": _html_field("Description"),
                       "evidence": _html_field("Evidence"),
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
                 "category", "compliance_level", "status", "is_approved", "created_at"]
    fw_writable = ["name", "short_name", "description", "type", "category", "status",
                   "owner_id"]

    _register_crud(server, "framework", Framework, "compliance.framework",
                   list_fields=fw_fields,
                   writable_fields=fw_writable,
                   search_fields=["reference", "name", "short_name", "description"],
                   filters=["type", "category", "status"],
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

    req_fields = ["id", "reference", "requirement_number", "name", "description", "type",
                  "compliance_status", "compliance_level", "priority", "is_applicable",
                  "framework_id", "section_id", "is_approved", "created_at"]
    req_writable = ["requirement_number", "name", "description", "guidance", "type",
                    "compliance_status", "compliance_level",
                    "priority", "is_applicable", "compliance_evidence", "compliance_gaps",
                    "framework_id", "section_id", "owner_id"]

    _register_crud(server, "requirement", Requirement, "compliance.requirement",
                   list_fields=req_fields,
                   writable_fields=req_writable,
                   search_fields=["reference", "requirement_number", "name", "description"],
                   filters=["framework_id", "section_id", "compliance_status", "type", "priority"],
                   scope_filtered=False,
                   field_overrides={
                       "description": _html_field("Description"),
                       "guidance": _html_field("Implementation recommendations"),
                       "compliance_evidence": _html_field("Compliance evidence"),
                       "compliance_gaps": _html_field("Identified gaps"),
                   })

    ca_fields = ["id", "name", "description", "assessment_date", "status",
                 "overall_compliance_level", "total_requirements",
                 "compliant_count", "non_compliant_count",
                 "framework_id", "is_approved", "created_at"]
    ca_writable = ["name", "description", "assessment_date", "status",
                   "framework_id", "assessor_id"]

    _register_crud(server, "compliance_assessment", ComplianceAssessment,
                   "compliance.assessment",
                   list_fields=ca_fields,
                   writable_fields=ca_writable,
                   search_fields=["name", "description"],
                   filters=["framework_id", "status"],
                   field_overrides=_HTML_DESC)

    ar_fields = ["id", "assessment_id", "requirement_id", "compliance_status",
                 "compliance_level", "evidence", "gaps", "assessed_at"]
    ar_writable = ["assessment_id", "requirement_id", "compliance_status",
                   "compliance_level", "evidence", "gaps"]

    _register_crud(server, "assessment_result", AssessmentResult, "compliance.assessment",
                   list_fields=ar_fields,
                   writable_fields=ar_writable,
                   search_fields=[],
                   filters=["assessment_id", "requirement_id", "compliance_status"],
                   scope_filtered=False,
                   has_approve=False,
                   field_overrides={
                       "evidence": _html_field("Evidence"),
                       "gaps": _html_field("Gaps"),
                   })

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
                   field_overrides={
                       "description": _html_field("Description"),
                       "justification": _html_field("Justification"),
                   })

    ap_fields = ["id", "reference", "name", "description", "priority", "status",
                 "target_date", "progress_percentage",
                 "requirement_id", "assessment_id", "is_approved", "created_at"]
    ap_writable = ["name", "description", "priority", "status", "target_date",
                   "progress_percentage", "requirement_id", "assessment_id", "owner_id"]

    _register_crud(server, "action_plan", ComplianceActionPlan, "compliance.action_plan",
                   list_fields=ap_fields,
                   writable_fields=ap_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "priority", "requirement_id", "assessment_id"],
                   field_overrides=_HTML_DESC)

    # ── Controls ──────────────────────────────────────────
    ComplianceControl = _get_model("compliance", "ComplianceControl")
    ctrl_fields = ["id", "reference", "name", "description", "objective",
                   "frequency", "status", "result",
                   "planned_date", "completion_date",
                   "owner_id", "support_asset_id", "site_id", "supplier_id",
                   "is_approved", "created_at"]
    ctrl_writable = ["name", "description", "objective",
                     "frequency", "status", "result",
                     "planned_date", "completion_date",
                     "owner_id", "support_asset_id", "site_id", "supplier_id"]

    _register_crud(server, "compliance_control", ComplianceControl, "compliance.control",
                   list_fields=ctrl_fields,
                   writable_fields=ctrl_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "result", "frequency", "owner_id",
                            "support_asset_id", "site_id", "supplier_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "objective": _html_field("Control objective"),
                       "evidence": _html_field("Evidence"),
                       "findings": _html_field("Findings"),
                   })

    # ── Audits ────────────────────────────────────────────
    ComplianceAudit = _get_model("compliance", "ComplianceAudit")
    audit_fields = ["id", "reference", "name", "description",
                    "audit_type", "status",
                    "planned_start_date", "planned_end_date",
                    "actual_start_date", "actual_end_date",
                    "lead_auditor_id", "control_body_id",
                    "is_approved", "created_at"]
    audit_writable = ["name", "description",
                      "audit_type", "status",
                      "planned_start_date", "planned_end_date",
                      "actual_start_date", "actual_end_date",
                      "lead_auditor_id", "control_body_id"]

    _register_crud(server, "compliance_audit", ComplianceAudit, "compliance.audit",
                   list_fields=audit_fields,
                   writable_fields=audit_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["audit_type", "status", "lead_auditor_id", "control_body_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "objectives": _html_field("Audit objectives"),
                       "conclusion": _html_field("Conclusion"),
                       "findings_summary": _html_field("Findings summary"),
                   })

    # ── Control Bodies & Authorities ──────────────────────
    ControlBody = _get_model("compliance", "ControlBody")
    cb_fields = ["id", "reference", "name", "description",
                 "is_accredited", "accreditation_details",
                 "contact_name", "contact_email", "contact_phone",
                 "website", "country", "is_approved", "created_at"]
    cb_writable = ["name", "description",
                   "is_accredited", "accreditation_details",
                   "contact_name", "contact_email", "contact_phone",
                   "website", "address", "country"]

    _register_crud(server, "control_body", ControlBody, "compliance.control_body",
                   list_fields=cb_fields,
                   writable_fields=cb_writable,
                   search_fields=["reference", "name", "description", "country"],
                   filters=["is_accredited", "country"],
                   scope_filtered=False,
                   field_overrides=_HTML_DESC)

    # ── Auditors ──────────────────────────────────────────
    Auditor = _get_model("compliance", "Auditor")
    auditor_fields = ["id", "reference", "first_name", "last_name",
                      "email", "phone", "control_body_id",
                      "certifications", "specializations", "created_at"]
    auditor_writable = ["first_name", "last_name", "email", "phone",
                        "control_body_id", "certifications", "specializations"]

    _register_crud(server, "auditor", Auditor, "compliance.auditor",
                   list_fields=auditor_fields,
                   writable_fields=auditor_writable,
                   search_fields=["reference", "first_name", "last_name",
                                  "email", "certifications"],
                   filters=["control_body_id"],
                   scope_filtered=False,
                   has_approve=False)

    # ── Findings ─────────────────────────────────────────
    Finding = _get_model("compliance", "Finding")
    finding_fields = ["id", "reference", "name", "description",
                      "finding_type",
                      "audit_id", "control_id",
                      "is_approved", "created_at"]
    finding_writable = ["name", "description", "finding_type",
                        "audit_id", "control_id", "evidence"]

    _register_crud(server, "finding", Finding, "compliance.finding",
                   list_fields=finding_fields,
                   writable_fields=finding_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["finding_type", "audit_id", "control_id"],
                   field_overrides={
                       "description": _html_field("Description"),
                       "evidence": _html_field("Evidence"),
                   })


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
                   field_overrides=_HTML_DESC)

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
                   field_overrides=_HTML_DESC)

    risk_fields = ["id", "reference", "name", "description", "status", "priority",
                   "current_risk_level", "assessment_id",
                   "is_approved", "created_at"]
    risk_writable = ["name", "description", "status", "priority",
                     "initial_likelihood", "initial_impact",
                     "current_likelihood", "current_impact",
                     "residual_likelihood", "residual_impact",
                     "treatment_strategy", "assessment_id", "risk_owner_id"]

    _register_crud(server, "risk", Risk, "risks.risk",
                   list_fields=risk_fields,
                   writable_fields=risk_writable,
                   search_fields=["reference", "name", "description"],
                   filters=["status", "priority", "assessment_id"],
                   scope_filtered=False,
                   field_overrides=_HTML_DESC)

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
                   field_overrides={
                       "description": _html_field("Description"),
                       "treatment_type": {
                           "type": "string",
                           "description": "Treatment strategy type",
                           "enum": ["mitigate", "transfer", "avoid"],
                       },
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
                   field_overrides=_HTML_DESC)

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
                   has_approve=False,
                   field_overrides={
                       "justification": _html_field("Justification"),
                       "conditions": _html_field("Conditions"),
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
                   has_approve=False,
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
                kwargs[field_name] = arguments[field_name]
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
        for field_name in writable_fields:
            if field_name in arguments:
                setattr(obj, field_name, arguments[field_name])
        if image_url:
            try:
                _apply_logo_from_url(obj, image_url)
            except ValueError as e:
                return _error(str(e))
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

    if hasattr(supplier, "is_approved"):
        supplier.is_approved = False
        supplier.approved_by = None
        supplier.approved_at = None
    if hasattr(supplier, "version"):
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
                   field_overrides=None):
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
        _obj_schema(create_props),
        require_perm(f"{perm_prefix}.create")(
            _create_handler(model_class, writable_fields, scope_filtered)
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
            _update_handler(model_class, writable_fields, scope_filtered)
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
