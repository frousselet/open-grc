from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

register = template.Library()

DIC_COLORS = {
    0: ("secondary", "N"),
    1: ("success", "L"),
    2: ("info", "M"),
    3: ("warning", "H"),
    4: ("danger", "C"),
}

DIC_LABELS = {
    0: _("Negligible"),
    1: _("Low"),
    2: _("Medium"),
    3: _("High"),
    4: _("Critical"),
}


@register.filter
def dic_badge(value):
    """Render a DIC level as a colored Bootstrap badge."""
    try:
        level = int(value)
    except (TypeError, ValueError):
        return "—"
    color, short = DIC_COLORS.get(level, ("secondary", "?"))
    label = DIC_LABELS.get(level, "?")
    return mark_safe(
        f'<span class="badge text-bg-{color}" title="{label}">{level}</span>'
    )
