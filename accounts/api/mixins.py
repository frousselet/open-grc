from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from context.models import Scope


class ApprovableAPIMixin:
    """Reset approval on update; add approve/reject actions to ViewSets."""

    def _get_approve_codename(self):
        module = getattr(self, "permission_module", None)
        if not module and hasattr(self, "queryset") and self.queryset is not None:
            module = self.queryset.model._meta.app_label
        feature = getattr(self, "permission_feature", None)
        if not feature and hasattr(self, "queryset") and self.queryset is not None:
            feature = self.queryset.model._meta.model_name
        return f"{module}.{feature}.approve"

    def perform_update(self, serializer):
        current_version = serializer.instance.version or 0
        serializer.save(
            is_approved=False,
            approved_by=None,
            approved_at=None,
            version=current_version + 1,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, **kwargs):
        obj = self.get_object()
        codename = self._get_approve_codename()
        if not request.user.is_superuser and not request.user.has_perm(codename):
            raise PermissionDenied("Permission d'approbation requise.")
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, **kwargs):
        obj = self.get_object()
        codename = self._get_approve_codename()
        if not request.user.is_superuser and not request.user.has_perm(codename):
            raise PermissionDenied("Permission d'approbation requise.")
        obj.is_approved = False
        obj.approved_by = None
        obj.approved_at = None
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)


class HistoryAPIMixin:
    """Add a /history/ action to any ViewSet whose model has django-simple-history."""

    HISTORY_APPROVAL_FIELDS = {"is_approved", "approved_by", "approved_by_id", "approved_at"}
    HISTORY_HIDDEN_FIELDS = HISTORY_APPROVAL_FIELDS | {"version"}

    @action(detail=True, methods=["get"])
    def history(self, request, **kwargs):
        obj = self.get_object()
        records = obj.history.select_related("history_user").all()[:100]
        data = []
        for record in records:
            entry = {
                "history_id": record.history_id,
                "history_date": record.history_date,
                "history_type": record.history_type,
                "history_user": str(record.history_user) if record.history_user else None,
                "history_change_reason": record.history_change_reason,
                "version": getattr(record, "version", None),
            }
            # Compute diff against previous record
            if record.history_type != "+":
                try:
                    prev = record.prev_record
                    if prev:
                        delta = record.diff_against(prev)
                        approval_changes = []
                        regular_changes = []
                        for c in delta.changes:
                            if c.field in self.HISTORY_HIDDEN_FIELDS:
                                if c.field in self.HISTORY_APPROVAL_FIELDS:
                                    approval_changes.append(c)
                                continue
                            regular_changes.append({
                                "field": c.field,
                                "old": str(c.old) if c.old is not None else None,
                                "new": str(c.new) if c.new is not None else None,
                            })
                        if not regular_changes and approval_changes:
                            entry["is_approval"] = True
                            entry["approved"] = bool(record.is_approved)
                            entry["changes"] = []
                        else:
                            entry["is_approval"] = False
                            entry["changes"] = regular_changes
                except Exception:
                    entry["changes"] = []
            else:
                entry["changes"] = []
            data.append(entry)
        return Response(data)


class ScopeFilterAPIMixin:
    """Filter queryset by the user's allowed scopes (DRF ViewSets).

    Works for:
    - Models with a ``scopes`` M2M → filter on scopes__id
    - Scope model itself → filter on id
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated or user.is_superuser:
            return qs

        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs

        model = qs.model
        if model is Scope or (hasattr(model, "_meta") and model._meta.label == "context.Scope"):
            return qs.filter(id__in=scope_ids)
        if any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs
