from django.db.models import Q


class SortableListMixin:
    """Mixin for ListView that adds server-side sorting and text search.

    Class attributes:
        sortable_fields: dict mapping URL param names to ORM field paths.
            Example: {"name": "name", "owner": "owner__last_name"}
        default_sort: default sort field (must be a key in sortable_fields).
        default_sort_order: "asc" or "desc".
        search_fields: list of ORM field paths to search with ?q= param.
            Example: ["name", "reference", "owner__last_name"]
    """

    sortable_fields = {}
    default_sort = None
    default_sort_order = "asc"
    search_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self._apply_search(qs)
        qs = self._apply_sorting(qs)
        return qs

    def _apply_search(self, qs):
        query = self.request.GET.get("q", "").strip()
        if not query or not self.search_fields:
            return qs
        q_objects = Q()
        for field in self.search_fields:
            q_objects |= Q(**{f"{field}__icontains": query})
        return qs.filter(q_objects)

    def _apply_sorting(self, qs):
        sort_field = self.request.GET.get("sort", self.default_sort)
        order = self.request.GET.get("order", self.default_sort_order)
        if sort_field and sort_field in self.sortable_fields:
            orm_field = self.sortable_fields[sort_field]
            if order == "desc":
                orm_field = f"-{orm_field}"
            qs = qs.order_by(orm_field)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_sort"] = self.request.GET.get("sort", self.default_sort or "")
        ctx["current_order"] = self.request.GET.get("order", self.default_sort_order)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx
