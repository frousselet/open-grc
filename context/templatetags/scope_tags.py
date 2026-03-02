from collections import OrderedDict

from django import template

register = template.Library()


@register.inclusion_tag("widgets/grouped_scope_badges.html")
def grouped_scope_badges(scopes):
    """Render scope badges grouped by parent to avoid repeating parent names.

    Root scopes → standalone badge.
    Child scopes sharing a parent → [Parent] [child1] [child2] with children muted.
    """
    groups = OrderedDict()
    roots = []  # list of (pk, name) tuples

    for s in scopes:
        if s.parent_scope_id:
            pid = s.parent_scope_id
            if pid not in groups:
                groups[pid] = {
                    "parent_name": s.parent_scope.full_path,
                    "children": [],
                }
            groups[pid]["children"].append(s.name)
        else:
            roots.append((s.pk, s.name))

    # If a root scope is also the parent of a group, don't show it twice.
    standalone = [name for pk, name in roots if pk not in groups]

    return {
        "roots": standalone,
        "groups": list(groups.values()),
    }
