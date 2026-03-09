from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from context.models import Scope


class ApprovableUpdateMixin:
    """Reset approval status and increment version after a domain object is updated.

    Respects VersioningConfig: only triggers version bump and approval reset
    when a "major" field has changed. If approval is disabled for the model,
    the approval fields are left unchanged.
    """

    def _is_major_change(self, form):
        """Determine if the form changes include at least one major field."""
        from core.models import VersioningConfig

        model_class = self.object.__class__
        if not VersioningConfig.is_approval_enabled(model_class):
            return False
        major_fields = VersioningConfig.get_major_fields(model_class)
        if major_fields is None:
            # No config or empty major_fields list → all changes are major
            return True
        changed = set(form.changed_data)
        return bool(changed & major_fields)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self._is_major_change(form):
            self.object.is_approved = False
            self.object.approved_by = None
            self.object.approved_at = None
            self.object.version = (self.object.version or 0) + 1
        self.object.save()
        form.save_m2m()
        return HttpResponseRedirect(self.get_success_url())


class ApprovalContextMixin:
    """Add approval context (can_approve, approve_url, approval_enabled) to detail views."""

    approval_module = None
    approval_feature = None
    approve_url_name = None

    def _get_approval_module(self):
        if self.approval_module:
            return self.approval_module
        return self.model._meta.app_label

    def _get_approval_feature(self):
        if self.approval_feature:
            return self.approval_feature
        return self.model._meta.model_name

    def get_context_data(self, **kwargs):
        from core.models import VersioningConfig

        ctx = super().get_context_data(**kwargs)

        # Check if approval is enabled for this model
        approval_enabled = VersioningConfig.is_approval_enabled(self.model)
        ctx["approval_enabled"] = approval_enabled

        if not approval_enabled:
            ctx["can_approve"] = False
            return ctx

        user = self.request.user
        module = self._get_approval_module()
        feature = self._get_approval_feature()
        codename = f"{module}.{feature}.approve"

        can_approve = False
        if user.is_superuser:
            can_approve = True
        elif user.has_perm(codename):
            # Check scope access via M2M scopes
            obj = self.object
            if hasattr(obj, "scopes") and hasattr(obj.scopes, "values_list"):
                allowed = user.get_allowed_scope_ids()
                if allowed is None:
                    can_approve = True
                else:
                    obj_scope_ids = set(obj.scopes.values_list("id", flat=True))
                    if obj_scope_ids & set(allowed):
                        can_approve = True
            else:
                can_approve = True

        ctx["can_approve"] = can_approve
        if self.approve_url_name:
            ctx["approve_url"] = reverse(self.approve_url_name, kwargs={"pk": self.object.pk})
        return ctx


class ScopeFilterMixin:
    """Filter queryset by the user's allowed scopes (UI views).

    Works for:
    - ScopedModel subclasses (have a ``scopes`` M2M) → filter on scopes__id
    - Scope model itself → filter on id
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser:
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
