class SortableListMixin:
    """Mixin for ListView that adds server-side sorting.

    Sort preferences are persisted per user via JS (no URL params).
    Search/filtering is handled client-side via JS.

    Class attributes:
        sortable_fields: dict mapping field names to ORM field paths.
            Example: {"name": "name", "owner": "owner__last_name"}
        default_sort: default sort field (must be a key in sortable_fields).
        default_sort_order: "asc" or "desc".
        sort_view_key: unique key to persist sort preferences per user.
            Defaults to "app_label.model_name" from the view's model.
    """

    sortable_fields = {}
    default_sort = None
    default_sort_order = "asc"
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

        Priority: saved user preference > class defaults.
        """
        saved_sort, saved_order = self._get_saved_preference()
        if saved_sort:
            return saved_sort, saved_order
        return self.default_sort, self.default_sort_order

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self._apply_sorting(qs)
        return qs

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
        ctx["sort_view_key"] = self._get_sort_view_key()
        return ctx
