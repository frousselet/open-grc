from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def sortable_th(context, field_name, label, css_class=""):
    """Render a sortable <th> element.

    Sorting is persisted via JS (saved to user preferences).
    No sort params are added to the URL.

    Usage: {% sortable_th "name" "Name" %}
           {% sortable_th "name" "Name" "text-end" %}
    """
    current_sort = context.get("current_sort", "")
    current_order = context.get("current_order", "asc")

    if current_sort == field_name:
        new_order = "desc" if current_order == "asc" else "asc"
    else:
        new_order = "asc"

    # Sort indicator
    if current_sort == field_name:
        if current_order == "asc":
            icon = '<i class="bi bi-sort-up sort-icon sort-icon-active ms-1"></i>'
        else:
            icon = '<i class="bi bi-sort-down sort-icon sort-icon-active ms-1"></i>'
    else:
        icon = '<i class="bi bi-arrow-down-up sort-icon sort-icon-idle ms-1"></i>'

    class_attr = f' class="{css_class}"' if css_class else ""

    return format_html(
        '<th{class_attr}><a href="#" class="sortable-th text-decoration-none text-reset"'
        ' data-sort-field="{field}" data-sort-order="{order}"'
        ' style="white-space:nowrap">{label}{icon}</a></th>',
        class_attr=format_html(class_attr),
        field=field_name,
        order=new_order,
        label=label,
        icon=format_html(icon),
    )
