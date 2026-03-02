from django import template

register = template.Library()


@register.inclusion_tag("widgets/grouped_scope_badges.html")
def grouped_scope_badges(scopes):
    """Render scope breadcrumb pills, showing only selection roots.

    Since checking a parent automatically checks all descendants,
    child scopes whose parent is also in the list are redundant.
    Only *selection roots* (scopes whose parent is NOT in the list)
    are displayed, each as a breadcrumb pill with ancestor context.

    Examples (selected scopes → display):
      [Iguane, Hébergement, HDS]  →  (Iguane Solutions)
      [Hébergement, HDS]          →  (Iguane Solutions › Hébergement)
      [HDS]                       →  (Iguane Solutions › Hébergement › HDS)
    """
    scope_list = list(scopes)
    scope_ids = {s.pk for s in scope_list}

    crumbs = []
    for s in scope_list:
        # Skip scopes whose parent is also selected (they are implied).
        if s.parent_scope_id in scope_ids:
            continue
        ancestors = [a.name for a in s.get_ancestors()]
        crumbs.append(ancestors + [s.name])

    return {"crumbs": crumbs}
