from collections import defaultdict

from django import template

register = template.Library()


@register.inclusion_tag("widgets/grouped_scope_badges.html")
def grouped_scope_badges(scopes):
    """Render scopes as breadcrumb pills, one per root-to-leaf path.

    Builds a mini-tree from the selected scopes, then extracts every
    root-to-leaf branch as a breadcrumb: ``Org › BU › Site``.

    - Ancestor context (parents *not* in the list) is prepended to give
      the full hierarchy from the top of the tree.
    - When a branch has siblings, the common prefix repeats in each pill
      so every pill is self-contained and unambiguous.
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

    def get_branches(scope, prefix):
        """Return every root-to-leaf path as a list of segment names."""
        path = prefix + [scope.name]
        kids = children_of.get(scope.pk, [])
        if not kids:
            return [path]
        branches = []
        for kid in kids:
            branches.extend(get_branches(kid, path))
        return branches

    crumbs = []
    for root in tree_roots:
        # Prepend ancestors that are NOT in the scope list for context.
        prefix = [a.name for a in root.get_ancestors()]
        for branch in get_branches(root, prefix):
            crumbs.append(branch)

    return {"crumbs": crumbs}
