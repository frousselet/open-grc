import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, ScopeFilterMixin
from core.mixins import SortableListMixin
from .constants import CollectionMethod, IndicatorType, PREDEFINED_SOURCE_FORMAT
from .forms import (
    ActivityForm,
    IndicatorForm,
    IndicatorMeasurementForm,
    PredefinedIndicatorForm,
    IssueForm,
    ObjectiveForm,
    RoleForm,
    ScopeForm,
    StakeholderForm,
    SwotAnalysisForm,
)
from .models import (
    Activity,
    Indicator,
    IndicatorMeasurement,
    Issue,
    Objective,
    Role,
    Scope,
    Site,
    Stakeholder,
    SwotAnalysis,
    Tag,
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


# ── Dashboard indicator helpers ──────────────────────────────

DASHBOARD_INDICATOR_SLOTS = 10


def _format_number(value):
    """Format a numeric string with locale-aware thousand separators."""
    try:
        num = float(value)
    except (ValueError, TypeError):
        return value
    # Use integer display when there is no fractional part
    if num == int(num):
        return formats.number_format(int(num), use_l10n=True)
    return formats.number_format(num, decimal_pos=1, use_l10n=True)


def get_dashboard_indicator_slots(user):
    """Load pinned indicators with trend + sparkline data, padded to 10 slots."""
    pinned_ids = user.dashboard_indicators or []
    chart_ids = {str(i) for i in (user.dashboard_indicator_charts or [])}

    indicator_map = {}
    if pinned_ids:
        indicators = Indicator.objects.filter(
            id__in=pinned_ids,
        ).prefetch_related("measurements")

        for ind in indicators:
            show_chart = str(ind.pk) in chart_ids
            # Fetch enough measurements for sparklines when chart is enabled
            limit = 20 if show_chart else 2
            measurements = list(ind.measurements.order_by("-recorded_at")[:limit])
            current = measurements[0] if measurements else None
            previous = measurements[1] if len(measurements) > 1 else None

            trend = None
            trend_value = None
            delta_display = ""
            if current and previous and ind.format == "number":
                try:
                    cur_val = float(current.value)
                    prev_val = float(previous.value)
                    diff = cur_val - prev_val
                    trend_value = diff
                    if diff > 0:
                        trend = "up"
                        delta_display = "+" + _format_number(diff)
                    elif diff < 0:
                        trend = "down"
                        delta_display = _format_number(diff)
                    else:
                        trend = "stable"
                except (ValueError, TypeError):
                    pass
            elif current and previous and ind.format == "boolean":
                cur_bool = current.value.lower() in ("true", "1", "yes")
                prev_bool = previous.value.lower() in ("true", "1", "yes")
                if cur_bool != prev_bool:
                    trend = "changed"
                else:
                    trend = "stable"

            # Formatted current value with thousand separators
            formatted_value = None
            if ind.format == "number" and ind.current_value:
                formatted_value = _format_number(ind.current_value)

            # Build sparkline values (chronological, numeric only)
            sparkline_data = []
            if show_chart and ind.format == "number" and len(measurements) >= 2:
                for m in reversed(measurements):
                    try:
                        sparkline_data.append(float(m.value))
                    except (ValueError, TypeError):
                        continue

            indicator_map[str(ind.pk)] = {
                "indicator": ind,
                "current_measurement": current,
                "previous_measurement": previous,
                "trend": trend,
                "trend_value": trend_value,
                "delta_display": delta_display,
                "formatted_value": formatted_value,
                "show_chart": show_chart,
                "sparkline_data": sparkline_data,
            }

    # Build ordered list, padded with None for empty slots
    slots = []
    for pid in pinned_ids:
        if pid in indicator_map:
            slots.append(indicator_map[pid])
    while len(slots) < DASHBOARD_INDICATOR_SLOTS:
        slots.append(None)
    return slots


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
        return qs.filter(scopes__id__in=scope_ids).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Scopes — filtered by access
        scope_ids = user.get_allowed_scope_ids()
        scopes_qs = Scope.objects.all()
        if not user.is_superuser and scope_ids is not None:
            scopes_qs = scopes_qs.filter(id__in=scope_ids)
        if scope_ids is not None:
            ctx["user_scopes"] = Scope.objects.filter(id__in=scope_ids).select_related("parent_scope")

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

        # Dashboard indicators
        ctx["dashboard_indicator_slots"] = get_dashboard_indicator_slots(user)
        ctx["available_indicators"] = Indicator.objects.filter(
            status="active",
        ).order_by("indicator_type", "name")
        ctx["dashboard_indicator_chart_ids"] = user.dashboard_indicator_charts or []

        return ctx


# ── Scope ───────────────────────────────────────────────────

class ScopeListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Scope
    template_name = "context/scope_list.html"
    context_object_name = "scopes"
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "version": "version",
        "status": "status",
        "effective_date": "effective_date",
        "review_date": "review_date",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]
    paginate_by = None  # tree view shows all

    def get_queryset(self):
        qs = super().get_queryset().select_related("parent_scope")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scopes"] = self._build_tree(list(ctx["scopes"]))
        return ctx

    @staticmethod
    def _build_tree(scopes):
        """Return scopes in depth-first tree order, annotated with tree_level/tree_indent.

        Sibling order is preserved from the queryset (i.e. server-side sort
        applies within each parent group, keeping the hierarchy intact).
        """
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


# ── Issue ───────────────────────────────────────────────────

class IssueListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Issue
    template_name = "context/issue_list.html"
    context_object_name = "issues"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "impact": "impact_level",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        type_filter = self.request.GET.get("type")
        if type_filter:
            qs = qs.filter(type=type_filter)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        impact_filter = self.request.GET.get("impact")
        if impact_filter:
            qs = qs.filter(impact_level=impact_filter)
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

class StakeholderListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Stakeholder
    template_name = "context/stakeholder_list.html"
    context_object_name = "stakeholders"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "influence": "influence_level",
        "interest": "interest_level",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        type_filter = self.request.GET.get("type")
        if type_filter:
            qs = qs.filter(type=type_filter)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


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

class ObjectiveListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Objective
    template_name = "context/objective_list.html"
    context_object_name = "objectives"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "category": "category",
        "progress": "progress_percentage",
        "status": "status",
        "target_date": "target_date",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        category_filter = self.request.GET.get("category")
        if category_filter:
            qs = qs.filter(category=category_filter)
        return qs


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

class SwotListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = SwotAnalysis
    template_name = "context/swot_list.html"
    context_object_name = "analyses"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "date": "analysis_date",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


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

class RoleListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Role
    template_name = "context/role_list.html"
    context_object_name = "roles"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            user_count=Count("assigned_users")
        )
        type_filter = self.request.GET.get("type")
        if type_filter:
            qs = qs.filter(type=type_filter)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


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

class ActivityListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Activity
    template_name = "context/activity_list.html"
    context_object_name = "activities"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "criticality": "criticality",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        criticality_filter = self.request.GET.get("criticality")
        if criticality_filter:
            qs = qs.filter(criticality=criticality_filter)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


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


@login_required
@require_POST
def tag_create_inline(request):
    """Create (or retrieve) a tag via AJAX and return its id/name as JSON."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"error": "Name is required"}, status=400)

    tag, _created = Tag.objects.get_or_create(
        name__iexact=name,
        defaults={"name": name},
    )
    return JsonResponse({"id": str(tag.id), "name": tag.name})


class TagListView(LoginRequiredMixin, ListView):
    model = Tag
    template_name = "context/tag_list.html"
    context_object_name = "tags"
    paginate_by = 50

    def get_queryset(self):
        from django.db.models.fields.related import ManyToManyRel

        qs = Tag.objects.all()
        tags = list(qs)
        for tag in tags:
            usage = []
            for field in Tag._meta.get_fields():
                if isinstance(field, ManyToManyRel):
                    accessor = field.get_accessor_name()
                    count = getattr(tag, accessor).count()
                    if count > 0:
                        model_name = field.related_model._meta.verbose_name_plural
                        usage.append((str(model_name), count))
            tag.usage = usage
            tag.usage_total = sum(c for _, c in usage)
        return tags


class TagUpdateView(LoginRequiredMixin, UpdateView):
    model = Tag
    template_name = "context/tag_form.html"
    success_url = reverse_lazy("context:tag-list")

    def get_form_class(self):
        from .forms import TagForm
        return TagForm


class TagDeleteView(LoginRequiredMixin, DeleteView):
    model = Tag
    template_name = "context/confirm_delete.html"
    success_url = reverse_lazy("context:tag-list")


# ── Indicators ─────────────────────────────────────────────

MAX_DASHBOARD_INDICATORS = 10


@login_required
@require_POST
def dashboard_indicator_toggle(request):
    """Toggle an indicator on/off the dashboard (AJAX)."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    indicator_id = data.get("indicator_id", "").strip()
    if not indicator_id:
        return JsonResponse({"error": "indicator_id is required"}, status=400)

    # Verify the indicator exists
    if not Indicator.objects.filter(pk=indicator_id).exists():
        return JsonResponse({"error": "Indicator not found"}, status=404)

    user = request.user
    pinned = list(user.dashboard_indicators or [])

    if indicator_id in pinned:
        pinned.remove(indicator_id)
        action = "removed"
    else:
        if len(pinned) >= MAX_DASHBOARD_INDICATORS:
            return JsonResponse(
                {"error": _("Maximum %d indicators on the dashboard.") % MAX_DASHBOARD_INDICATORS},
                status=400,
            )
        pinned.append(indicator_id)
        action = "added"

    user.dashboard_indicators = pinned
    user.save(update_fields=["dashboard_indicators"])
    return JsonResponse({"action": action, "pinned": pinned})


@login_required
@require_POST
def dashboard_indicator_chart_toggle(request):
    """Toggle sparkline visibility for a single indicator (AJAX)."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    indicator_id = data.get("indicator_id", "").strip()
    if not indicator_id:
        return JsonResponse({"error": "indicator_id is required"}, status=400)

    user = request.user
    chart_ids = list(user.dashboard_indicator_charts or [])

    if indicator_id in chart_ids:
        chart_ids.remove(indicator_id)
        action = "hidden"
    else:
        chart_ids.append(indicator_id)
        action = "shown"

    user.dashboard_indicator_charts = chart_ids
    user.save(update_fields=["dashboard_indicator_charts"])
    return JsonResponse({"action": action, "chart_ids": chart_ids})


class IndicatorListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Indicator
    template_name = "context/indicator_list.html"
    context_object_name = "indicators"
    paginate_by = 25
    indicator_type = None
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "format": "format",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        if self.indicator_type:
            qs = qs.filter(indicator_type=self.indicator_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicator_type"] = self.indicator_type
        return ctx


class IndicatorDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Indicator
    template_name = "context/indicator_detail.html"
    context_object_name = "indicator"
    approve_url_name = "context:indicator-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["measurements"] = self.object.measurements.select_related("recorded_by")[:50]
        ctx["measurement_form"] = IndicatorMeasurementForm(
            indicator_format=self.object.format,
        )
        return ctx


class IndicatorCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Indicator
    form_class = IndicatorForm
    template_name = "context/indicator_form.html"
    indicator_type = None

    def get_success_url(self):
        return reverse_lazy("context:indicator-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicator_type"] = self.indicator_type
        return ctx

    def form_valid(self, form):
        form.instance.indicator_type = self.indicator_type
        return super().form_valid(form)


class PredefinedIndicatorCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Indicator
    form_class = PredefinedIndicatorForm
    template_name = "context/indicator_predefined_form.html"

    def get_success_url(self):
        return reverse_lazy("context:indicator-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.is_internal = True
        form.instance.indicator_type = IndicatorType.ORGANIZATIONAL
        form.instance.collection_method = CollectionMethod.INTERNAL
        # Auto-determine format and unit from source
        source = form.instance.internal_source
        fmt, unit = PREDEFINED_SOURCE_FORMAT.get(source, ("number", ""))
        form.instance.format = fmt
        form.instance.unit = unit
        response = super().form_valid(form)
        # Trigger first measurement on creation
        value = self.object.compute_internal_value()
        if value is not None:
            self.object.record_measurement(
                value=value,
                recorded_by=self.request.user,
                notes=_("Initial measurement (automatic)."),
            )
        return response


class IndicatorUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Indicator
    template_name = "context/indicator_form.html"

    def get_form_class(self):
        if self.object.is_internal:
            return PredefinedIndicatorForm
        return IndicatorForm

    def get_template_names(self):
        if self.object.is_internal:
            return ["context/indicator_predefined_form.html"]
        return ["context/indicator_form.html"]

    def get_success_url(self):
        return reverse_lazy("context:indicator-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicator_type"] = self.object.indicator_type
        return ctx


class IndicatorDeleteView(LoginRequiredMixin, DeleteView):
    model = Indicator
    template_name = "context/confirm_delete.html"

    def get_success_url(self):
        indicator = self.get_object()
        if indicator.indicator_type == IndicatorType.TECHNICAL:
            return reverse_lazy("context:indicator-technical-list")
        return reverse_lazy("context:indicator-organizational-list")


class IndicatorRecordMeasurementView(LoginRequiredMixin, View):
    """Record a measurement for an indicator (manual)."""

    def post(self, request, pk):
        indicator = get_object_or_404(Indicator, pk=pk)
        form = IndicatorMeasurementForm(request.POST, indicator_format=indicator.format)
        if form.is_valid():
            indicator.record_measurement(
                value=form.cleaned_data["value"],
                recorded_by=request.user,
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(request, _("Measurement recorded."))
        else:
            messages.error(request, _("Invalid measurement data."))
        return redirect("context:indicator-detail", pk=pk)


class IndicatorRefreshView(LoginRequiredMixin, View):
    """Trigger a refresh of a predefined indicator's value."""

    def post(self, request, pk):
        indicator = get_object_or_404(Indicator, pk=pk)
        if not indicator.is_internal:
            messages.error(request, _("This indicator is not a predefined indicator."))
            return redirect("context:indicator-detail", pk=pk)
        value = indicator.compute_internal_value()
        if value is not None:
            indicator.record_measurement(
                value=value,
                recorded_by=request.user,
                notes=_("Manual refresh."),
            )
            messages.success(request, _("Indicator refreshed."))
        else:
            messages.warning(request, _("Could not compute the indicator value."))
        return redirect("context:indicator-detail", pk=pk)
