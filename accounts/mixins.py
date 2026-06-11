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


class WorkflowStepperMixin:
    """Build the generic lifecycle stepper context for a detail view.

    Reads the object's workflow definition (states in declaration order, the
    caller's allowed transitions, branch states like cancelled / archived) and
    produces the context consumed by ``includes/workflow_stepper.html``.

    The transition is posted to the shared ``workflow:transition`` URL by
    default; views whose bespoke transition endpoint carries extra side effects
    (required-fields gating, recalculations) set
    ``workflow_transition_url_name`` or override
    :meth:`get_workflow_transition_url`.
    """

    workflow_transition_url_name = None

    def get_workflow_transition_url(self, obj):
        if self.workflow_transition_url_name:
            return reverse(self.workflow_transition_url_name, kwargs={"pk": obj.pk})
        return reverse(
            "workflow:transition",
            kwargs={
                "app_label": obj._meta.app_label,
                "model": obj._meta.model_name,
                "pk": obj.pk,
            },
        )

    def get_context_data(self, **kwargs):
        from core.workflow import allowed_transitions

        ctx = super().get_context_data(**kwargs)
        obj = self.object
        if not hasattr(obj, "get_workflow"):
            return ctx
        workflow = obj.get_workflow()
        current = obj.workflow_state or workflow.initial_state.code
        user = self.request.user

        def has_perm(codename):
            return user.is_superuser or user.has_perm(codename)

        allowed = allowed_transitions(
            workflow, current,
            has_perm=has_perm, perm_namespace=obj.workflow_perm_namespace,
        ) if workflow.has_state(current) else ()

        main_states = [s for s in workflow.states if not s.branch]
        branch_state = next((s for s in workflow.states if s.branch), None)
        main_codes = [s.code for s in main_states]
        current_idx = main_codes.index(current) if current in main_codes else None
        on_branch = branch_state is not None and current == branch_state.code

        # Forward step: the allowed transition to the next main-flow state.
        next_transition = None
        if current_idx is not None and current_idx + 1 < len(main_codes):
            next_code = main_codes[current_idx + 1]
            next_transition = next(
                (t for t in allowed if t.target == next_code and not t.requires_comment),
                None,
            )

        steps = []
        for i, state in enumerate(main_states):
            if current_idx is None:
                step_state = "future"
            elif i < current_idx:
                step_state = "done"
            elif i == current_idx:
                step_state = "current"
            elif next_transition is not None and state.code == next_transition.target:
                step_state = "next"
            else:
                step_state = "future"
            steps.append({"value": state.code, "label": state.label, "state": step_state})

        # Backward move (refusal / rework): first allowed transition going back.
        refusal_transition = None
        if current_idx is not None:
            for t in allowed:
                if t.target in main_codes and main_codes.index(t.target) < current_idx:
                    refusal_transition = t
                    break

        branch_transition = None
        if branch_state is not None:
            branch_transition = next(
                (t for t in allowed if t.target == branch_state.code), None,
            )

        ctx.update({
            "wf_enabled": True,
            "wf_steps": steps,
            "wf_container_id": f"workflow-stepper-{obj.pk}",
            "wf_entity_id": str(obj.pk),
            "wf_transition_url": self.get_workflow_transition_url(obj),
            "wf_next_status": next_transition.target if next_transition else None,
            "wf_cancelled": {
                "value": branch_state.code,
                "label": branch_state.label,
                "state": "current" if on_branch else "future",
            } if branch_state else None,
            "wf_can_cancel": branch_transition is not None,
            "wf_cancel_requires_comment": bool(
                branch_transition and branch_transition.requires_comment
            ),
            "wf_cancel_verb": branch_transition.verb if branch_transition else None,
            "wf_refusal": {
                "status": refusal_transition.target,
                "label": refusal_transition.verb,
            } if refusal_transition else None,
            "wf_can_refuse": refusal_transition is not None,
            "wf_refuse_requires_comment": bool(
                refusal_transition and refusal_transition.requires_comment
            ),
            "wf_start_value": main_codes[0] if main_codes else None,
            "wf_branch_value": main_codes[-1] if main_codes else None,
            "wf_terminal_value": main_codes[-1] if main_codes else None,
        })
        return ctx


class ScopeFilterMixin:
    """Filter queryset by the user's allowed scopes (UI views).

    Works for:
    - Views with ``scope_parent_lookup`` attribute → filter via parent FK path
    - ScopedModel subclasses (have a ``scopes`` M2M) → filter on scopes__id
    - Scope model itself → filter on id
    """

    scope_parent_lookup = None

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
        parent_lookup = getattr(self, "scope_parent_lookup", None)
        if parent_lookup:
            return qs.filter(**{f"{parent_lookup}__id__in": scope_ids}).distinct()
        if any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs
