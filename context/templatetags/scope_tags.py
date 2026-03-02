from django import template

register = template.Library()


def _selection_roots(scopes):
    """Return breadcrumb segments for selection roots only."""
    scope_list = list(scopes)
    scope_ids = {s.pk for s in scope_list}

    crumbs = []
    for s in scope_list:
        if s.parent_scope_id in scope_ids:
            continue
        ancestors = [a.name for a in s.get_ancestors()]
        crumbs.append(ancestors + [s.name])

    return scope_list, crumbs


@register.inclusion_tag("widgets/grouped_scope_badges.html")
def grouped_scope_badges(scopes):
    """Render scope breadcrumb pills, showing only selection roots.

    Since checking a parent automatically checks all descendants,
    child scopes whose parent is also in the list are redundant.
    Only *selection roots* (scopes whose parent is NOT in the list)
    are displayed, each as a breadcrumb pill with ancestor context.
    """
    _, crumbs = _selection_roots(scopes)
    return {"crumbs": crumbs}


@register.inclusion_tag("widgets/scope_popover.html")
def scope_popover(scopes):
    """Render a compact count badge with a click-to-expand popover.

    Designed for table cells: shows « 3 » as a small pill, and on click
    reveals a floating panel listing the scope breadcrumb pills.
    """
    scope_list, crumbs = _selection_roots(scopes)
    return {"count": len(scope_list), "crumbs": crumbs}
