from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from context.models import Scope


class ApprovableAPIMixin:
    """Reset approval on update; add approve/reject actions to ViewSets.

    Respects VersioningConfig: only triggers version bump and approval reset
    when a "major" field has changed. If approval is disabled for the model,
    approval fields are left unchanged.
    """

    def _get_perm_namespace(self):
        """``module.feature`` permission path of the entity (workflow codenames)."""
        module = getattr(self, "permission_module", None)
        if not module and hasattr(self, "queryset") and self.queryset is not None:
            module = self.queryset.model._meta.app_label
        feature = getattr(self, "permission_feature", None)
        if not feature and hasattr(self, "queryset") and self.queryset is not None:
            feature = self.queryset.model._meta.model_name
        return f"{module}.{feature}"

    def _get_approve_codename(self):
        return f"{self._get_perm_namespace()}.approve"

    def _is_major_change(self, serializer):
        """Determine if the update includes at least one major field."""
        from core.models import VersioningConfig

        model_class = serializer.instance.__class__
        if not VersioningConfig.is_approval_enabled(model_class):
            return False
        major_fields = VersioningConfig.get_major_fields(model_class)
        if major_fields is None:
            return True  # All changes are major
        changed = set(serializer.validated_data.keys())
        return bool(changed & major_fields)

    def perform_update(self, serializer):
        if self._is_major_change(serializer):
            current_version = serializer.instance.version or 0
            serializer.save(
                is_approved=False,
                approved_by=None,
                approved_at=None,
                version=current_version + 1,
            )
        else:
            serializer.save()

    def _terminal_state_response(self, obj):
        """A 400 response if the element is in a terminal lifecycle state, else None."""
        try:
            if obj.get_lifecycle_state().is_terminal:
                return Response(
                    {"detail": (
                        f"Element is in the terminal '{obj.workflow_state}' "
                        "lifecycle state."
                    )},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            pass
        return None

    def get_queryset(self):
        """Support filtering any lifecycle entity list by ``?workflow_state=``."""
        qs = super().get_queryset()
        raw = self.request.query_params.get("workflow_state") if self.request else None
        if raw:
            try:
                qs.model._meta.get_field("workflow_state")
            except Exception:
                return qs
            states = [s for s in raw.split(",") if s]
            if states:
                qs = qs.filter(workflow_state__in=states)
        return qs

    @action(detail=True, methods=["get", "post"], url_path="transition")
    def transition(self, request, **kwargs):
        """GET: list the caller's allowed lifecycle transitions. POST: perform one."""
        from core.workflow import (
            PermissionDeniedError,
            WorkflowError,
            allowed_transitions,
            validate_transition,
        )

        obj = self.get_object()
        workflow = obj.get_workflow()
        current = obj.workflow_state or workflow.initial_state.code
        namespace = self._get_perm_namespace()

        def has_perm(codename):
            return request.user.is_superuser or request.user.has_perm(codename)

        if request.method == "GET":
            transitions = allowed_transitions(
                workflow, current, has_perm=has_perm, perm_namespace=namespace,
            )
            return Response({
                "workflow": workflow.name,
                "workflow_state": current,
                "allowed_transitions": [
                    {
                        "target": t.target,
                        "verb": str(t.verb),
                        "action": t.action,
                        "requires_comment": t.requires_comment,
                    }
                    for t in transitions
                ],
            })

        target = request.data.get("target_state")
        comment = request.data.get("comment") or None
        if not target:
            return Response(
                {"detail": "target_state is required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_transition(
                workflow, current, target,
                has_perm=has_perm, perm_namespace=namespace, comment=comment,
            )
        except PermissionDeniedError as e:
            raise PermissionDenied(str(e))
        except WorkflowError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
        obj.transition_to(target, request.user, comment=comment)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, **kwargs):
        """Deprecated alias of the validate transition (kept for compatibility)."""
        obj = self.get_object()
        codename = self._get_approve_codename()
        if not request.user.is_superuser and not request.user.has_perm(codename):
            raise PermissionDenied("Permission d'approbation requise.")
        terminal = self._terminal_state_response(obj)
        if terminal is not None:
            return terminal
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
        terminal = self._terminal_state_response(obj)
        if terminal is not None:
            return terminal
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
    - ViewSets with ``scope_parent_lookup`` attribute → filter via parent FK path
    - Models with a ``scopes`` M2M → filter on scopes__id
    - Scope model itself → filter on id
    """

    scope_parent_lookup = None

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
        parent_lookup = getattr(self, "scope_parent_lookup", None)
        if parent_lookup:
            return qs.filter(**{f"{parent_lookup}__id__in": scope_ids}).distinct()
        if any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs


class BatchCreateMixin:
    """Add a batch/ endpoint to create multiple objects in a single request."""

    batch_max_items = 100

    @action(detail=False, methods=["post"], url_path="batch")
    def batch_create(self, request):
        items = request.data.get("items", [])

        if not isinstance(items, list):
            return Response(
                {"error": "The 'items' field must be a list."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        if len(items) > self.batch_max_items:
            return Response(
                {"error": f"Maximum {self.batch_max_items} items per batch."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        results = []
        created_count = 0
        error_count = 0

        for index, item_data in enumerate(items):
            serializer = self.get_serializer(data=item_data)
            if serializer.is_valid():
                try:
                    instance = serializer.save(
                        **self._get_batch_create_kwargs(request)
                    )
                    results.append({
                        "index": index,
                        "status": "created",
                        "id": str(instance.pk),
                        "reference": getattr(instance, "reference", None),
                    })
                    created_count += 1
                except Exception as e:
                    results.append({
                        "index": index,
                        "status": "error",
                        "errors": {"non_field_errors": [str(e)]},
                    })
                    error_count += 1
            else:
                results.append({
                    "index": index,
                    "status": "error",
                    "errors": serializer.errors,
                })
                error_count += 1

        return Response({
            "status": "completed" if error_count == 0 else "completed_with_errors",
            "total": len(items),
            "created": created_count,
            "errors": error_count,
            "results": results,
        })

    def _get_batch_create_kwargs(self, request):
        """Extra kwargs passed to serializer.save() for each batch item."""
        kwargs = {}
        if hasattr(self, "perform_create"):
            # Check if the viewset sets created_by
            model = self.get_queryset().model
            if hasattr(model, "created_by"):
                kwargs["created_by"] = request.user
        return kwargs
