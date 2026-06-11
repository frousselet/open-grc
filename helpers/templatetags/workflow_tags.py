"""Template tags rendering lifecycle workflow state for any element."""

from django import template

register = template.Library()

# Workflow State.tone -> Bootstrap badge context.
_TONE_CLASSES = {
    "neutral": "secondary",
    "muted": "secondary",
    "secondary": "secondary",
    "info": "info",
    "primary": "primary",
    "warning": "warning",
    "success": "success",
    "danger": "danger",
    "dark": "dark",
}


@register.inclusion_tag("includes/workflow_badge.html")
def workflow_badge(obj):
    """Render the lifecycle state badge of any lifecycle-bearing element."""
    try:
        state = obj.get_lifecycle_state()
    except Exception:
        return {"label": getattr(obj, "workflow_state", ""), "badge_class": "secondary"}
    return {
        "label": state.label,
        "badge_class": _TONE_CLASSES.get(state.tone, "secondary"),
    }
