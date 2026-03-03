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
        sort_view_key: unique key to persist sort preferences per user.
            Defaults to "app_label.model_name" from the view's model.
    """

    sortable_fields = {}
    default_sort = None
    default_sort_order = "asc"
    search_fields = []
    sort_view_key = ""

    def _get_sort_view_key(self):
        if self.sort_view_key:
            return self.sort_view_key
        model = getattr(self, "model", None)
        if model:
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return ""

    def _get_saved_preference(self):
        """Return (sort_field, order) from user's saved preferences, or (None, None)."""
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None, None
        prefs = getattr(user, "table_preferences", None)
        if not isinstance(prefs, dict):
            return None, None
        view_key = self._get_sort_view_key()
        pref = prefs.get(view_key)
        if isinstance(pref, dict):
            sort_field = pref.get("sort", "")
            order = pref.get("order", "asc")
            if sort_field and sort_field in self.sortable_fields:
                return sort_field, order
        return None, None

    def _resolve_sort(self):
        """Determine the effective sort field and order.

        Priority: URL params > saved preference > class defaults.
        """
        url_sort = self.request.GET.get("sort")
        url_order = self.request.GET.get("order")

        if url_sort and url_sort in self.sortable_fields:
            return url_sort, url_order or self.default_sort_order

        saved_sort, saved_order = self._get_saved_preference()
        if saved_sort:
            return saved_sort, saved_order

        return self.default_sort, self.default_sort_order

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
        sort_field, order = self._resolve_sort()
        if sort_field and sort_field in self.sortable_fields:
            orm_field = self.sortable_fields[sort_field]
            if order == "desc":
                orm_field = f"-{orm_field}"
            qs = qs.order_by(orm_field)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sort_field, order = self._resolve_sort()
        ctx["current_sort"] = sort_field or ""
        ctx["current_order"] = order or "asc"
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["sort_view_key"] = self._get_sort_view_key()
        return ctx
