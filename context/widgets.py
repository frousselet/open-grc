from django import forms


class ScopeTreeData:
    """Light value-object used to pass tree nodes to the template."""

    __slots__ = ("id", "name", "full_path", "depth", "indent", "parent_id", "has_children", "selected")

    def __init__(self, pk, name, full_path, depth, parent_id, has_children, selected):
        self.id = str(pk)
        self.name = name
        self.full_path = full_path
        self.depth = depth
        self.indent = 12 + depth * 24  # px
        self.parent_id = str(parent_id) if parent_id else ""
        self.has_children = has_children
        self.selected = selected


class ScopeTreeWidget(forms.CheckboxSelectMultiple):
    """Renders scopes as a hierarchical tree with checkboxes.

    The template ``widgets/scope_tree_widget.html`` receives ``widget.tree_data``
    which is a depth-first ordered list of ``ScopeTreeData`` nodes.
    """

    template_name = "widgets/scope_tree_widget.html"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)
        self.tree_data = []

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["tree_data"] = self.tree_data
        return ctx

    def build_tree_data(self, queryset, selected_ids):
        """Build a depth-first ordered list of ScopeTreeData nodes."""
        scopes = list(queryset.select_related("parent_scope"))
        by_parent = {}
        for s in scopes:
            by_parent.setdefault(s.parent_scope_id, []).append(s)

        ids_with_children = (set(by_parent.keys()) - {None}) & {s.pk for s in scopes}

        selected_set = {str(pk) for pk in (selected_ids or [])}

        result = []
        visited = set()

        def walk(parent_id, depth, path):
            for s in sorted(by_parent.get(parent_id, []), key=lambda x: x.name):
                full_path = path + [s.name]
                result.append(ScopeTreeData(
                    pk=s.pk,
                    name=s.name,
                    full_path=" / ".join(full_path),
                    depth=depth,
                    parent_id=parent_id,
                    has_children=s.pk in ids_with_children,
                    selected=str(s.pk) in selected_set,
                ))
                visited.add(s.pk)
                walk(s.pk, depth + 1, full_path)

        walk(None, 0, [])

        # Orphans (parent filtered out by access control)
        for s in scopes:
            if s.pk not in visited:
                result.append(ScopeTreeData(
                    pk=s.pk, name=s.name, full_path=s.name,
                    depth=0, parent_id=None,
                    has_children=s.pk in ids_with_children,
                    selected=str(s.pk) in selected_set,
                ))

        self.tree_data = result
        return result
