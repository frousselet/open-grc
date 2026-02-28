from django import template
from django.utils.safestring import mark_safe

register = template.Library()

DIC_COLORS = {
    0: ("secondary", "N"),
    1: ("success", "F"),
    2: ("info", "M"),
    3: ("warning", "É"),
    4: ("danger", "C"),
}

DIC_LABELS = {
    0: "Négligeable",
    1: "Faible",
    2: "Moyen",
    3: "Élevé",
    4: "Critique",
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
