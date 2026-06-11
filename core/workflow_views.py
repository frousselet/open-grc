"""Generic UI endpoint performing a lifecycle transition on any element."""

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from context.models.base import BaseModel
from core.workflow import (
    PermissionDeniedError,
    WorkflowError,
    validate_transition,
)


class WorkflowTransitionView(LoginRequiredMixin, View):
    """POST ``target_status`` (+ optional ``comment``) to move an element.

    Single endpoint for every lifecycle entity: the permission required is the
    one declared on the matched transition (e.g. ``.update`` to submit,
    ``.approve`` to validate), resolved against the element's permission
    namespace. Redirects back to the validated referer.
    """

    def post(self, request, app_label, model, pk):
        try:
            model_class = apps.get_model(app_label, model)
        except LookupError:
            raise Http404
        if not (isinstance(model_class, type) and issubclass(model_class, BaseModel)):
            raise Http404
        obj = get_object_or_404(model_class, pk=pk)

        # Scope guard (mirrors ScopeFilterMixin for scoped models).
        user = request.user
        if not user.is_superuser:
            allowed_scopes = user.get_allowed_scope_ids()
            if allowed_scopes is not None and hasattr(obj, "scopes"):
                obj_scopes = set(obj.scopes.values_list("id", flat=True))
                if obj_scopes and not (obj_scopes & set(allowed_scopes)):
                    raise Http404

        target = request.POST.get("target_status", "")
        comment = request.POST.get("comment", "").strip() or None
        workflow = obj.get_workflow()
        current = obj.workflow_state or workflow.initial_state.code

        def has_perm(codename):
            return user.is_superuser or user.has_perm(codename)

        try:
            validate_transition(
                workflow, current, target,
                has_perm=has_perm,
                perm_namespace=obj.workflow_perm_namespace,
                comment=comment,
            )
            obj.transition_to(target, user, comment=comment)
        except PermissionDeniedError:
            messages.error(
                request, _("You do not have permission to perform this transition.")
            )
        except WorkflowError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                _("%(label)s moved to \"%(state)s\".") % {
                    "label": str(obj._meta.verbose_name).capitalize(),
                    "state": obj.lifecycle_label,
                },
            )
        return redirect(self._safe_next(request))

    def _safe_next(self, request):
        candidate = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
        if candidate and url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return candidate
        return "/"
