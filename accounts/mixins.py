from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from context.models import Scope


class ApprovableUpdateMixin:
    """Reset approval status and increment version after a domain object is updated."""

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.is_approved = False
        self.object.approved_by = None
        self.object.approved_at = None
        self.object.version = (self.object.version or 0) + 1
        self.object.save()
        form.save_m2m()
        return HttpResponseRedirect(self.get_success_url())


class ApprovalContextMixin:
    """Add approval context (can_approve, approve_url) to detail views."""

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
        ctx = super().get_context_data(**kwargs)
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
