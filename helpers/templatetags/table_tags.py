from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def sortable_th(context, field_name, label, css_class=""):
    """Render a sortable <th> element.

    Usage: {% sortable_th "name" "Name" %}
           {% sortable_th "name" "Name" "text-end" %}
    """
    request = context.get("request")
    current_sort = context.get("current_sort", "")
    current_order = context.get("current_order", "asc")

    # Build the new URL preserving existing query params
    params = request.GET.copy()

    if current_sort == field_name:
        new_order = "desc" if current_order == "asc" else "asc"
    else:
        new_order = "asc"

    params["sort"] = field_name
    params["order"] = new_order
    # Reset page when sorting changes
    params.pop("page", None)

    url = "?" + params.urlencode()

    # Sort indicator
    if current_sort == field_name:
        if current_order == "asc":
            icon = '<i class="bi bi-sort-up ms-1" style="font-size:.75rem;opacity:.7"></i>'
        else:
            icon = '<i class="bi bi-sort-down ms-1" style="font-size:.75rem;opacity:.7"></i>'
    else:
        icon = '<i class="bi bi-arrow-down-up ms-1" style="font-size:.7rem;opacity:.25"></i>'

    class_attr = f' class="{css_class}"' if css_class else ""

    return format_html(
        '<th{class_attr}><a href="{url}" class="sortable-th text-decoration-none text-reset"'
        ' data-sort-field="{field}" data-sort-order="{order}"'
        ' style="white-space:nowrap">{label}{icon}</a></th>',
        class_attr=format_html(class_attr),
        url=url,
        field=field_name,
        order=new_order,
        label=label,
        icon=format_html(icon),
    )
