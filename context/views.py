from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, ScopeFilterMixin
from .forms import (
    ActivityForm,
    IssueForm,
    ObjectiveForm,
    RoleForm,
    ScopeForm,
    SiteForm,
    StakeholderForm,
    SwotAnalysisForm,
)
from .models import (
    Activity,
    Issue,
    Objective,
    Role,
    Scope,
    Site,
    Stakeholder,
    SwotAnalysis,
)


# ── Mixins ──────────────────────────────────────────────────

class CreatedByMixin:
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class HistoryMixin:
    """Add history_records to context for detail views."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history_records"] = self.object.history.select_related("history_user").all()[:50]
        return ctx


class ApproveView(LoginRequiredMixin, View):
    """Generic approve view for context domain models."""

    model = None
    permission_feature = None
    success_url = None

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"context.{feature}.approve"
        if not request.user.is_superuser and not request.user.has_perm(codename):
            messages.error(request, _("You do not have permission to approve this item."))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        messages.success(request, _("Item approved."))
        return redirect(request.META.get("HTTP_REFERER", self.success_url or "/"))


# ── Dashboard ───────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "context/dashboard.html"

    def _filter_scoped(self, qs):
        """Filter a ScopedModel queryset by allowed scopes."""
        user = self.request.user
        if user.is_superuser:
            return qs
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        return qs.filter(scope_id__in=scope_ids)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Scopes — filtered by access
        scopes_qs = Scope.objects.all()
        if not user.is_superuser:
            scope_ids = user.get_allowed_scope_ids()
            if scope_ids is not None:
                scopes_qs = scopes_qs.filter(id__in=scope_ids)

        ctx["scope_count"] = scopes_qs.count()
        ctx["active_scopes"] = scopes_qs.filter(status="active").select_related("parent_scope")

        ctx["issue_count"] = self._filter_scoped(Issue.objects.all()).count()
        ctx["issues_by_impact"] = (
            self._filter_scoped(Issue.objects.all())
            .values("impact_level")
            .annotate(count=Count("id"))
            .order_by("impact_level")
        )
        ctx["stakeholder_count"] = self._filter_scoped(Stakeholder.objects.all()).count()
        ctx["objective_count"] = self._filter_scoped(Objective.objects.all()).count()
        ctx["swot_count"] = self._filter_scoped(SwotAnalysis.objects.all()).count()
        ctx["role_count"] = self._filter_scoped(Role.objects.all()).count()
        ctx["mandatory_roles_without_users"] = self._filter_scoped(
            Role.objects.filter(is_mandatory=True)
        ).annotate(user_count=Count("assigned_users")).filter(user_count=0)
        ctx["activity_count"] = self._filter_scoped(Activity.objects.all()).count()
        ctx["critical_activities_no_owner"] = self._filter_scoped(
            Activity.objects.filter(criticality="critical")
        ).count()
        ctx["site_count"] = Site.objects.count()
        return ctx


# ── Scope ───────────────────────────────────────────────────

class ScopeListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Scope
    template_name = "context/scope_list.html"
    context_object_name = "scopes"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_scope")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scopes"] = self._build_tree(list(ctx["scopes"]))
        return ctx

    @staticmethod
    def _build_tree(scopes):
        """Return scopes in depth-first tree order, annotated with tree_level/tree_indent."""
        by_parent = {}
        for s in scopes:
            by_parent.setdefault(s.parent_scope_id, []).append(s)

        result = []
        visited = set()

        def walk(parent_id, level):
            for s in by_parent.get(parent_id, []):
                s.tree_level = level
                s.tree_indent = level * 24
                result.append(s)
                visited.add(s.pk)
                walk(s.pk, level + 1)

        walk(None, 0)

        # Orphans (parent filtered out by scope access)
        for s in scopes:
            if s.pk not in visited:
                s.tree_level = 0
                s.tree_indent = 0
                result.append(s)

        return result


class ScopeDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Scope
    template_name = "context/scope_detail.html"
    context_object_name = "scope"
    approve_url_name = "context:scope-approve"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_scope")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ancestors"] = self.object.get_ancestors()
        ctx["children"] = self.object.children.exclude(status="archived")
        return ctx


class ScopeCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Scope
    form_class = ScopeForm
    template_name = "context/scope_form.html"
    success_url = reverse_lazy("context:scope-list")


class ScopeUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = Scope
    form_class = ScopeForm
    template_name = "context/scope_form.html"
    success_url = reverse_lazy("context:scope-list")


class ScopeDeleteView(LoginRequiredMixin, DeleteView):
    model = Scope
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:scope-list")


# ── Site ────────────────────────────────────────────────────

class SiteListView(LoginRequiredMixin, ListView):
    model = Site
    template_name = "context/site_list.html"
    context_object_name = "sites"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_site")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sites"] = self._build_tree(list(ctx["sites"]))
        return ctx

    @staticmethod
    def _build_tree(sites):
        """Return sites in depth-first tree order, annotated with tree_level/tree_indent."""
        by_parent = {}
        for s in sites:
            by_parent.setdefault(s.parent_site_id, []).append(s)

        result = []
        visited = set()

        def walk(parent_id, level):
            for s in by_parent.get(parent_id, []):
                s.tree_level = level
                s.tree_indent = level * 24
                result.append(s)
                visited.add(s.pk)
                walk(s.pk, level + 1)

        walk(None, 0)

        for s in sites:
            if s.pk not in visited:
                s.tree_level = 0
                s.tree_indent = 0
                result.append(s)

        return result


class SiteDetailView(LoginRequiredMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Site
    template_name = "context/site_detail.html"
    context_object_name = "site"
    approve_url_name = "context:site-approve"

    def get_queryset(self):
        return super().get_queryset().select_related("parent_site")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ancestors"] = self.object.get_ancestors()
        ctx["children"] = self.object.children.exclude(status="archived")
        return ctx


class SiteCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Site
    form_class = SiteForm
    template_name = "context/site_form.html"
    success_url = reverse_lazy("context:site-list")


class SiteUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = Site
    form_class = SiteForm
    template_name = "context/site_form.html"
    success_url = reverse_lazy("context:site-list")


class SiteDeleteView(LoginRequiredMixin, DeleteView):
    model = Site
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:site-list")


# ── Issue ───────────────────────────────────────────────────

class IssueListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Issue
    template_name = "context/issue_list.html"
    context_object_name = "issues"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope", "scope__parent_scope")
        type_filter = self.request.GET.get("type")
        if type_filter:
            qs = qs.filter(type=type_filter)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class IssueDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Issue
    template_name = "context/issue_detail.html"
    context_object_name = "issue"
    approve_url_name = "context:issue-approve"


class IssueCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Issue
    form_class = IssueForm
    template_name = "context/issue_form.html"
    success_url = reverse_lazy("context:issue-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class IssueUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Issue
    form_class = IssueForm
    template_name = "context/issue_form.html"
    success_url = reverse_lazy("context:issue-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class IssueDeleteView(LoginRequiredMixin, DeleteView):
    model = Issue
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:issue-list")


# ── Stakeholder ─────────────────────────────────────────────

class StakeholderListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Stakeholder
    template_name = "context/stakeholder_list.html"
    context_object_name = "stakeholders"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("scope", "scope__parent_scope")


class StakeholderDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Stakeholder
    template_name = "context/stakeholder_detail.html"
    context_object_name = "stakeholder"
    approve_url_name = "context:stakeholder-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("expectations")


class StakeholderCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Stakeholder
    form_class = StakeholderForm
    template_name = "context/stakeholder_form.html"
    success_url = reverse_lazy("context:stakeholder-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class StakeholderUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Stakeholder
    form_class = StakeholderForm
    template_name = "context/stakeholder_form.html"
    success_url = reverse_lazy("context:stakeholder-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class StakeholderDeleteView(LoginRequiredMixin, DeleteView):
    model = Stakeholder
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:stakeholder-list")


# ── Objective ───────────────────────────────────────────────

class ObjectiveListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Objective
    template_name = "context/objective_list.html"
    context_object_name = "objectives"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("scope", "owner")


class ObjectiveDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Objective
    template_name = "context/objective_detail.html"
    context_object_name = "objective"
    approve_url_name = "context:objective-approve"


class ObjectiveCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Objective
    form_class = ObjectiveForm
    template_name = "context/objective_form.html"
    success_url = reverse_lazy("context:objective-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ObjectiveUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Objective
    form_class = ObjectiveForm
    template_name = "context/objective_form.html"
    success_url = reverse_lazy("context:objective-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ObjectiveDeleteView(LoginRequiredMixin, DeleteView):
    model = Objective
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:objective-list")


# ── SWOT ────────────────────────────────────────────────────

class SwotListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = SwotAnalysis
    template_name = "context/swot_list.html"
    context_object_name = "analyses"
    paginate_by = 25


class SwotDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = SwotAnalysis
    template_name = "context/swot_detail.html"
    context_object_name = "analysis"
    approval_feature = "swot"
    approve_url_name = "context:swot-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items")


class SwotCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = SwotAnalysis
    form_class = SwotAnalysisForm
    template_name = "context/swot_form.html"
    success_url = reverse_lazy("context:swot-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SwotUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = SwotAnalysis
    form_class = SwotAnalysisForm
    template_name = "context/swot_form.html"
    success_url = reverse_lazy("context:swot-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SwotDeleteView(LoginRequiredMixin, DeleteView):
    model = SwotAnalysis
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:swot-list")


# ── Role ────────────────────────────────────────────────────

class RoleListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Role
    template_name = "context/role_list.html"
    context_object_name = "roles"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().annotate(
            user_count=Count("assigned_users")
        )


class RoleDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Role
    template_name = "context/role_detail.html"
    context_object_name = "role"
    approve_url_name = "context:role-approve"

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "responsibilities", "assigned_users"
        )


class RoleCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = "context/role_form.html"
    success_url = reverse_lazy("context:role-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RoleUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = "context/role_form.html"
    success_url = reverse_lazy("context:role-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RoleDeleteView(LoginRequiredMixin, DeleteView):
    model = Role
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:role-list")


# ── Activity ────────────────────────────────────────────────

class ActivityListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Activity
    template_name = "context/activity_list.html"
    context_object_name = "activities"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("scope", "owner")


class ActivityDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Activity
    template_name = "context/activity_detail.html"
    context_object_name = "activity"
    approve_url_name = "context:activity-approve"


class ActivityCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    template_name = "context/activity_form.html"
    success_url = reverse_lazy("context:activity-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActivityUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    template_name = "context/activity_form.html"
    success_url = reverse_lazy("context:activity-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActivityDeleteView(LoginRequiredMixin, DeleteView):
    model = Activity
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:activity-list")
