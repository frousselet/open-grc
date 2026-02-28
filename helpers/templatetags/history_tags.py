from django import template

register = template.Library()

HISTORY_TYPE_LABELS = {
    "+": "Création",
    "~": "Modification",
    "-": "Suppression",
}

HISTORY_TYPE_BADGES = {
    "+": "success",
    "~": "warning",
    "-": "danger",
}


@register.filter
def history_type_label(value):
    return HISTORY_TYPE_LABELS.get(value, value)


@register.filter
def history_type_badge(value):
    return HISTORY_TYPE_BADGES.get(value, "secondary")


APPROVAL_FIELDS = {"is_approved", "approved_by", "approved_by_id", "approved_at"}
HIDDEN_FIELDS = APPROVAL_FIELDS | {"version"}


@register.simple_tag
def history_changes(record):
    """Return a dict with changes, is_approval flag, and approved status.

    Uses django-simple-history's delta to compute diffs against the previous record.
    Filters out approval and version fields from regular changes, and detects
    approval-only modifications.
    """
    empty = {"changes": [], "is_approval": False, "approved": False}
    if record.history_type == "+":
        return empty
    try:
        prev = record.prev_record
    except Exception:
        return empty
    if prev is None:
        return empty

    delta = record.diff_against(prev)
    approval_changes = []
    regular_changes = []
    for change in delta.changes:
        field_name = change.field
        if field_name in HIDDEN_FIELDS:
            if field_name in APPROVAL_FIELDS:
                approval_changes.append(change)
            continue
        # Try to get verbose name from the model
        try:
            field_obj = record.instance_type._meta.get_field(field_name)
            verbose = str(field_obj.verbose_name)
        except Exception:
            verbose = field_name.replace("_", " ").capitalize()

        old_val = change.old if change.old not in (None, "") else "—"
        new_val = change.new if change.new not in (None, "") else "—"
        regular_changes.append({"field": verbose, "old": old_val, "new": new_val})

    if not regular_changes and approval_changes:
        return {
            "changes": [],
            "is_approval": True,
            "approved": bool(record.is_approved),
        }

    return {"changes": regular_changes, "is_approval": False, "approved": False}


@register.simple_tag
def history_snapshot(record):
    """Return all field values of a historical record for initial creation display."""
    fields = []
    excluded = {
        "id", "history_id", "history_date", "history_change_reason",
        "history_type", "history_user", "history_user_id",
        "created_at", "updated_at",
        "is_approved", "approved_by", "approved_by_id", "approved_at", "version",
    }
    for field in record._meta.get_fields():
        name = getattr(field, "attname", None) or field.name
        if name in excluded or name.startswith("history_"):
            continue
        # Skip reverse relations
        if not hasattr(field, "column"):
            continue
        try:
            value = getattr(record, name)
        except Exception:
            continue
        if value in (None, ""):
            continue

        # Verbose name
        try:
            model_field = record.instance_type._meta.get_field(field.name)
            verbose = str(model_field.verbose_name)
        except Exception:
            verbose = field.name.replace("_", " ").capitalize()

        fields.append({"field": verbose, "value": value})
    return fields
