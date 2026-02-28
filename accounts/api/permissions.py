from rest_framework.permissions import BasePermission


# Maps DRF actions to custom permission action names
DRF_ACTION_MAP = {
    "list": "read",
    "retrieve": "read",
    "create": "create",
    "update": "update",
    "partial_update": "update",
    "destroy": "delete",
    "approve": "approve",
    "reject": "approve",
}


class ModulePermission(BasePermission):
    """
    Generic RBAC permission class resolving {module}.{feature}.{action}
    from viewset attributes or auto-detect from queryset model.

    ViewSet can declare:
        permission_module = "context"
        permission_feature = "scope"
    Or it auto-detects module from queryset.model._meta.app_label
    and feature from model_name.
    """

    # Override in subclasses or viewsets for custom action mapping
    custom_action_map = {}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        module = self._get_module(view)
        feature = self._get_feature(view)
        action = self._get_action(view, request)

        if not module or not feature or not action:
            return True

        codename = f"{module}.{feature}.{action}"
        return request.user.has_perm(codename)

    def _get_module(self, view):
        if hasattr(view, "permission_module"):
            return view.permission_module
        if hasattr(view, "queryset") and view.queryset is not None:
            return view.queryset.model._meta.app_label
        if hasattr(view, "get_queryset"):
            try:
                return view.get_queryset().model._meta.app_label
            except Exception:
                pass
        return None

    def _get_feature(self, view):
        if hasattr(view, "permission_feature"):
            return view.permission_feature
        if hasattr(view, "queryset") and view.queryset is not None:
            return view.queryset.model._meta.model_name
        if hasattr(view, "get_queryset"):
            try:
                return view.get_queryset().model._meta.model_name
            except Exception:
                pass
        return None

    def _get_action(self, view, request):
        action = getattr(view, "action", None)
        if action:
            # Check custom map first, then viewset-level, then default
            mapped = self.custom_action_map.get(action)
            if mapped:
                return mapped
            viewset_map = getattr(view, "custom_action_map", {})
            if action in viewset_map:
                return viewset_map[action]
            mapped = DRF_ACTION_MAP.get(action)
            if mapped:
                return mapped

        # Fallback based on HTTP method
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return "read"
        return "update"

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        # Check scope-based access for scoped objects
        scope_id = getattr(obj, "scope_id", None)
        if scope_id is not None:
            allowed = request.user.get_allowed_scope_ids()
            if allowed is None:
                return True
            return scope_id in allowed

        # M2M scopes (e.g. Framework.scopes)
        if hasattr(obj, "scopes") and hasattr(obj.scopes, "values_list"):
            allowed = request.user.get_allowed_scope_ids()
            if allowed is None:
                return True
            obj_scope_ids = set(obj.scopes.values_list("id", flat=True))
            return bool(obj_scope_ids & set(allowed))

        return True
