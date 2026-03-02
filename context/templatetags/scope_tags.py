from collections import defaultdict

from django import template

register = template.Library()


@register.inclusion_tag("widgets/grouped_scope_badges.html")
def grouped_scope_badges(scopes):
    """Render scope badges as connected trees, avoiding repeated parent names.

    Builds a mini-tree from the selected scopes:
    - Scopes whose parent is also selected are nested under it.
    - Tree roots show ``full_path`` (for context); descendants show ``name``.
    - Depth drives visual muting (opacity decreases with depth).

    Example: scopes [Iguane Solutions, Hébergement, Héb. données de santé]
    renders as  [Iguane Solutions][Hébergement][Héb. données de santé]
    with progressive fading.
    """
    scope_list = list(scopes)
    scope_ids = {s.pk for s in scope_list}

    children_of = defaultdict(list)
    tree_roots = []

    for s in scope_list:
        if s.parent_scope_id and s.parent_scope_id in scope_ids:
            children_of[s.parent_scope_id].append(s)
        else:
            tree_roots.append(s)

    def flatten_tree(scope, depth=0):
        """Depth-first traversal returning a flat list of badge nodes."""
        display = scope.full_path if depth == 0 else scope.name
        nodes = [{"name": display, "depth": depth}]
        for child in children_of.get(scope.pk, []):
            nodes.extend(flatten_tree(child, depth + 1))
        return nodes

    trees = []
    for root in tree_roots:
        trees.append(flatten_tree(root))

    return {"trees": trees}
