from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, ScopeFilterMixin, WorkflowStepperMixin
from accounts.views import PermissionRequiredMixin
from core.mixins import HtmxFormMixin, SortableListMixin
from .constants import (
    DEFAULT_IMPACT_SCALES,
    DEFAULT_LIKELIHOOD_SCALES,
    DEFAULT_RISK_LEVELS,
    DEFAULT_RISK_MATRIX,
    EbiosIterationType,
    Methodology,
    RiskPriority,
    RiskStatus,
    TreatmentDecision,
)
from .views_ebios import build_ebios_stepper_context
from .forms import (
    ImpactFormSet,
    ISO27005RiskCreateForm,
    ISO27005RiskUpdateForm,
    LikelihoodFormSet,
    RiskAcceptanceCreateForm,
    RiskAcceptanceUpdateForm,
    RiskAssessmentCreateForm,
    RiskAssessmentUpdateForm,
    RiskCriteriaForm,
    RiskCreateForm,
    RiskUpdateForm,
    RiskLevelFormSet,
    RiskTreatmentPlanCreateForm,
    RiskTreatmentPlanUpdateForm,
    ThreatCreateForm,
    ThreatUpdateForm,
    TreatmentActionCreateForm,
    TreatmentActionUpdateForm,
    VulnerabilityCreateForm,
    VulnerabilityUpdateForm,
)
from context.models import Scope
from .models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskTreatmentPlan,
    Threat,
    TreatmentAction,
    Vulnerability,
)


def _text_color_for_bg(hex_color):
    """Return '#fff' for dark backgrounds, '#000' for light ones."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#fff" if luminance < 0.55 else "#000"


def build_risk_matrix(risks_qs, criteria, likelihood_field, impact_field):
    """Build a risk matrix data structure for template rendering.

    Args:
        risks_qs: queryset of Risk objects
        criteria: RiskCriteria instance (with risk_matrix, scale_levels, risk_levels)
        likelihood_field: field name for likelihood on Risk (e.g. "current_likelihood")
        impact_field: field name for impact on Risk (e.g. "current_impact")

    Returns a dict with rows, impact_labels, risk_levels, has_data — or None.
    """
    if not criteria:
        return None

    likelihood_scales = list(
        criteria.scale_levels.filter(scale_type="likelihood").order_by("level")
    )
    impact_scales = list(
        criteria.scale_levels.filter(scale_type="impact").order_by("level")
    )
    if not likelihood_scales or not impact_scales:
        return None

    # Risk level index: int → {name, color}
    risk_level_map = {}
    for rl in criteria.risk_levels.all():
        risk_level_map[rl.level] = {"name": rl.name, "color": rl.color}

    # Count risks per (likelihood, impact) cell
    cell_counts = {}
    for risk in risks_qs:
        l_val = getattr(risk, likelihood_field, None)
        i_val = getattr(risk, impact_field, None)
        if l_val is not None and i_val is not None:
            cell_counts[(l_val, i_val)] = cell_counts.get((l_val, i_val), 0) + 1

    matrix = criteria.risk_matrix or {}

    # Rows: highest likelihood at top
    rows = []
    for ls in reversed(likelihood_scales):
        cells = []
        for im in impact_scales:
            matrix_key = f"{ls.level},{im.level}"
            rl_value = matrix.get(matrix_key)
            if rl_value is not None:
                rl_value = int(rl_value)
            rl_info = risk_level_map.get(rl_value, {})
            color = rl_info.get("color", "#e9ecef")
            count = cell_counts.get((ls.level, im.level), 0)
            cells.append({
                "likelihood": ls.level,
                "impact": im.level,
                "risk_level": rl_value,
                "risk_level_name": rl_info.get("name", ""),
                "color": color,
                "text_color": _text_color_for_bg(color),
                "count": count,
            })
        rows.append({
            "level": ls.level,
            "name": ls.name,
            "cells": cells,
        })

    return {
        "rows": rows,
        "impact_labels": [{"level": im.level, "name": im.name} for im in impact_scales],
        "risk_levels": risk_level_map,
        "has_data": bool(cell_counts),
    }


def build_default_risk_matrix(risks_qs=None, likelihood_field="current_likelihood",
                              impact_field="current_impact"):
    """Default 5x5 matrix (ISO 27005) when no RiskCriteria is configured."""

    likelihood_scales = DEFAULT_LIKELIHOOD_SCALES
    impact_scales = DEFAULT_IMPACT_SCALES
    risk_levels = DEFAULT_RISK_LEVELS
    matrix_map = DEFAULT_RISK_MATRIX

    # Count risks per cell if queryset provided
    cell_counts = {}
    if risks_qs is not None:
        for risk in risks_qs:
            l_val = getattr(risk, likelihood_field, None)
            i_val = getattr(risk, impact_field, None)
            if l_val is not None and i_val is not None:
                cell_counts[(l_val, i_val)] = cell_counts.get((l_val, i_val), 0) + 1

    # Rows: highest likelihood at top
    rows = []
    for l_level, l_name in reversed(likelihood_scales):
        cells = []
        for i_level, _ in impact_scales:
            rl_value = matrix_map.get((l_level, i_level), 1)
            rl_info = risk_levels[rl_value]
            color = rl_info["color"]
            count = cell_counts.get((l_level, i_level), 0)
            cells.append({
                "likelihood": l_level,
                "impact": i_level,
                "risk_level": rl_value,
                "risk_level_name": rl_info["name"],
                "color": color,
                "text_color": _text_color_for_bg(color),
                "count": count,
            })
        rows.append({
            "level": l_level,
            "name": l_name,
            "cells": cells,
        })

    return {
        "rows": rows,
        "impact_labels": [{"level": i, "name": n} for i, n in impact_scales],
        "risk_levels": risk_levels,
        "has_data": bool(cell_counts),
    }


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


class ApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generic approve view for risks domain models."""

    model = None
    permission_feature = None
    success_url = None

    def get_permission_required(self):
        feature = self.permission_feature or (self.model._meta.model_name if self.model else None)
        if feature:
            return f"risks.{feature}.approve"
        return None

    @property
    def permission_required(self):
        return self.get_permission_required()

    def post(self, request, pk):
        from core.models import VersioningConfig

        obj = get_object_or_404(self.model, pk=pk)
        if not VersioningConfig.is_approval_enabled(self.model):
            messages.error(request, _("Approval is disabled for this item type."))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"risks.{feature}.approve"
        if not request.user.is_superuser and not request.user.has_perm(codename):
            messages.error(request, _("You do not have permission to approve this item."))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        messages.success(request, _("Item approved."))
        return redirect(request.META.get("HTTP_REFERER", self.success_url or "/"))


# ── Risk Dashboard ──────────────────────────────────────────


class RiskDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Aggregated overview of the risk module.

    Cards: total risks, risks by status, by priority, treatment decision
    distribution, current and residual heatmaps, top 10 critical risks,
    overdue treatment plans and acceptances expiring within 90 days. All
    counters are filtered by the user's allowed scopes through the
    assessment's `scopes` M2M.
    """

    template_name = "risks/dashboard.html"
    permission_required = "risks.risk.read"

    def _scope_ids(self):
        user = self.request.user
        if user.is_superuser:
            return None
        return user.get_allowed_scope_ids()

    def _scoped_risks(self):
        scope_ids = self._scope_ids()
        qs = Risk.objects.all()
        if scope_ids is not None:
            qs = qs.filter(assessment__scopes__id__in=scope_ids).distinct()
        return qs

    def _scoped_treatment_plans(self):
        scope_ids = self._scope_ids()
        qs = RiskTreatmentPlan.objects.all()
        if scope_ids is not None:
            qs = qs.filter(risk__assessment__scopes__id__in=scope_ids).distinct()
        return qs

    def _scoped_acceptances(self):
        scope_ids = self._scope_ids()
        qs = RiskAcceptance.objects.all()
        if scope_ids is not None:
            qs = qs.filter(risk__assessment__scopes__id__in=scope_ids).distinct()
        return qs

    def get_context_data(self, **kwargs):
        from datetime import timedelta as _td

        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        risks_qs = self._scoped_risks()
        ctx["risk_count_total"] = risks_qs.count()

        # Aggregations
        status_counts = dict(
            risks_qs.values_list("status").annotate(n=Count("pk"))
        )
        ctx["risk_status_breakdown"] = [
            {"key": key, "label": str(label), "count": status_counts.get(key, 0)}
            for key, label in RiskStatus.choices
        ]

        priority_counts = dict(
            risks_qs.values_list("priority").annotate(n=Count("pk"))
        )
        ctx["risk_priority_breakdown"] = [
            {"key": key, "label": str(label), "count": priority_counts.get(key, 0)}
            for key, label in RiskPriority.choices
        ]

        decision_counts = dict(
            risks_qs.values_list("treatment_decision").annotate(n=Count("pk"))
        )
        ctx["treatment_decision_breakdown"] = [
            {
                "key": key,
                "label": str(label),
                "count": decision_counts.get(key, 0),
            }
            for key, label in TreatmentDecision.choices
        ]

        # Current-level distribution for an at-a-glance bar
        current_level_counts = dict(
            risks_qs.exclude(current_risk_level__isnull=True)
            .values_list("current_risk_level")
            .annotate(n=Count("pk"))
        )
        ctx["current_level_counts"] = [
            {"level": lvl, "count": current_level_counts.get(lvl, 0)}
            for lvl in sorted(current_level_counts.keys())
        ]

        # Top 10 critical risks (highest current_risk_level then priority)
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        ranked = sorted(
            risks_qs.select_related("assessment", "risk_owner"),
            key=lambda r: (
                -(r.current_risk_level or 0),
                -priority_order.get(r.priority, 0),
                r.reference or "",
            ),
        )
        ctx["top_critical_risks"] = [
            r for r in ranked
            if (r.current_risk_level is not None or r.priority in ("critical", "high"))
        ][:10]

        # Heatmaps reusing the same helpers as the global dashboard
        criteria = (
            RiskCriteria.objects.filter(is_default=True).first()
            or RiskCriteria.objects.filter(workflow_state="validated").first()
        )
        if criteria:
            ctx["matrix_criteria"] = criteria
            ctx["matrix_current"] = build_risk_matrix(
                risks_qs, criteria, "current_likelihood", "current_impact",
            )
            ctx["matrix_residual"] = build_risk_matrix(
                risks_qs, criteria, "residual_likelihood", "residual_impact",
            )
        if not ctx.get("matrix_current"):
            ctx["matrix_current"] = build_default_risk_matrix(
                risks_qs, "current_likelihood", "current_impact",
            )
        if not ctx.get("matrix_residual"):
            ctx["matrix_residual"] = build_default_risk_matrix(
                risks_qs, "residual_likelihood", "residual_impact",
            )
        ctx["current_risks_title"] = _("Current risks")
        ctx["residual_risks_title"] = _("Residual risks")

        # Overdue treatment plans
        plans_qs = self._scoped_treatment_plans()
        ctx["treatment_plan_total"] = plans_qs.count()
        terminal = {"completed", "cancelled"}
        overdue_plans = (
            plans_qs.exclude(status__in=terminal)
            .filter(
                Q(status="overdue")
                | Q(target_date__isnull=False, target_date__lt=today)
            )
            .select_related("risk", "owner")
            .order_by("target_date")
        )
        ctx["overdue_treatment_plans"] = list(overdue_plans[:10])
        ctx["overdue_treatment_plan_count"] = overdue_plans.count()

        # Acceptances expiring within 90 days
        acceptances_qs = self._scoped_acceptances()
        ctx["acceptance_total"] = acceptances_qs.filter(status="active").count()
        expiring = (
            acceptances_qs.filter(
                status="active",
                valid_until__isnull=False,
                valid_until__gte=today,
                valid_until__lte=today + _td(days=90),
            )
            .select_related("risk", "accepted_by")
            .order_by("valid_until")
        )
        ctx["expiring_acceptances"] = list(expiring[:10])
        ctx["expiring_acceptance_count"] = expiring.count()

        return ctx


# ── Risk Assessment ─────────────────────────────────────────

class RiskAssessmentListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = RiskAssessment
    template_name = "risks/assessment_list.html"
    context_object_name = "assessments"
    permission_required = "risks.assessment.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "methodology": "methodology",
        "date": "assessment_date",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("assessor", "risk_criteria")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RiskAssessmentDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = RiskAssessment
    template_name = "risks/assessment_detail.html"
    context_object_name = "assessment"
    permission_required = "risks.assessment.read"
    approval_module = "risks"
    approval_feature = "assessment"
    approve_url_name = "risks:assessment-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assessment_risks = self.object.risks.all()
        ctx["risks"] = assessment_risks[:20]
        ctx["iso27005_risks"] = self.object.iso27005_risks.select_related(
            "threat", "vulnerability", "risk"
        ).all()[:50]

        # Catalog counts for methodology workflow steps
        ctx["threat_count"] = Threat.objects.count()
        ctx["vulnerability_count"] = Vulnerability.objects.count()

        # EBIOS RM workshop progress (only meaningful for ebios_rm assessments)
        if self.object.methodology == Methodology.EBIOS_RM:
            ctx.update(build_ebios_stepper_context(self.object))

        # Risk matrices for this assessment
        criteria = self.object.risk_criteria
        if criteria:
            ctx["matrix_criteria"] = criteria
            ctx["matrix_current"] = build_risk_matrix(
                assessment_risks, criteria, "current_likelihood", "current_impact"
            )
            ctx["matrix_residual"] = build_risk_matrix(
                assessment_risks, criteria, "residual_likelihood", "residual_impact"
            )
        return ctx


class RiskAssessmentCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = RiskAssessment
    form_class = RiskAssessmentCreateForm
    template_name = "risks/assessment_form.html"
    modal_template_name = "risks/assessment_form_modal.html"
    permission_required = "risks.assessment.create"
    modal_title_create = _l("New risk assessment")
    modal_title_update = _l("Edit risk assessment")
    success_url = reverse_lazy("risks:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RiskAssessmentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = RiskAssessment
    form_class = RiskAssessmentUpdateForm
    template_name = "risks/assessment_form.html"
    modal_template_name = "risks/assessment_form_modal.html"
    permission_required = "risks.assessment.update"
    modal_title_create = _l("New risk assessment")
    modal_title_update = _l("Edit risk assessment")
    success_url = reverse_lazy("risks:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RiskAssessmentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = RiskAssessment
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.assessment.delete"
    success_url = reverse_lazy("risks:assessment-list")


class ISO27005ReportExportView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, View):
    """Generate and return an ISO 27005 risk assessment DOCX report.

    The export is filtered by the user's allowed scopes via the assessment's
    `scopes` M2M; the generated file is persisted as a `Report` for
    discoverability through the reports list.
    """

    scope_parent_lookup = "scopes"
    permission_required = "risks.export.read"

    def get_queryset(self):
        return RiskAssessment.objects.all()

    def get(self, request, pk, *args, **kwargs):
        assessment = get_object_or_404(self.get_queryset(), pk=pk)
        # Re-apply scope filter using the same mixin contract.
        user = request.user
        if not user.is_superuser:
            scope_ids = user.get_allowed_scope_ids()
            if scope_ids is not None:
                if not assessment.scopes.filter(id__in=scope_ids).exists():
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden(
                        _("Assessment is outside your allowed scopes.")
                    )

        from reports.constants import ReportStatus, ReportType
        from reports.iso27005_report import generate_iso27005_report_docx
        from reports.models import Report

        try:
            filename, content = generate_iso27005_report_docx(assessment, user)
        except Exception:
            Report.objects.create(
                report_type=ReportType.ISO27005_REPORT,
                name=f"ISO 27005 report - {assessment.reference}",
                status=ReportStatus.FAILED,
                created_by=user,
            )
            raise

        Report.objects.create(
            report_type=ReportType.ISO27005_REPORT,
            name=f"ISO 27005 report - {assessment.reference} - "
                 f"{timezone.now().strftime('%Y-%m-%d %H:%M')}",
            status=ReportStatus.COMPLETED,
            created_by=user,
            file_content=content,
            file_name=filename,
        )

        response = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ── Risk Criteria ───────────────────────────────────────────

class RiskCriteriaListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = RiskCriteria
    template_name = "risks/criteria_list.html"
    context_object_name = "criteria_list"
    permission_required = "risks.criteria.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(workflow_state=status_filter)
        return qs


class RiskCriteriaDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HistoryMixin, DetailView):
    model = RiskCriteria
    template_name = "risks/criteria_detail.html"
    context_object_name = "criteria"
    permission_required = "risks.criteria.read"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scale_levels"] = self.object.scale_levels.all()
        ctx["risk_levels"] = self.object.risk_levels.all()
        return ctx


class CriteriaFormsetMixin:
    """Shared formset handling for RiskCriteria create / update views."""

    def _build_formsets(self, instance=None, data=None):
        kwargs_l = {"instance": instance, "prefix": "likelihood"}
        kwargs_i = {"instance": instance, "prefix": "impact"}
        kwargs_r = {"instance": instance, "prefix": "risklevel"}
        if instance and instance.pk:
            kwargs_l["queryset"] = instance.scale_levels.filter(
                scale_type="likelihood"
            ).order_by("level")
            kwargs_i["queryset"] = instance.scale_levels.filter(
                scale_type="impact"
            ).order_by("level")
        if data is not None:
            kwargs_l["data"] = data
            kwargs_i["data"] = data
            kwargs_r["data"] = data
        return (
            LikelihoodFormSet(**kwargs_l),
            ImpactFormSet(**kwargs_i),
            RiskLevelFormSet(**kwargs_r),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "likelihood_fs" not in ctx:
            lfs, ifs, rfs = self._build_formsets(
                instance=getattr(self, "object", None)
            )
            ctx["likelihood_fs"] = lfs
            ctx["impact_fs"] = ifs
            ctx["risklevel_fs"] = rfs
        return ctx

    def _save_formsets(self, instance, likelihood_fs, impact_fs, risklevel_fs):
        for obj in likelihood_fs.save(commit=False):
            obj.scale_type = "likelihood"
            obj.save()
        for obj in likelihood_fs.deleted_objects:
            obj.delete()
        for obj in impact_fs.save(commit=False):
            obj.scale_type = "impact"
            obj.save()
        for obj in impact_fs.deleted_objects:
            obj.delete()
        risklevel_fs.save()
        # Recompute the risk matrix from the updated scales
        instance.rebuild_risk_matrix()


class RiskCriteriaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreatedByMixin, CriteriaFormsetMixin, CreateView):
    model = RiskCriteria
    form_class = RiskCriteriaForm
    template_name = "risks/criteria_form.html"
    permission_required = "risks.criteria.create"
    success_url = reverse_lazy("risks:criteria-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        lfs, ifs, rfs = self._build_formsets(data=request.POST)
        if form.is_valid() and lfs.is_valid() and ifs.is_valid() and rfs.is_valid():
            self.object = form.save()
            lfs.instance = self.object
            ifs.instance = self.object
            rfs.instance = self.object
            self._save_formsets(self.object, lfs, ifs, rfs)
            return redirect(self.success_url)
        ctx = self.get_context_data(
            form=form, likelihood_fs=lfs, impact_fs=ifs, risklevel_fs=rfs,
        )
        return self.render_to_response(ctx)


class RiskCriteriaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, CriteriaFormsetMixin, ScopeFilterMixin, UpdateView):
    model = RiskCriteria
    form_class = RiskCriteriaForm
    template_name = "risks/criteria_form.html"
    permission_required = "risks.criteria.update"
    success_url = reverse_lazy("risks:criteria-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        lfs, ifs, rfs = self._build_formsets(
            instance=self.object, data=request.POST,
        )
        if form.is_valid() and lfs.is_valid() and ifs.is_valid() and rfs.is_valid():
            self.object = form.save()
            self._save_formsets(self.object, lfs, ifs, rfs)
            return redirect(self.success_url)
        ctx = self.get_context_data(
            form=form, likelihood_fs=lfs, impact_fs=ifs, risklevel_fs=rfs,
        )
        return self.render_to_response(ctx)


class RiskCriteriaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = RiskCriteria
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.criteria.delete"
    success_url = reverse_lazy("risks:criteria-list")


# ── Risk ────────────────────────────────────────────────────

class RiskListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    scope_parent_lookup = "assessment__scopes"
    model = Risk
    template_name = "risks/risk_list.html"
    context_object_name = "risks"
    permission_required = "risks.risk.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "priority": "priority",
        "current_level": "current_risk_level",
        "treatment": "treatment_decision",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("assessment", "risk_owner")
        params = self.request.GET

        assessment_id = params.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        status_filter = params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        priority = params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)
        decision = params.get("treatment_decision")
        if decision:
            qs = qs.filter(treatment_decision=decision)

        date_after = params.get("date_after")
        if date_after:
            qs = qs.filter(created_at__date__gte=date_after)
        date_before = params.get("date_before")
        if date_before:
            qs = qs.filter(created_at__date__lte=date_before)

        m2m_filters = {
            "essential_asset": "affected_essential_assets__id",
            "support_asset": "affected_support_assets__id",
            "threat": "iso27005_sources__threat_id",
            "vulnerability": "iso27005_sources__vulnerability_id",
            "linked_requirement": "linked_requirements__id",
        }
        for param, lookup in m2m_filters.items():
            value = params.get(param)
            if value:
                qs = qs.filter(**{lookup: value})

        # M2M joins can produce duplicate rows; deduplicate.
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET

        # Choices for the advanced filter dropdowns. Limited to entities
        # actually referenced by the user's accessible risks to keep the
        # selects manageable.
        from assets.models import EssentialAsset, SupportAsset
        from compliance.models import Requirement
        from risks.models import Threat, Vulnerability

        base_qs = super().get_queryset()
        risk_ids = list(base_qs.values_list("pk", flat=True))

        if risk_ids:
            ctx["essential_asset_choices"] = (
                EssentialAsset.objects.filter(risks__in=risk_ids)
                .distinct()
                .order_by("name")
            )
            ctx["support_asset_choices"] = (
                SupportAsset.objects.filter(risks__in=risk_ids)
                .distinct()
                .order_by("name")
            )
            ctx["threat_choices"] = (
                Threat.objects.filter(iso27005_risks__risk_id__in=risk_ids)
                .distinct()
                .order_by("name")
            )
            ctx["vulnerability_choices"] = (
                Vulnerability.objects.filter(iso27005_risks__risk_id__in=risk_ids)
                .distinct()
                .order_by("name")
            )
            ctx["requirement_choices"] = (
                Requirement.objects.filter(linked_risks__in=risk_ids)
                .select_related("framework")
                .distinct()
                .order_by("requirement_number", "reference")
            )
        else:
            ctx["essential_asset_choices"] = []
            ctx["support_asset_choices"] = []
            ctx["threat_choices"] = []
            ctx["vulnerability_choices"] = []
            ctx["requirement_choices"] = []

        ctx["treatment_decision_choices"] = TreatmentDecision.choices
        ctx["has_advanced_filter"] = any(
            params.get(key)
            for key in (
                "treatment_decision", "date_after", "date_before",
                "essential_asset", "support_asset", "threat",
                "vulnerability", "linked_requirement",
            )
        )
        return ctx


class RiskBulkActionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Run a bulk action (approve or delete) on a list of risk UUIDs.

    Only operates on risks the user can see (scope-filtered). The action
    must be one of: approve, delete. The destination URL after the action
    is the risk list; selected_ids are read from the form's
    `risk_ids` field (multiple).
    """

    permission_required = "risks.risk.read"
    SUPPORTED_ACTIONS = {"approve", "delete"}

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")
        ids = request.POST.getlist("risk_ids")
        if action not in self.SUPPORTED_ACTIONS:
            messages.error(request, _("Unsupported bulk action."))
            return redirect("risks:risk-list")
        if not ids:
            messages.warning(request, _("No risks selected."))
            return redirect("risks:risk-list")

        qs = Risk.objects.filter(pk__in=ids)
        user = request.user
        if not user.is_superuser:
            scope_ids = user.get_allowed_scope_ids()
            if scope_ids is not None:
                qs = qs.filter(assessment__scopes__id__in=scope_ids).distinct()

        if action == "approve":
            if not user.is_superuser and not user.has_perm("risks.risk.approve"):
                messages.error(request, _("You do not have permission to approve risks."))
                return redirect("risks:risk-list")
            count = 0
            for risk in qs:
                if risk.is_approved:
                    continue
                risk.is_approved = True
                risk.approved_by = user
                risk.approved_at = timezone.now()
                risk.save(update_fields=["is_approved", "approved_by", "approved_at"])
                count += 1
            messages.success(
                request,
                _("%(count)d risk(s) approved.") % {"count": count},
            )
            return redirect("risks:risk-list")

        # action == "delete"
        if not user.is_superuser and not user.has_perm("risks.risk.delete"):
            messages.error(request, _("You do not have permission to delete risks."))
            return redirect("risks:risk-list")
        count, _details = qs.delete()
        messages.success(
            request,
            _("%(count)d risk(s) deleted.") % {"count": count},
        )
        return redirect("risks:risk-list")


class RiskDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    scope_parent_lookup = "assessment__scopes"
    model = Risk
    template_name = "risks/risk_detail.html"
    context_object_name = "risk"
    permission_required = "risks.risk.read"
    approval_module = "risks"
    approval_feature = "risk"
    approve_url_name = "risks:risk-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["treatment_plans"] = self.object.treatment_plans.all()
        ctx["acceptances"] = self.object.acceptances.all()
        ctx["iso27005_sources"] = self.object.iso27005_sources.select_related("threat", "vulnerability").all()
        return ctx


class RiskCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Risk
    form_class = RiskCreateForm
    template_name = "risks/risk_form.html"
    modal_template_name = "risks/risk_form_modal.html"
    permission_required = "risks.risk.create"
    modal_title_create = _l("New risk")
    modal_title_update = _l("Edit risk")
    success_url = reverse_lazy("risks:risk-list")

    def dispatch(self, request, *args, **kwargs):
        # Redirect to assessment list if no assessment context is provided
        if not request.GET.get("assessment"):
            messages.info(
                request,
                _("Please select an assessment and use its methodology workflow to create risks."),
            )
            return redirect("risks:assessment-list")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            initial["assessment"] = assessment_id
        return initial


class RiskUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    scope_parent_lookup = "assessment__scopes"
    model = Risk
    form_class = RiskUpdateForm
    template_name = "risks/risk_form.html"
    modal_template_name = "risks/risk_form_modal.html"
    permission_required = "risks.risk.update"
    modal_title_create = _l("New risk")
    modal_title_update = _l("Edit risk")
    success_url = reverse_lazy("risks:risk-list")


class RiskDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, DeleteView):
    scope_parent_lookup = "assessment__scopes"
    model = Risk
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.risk.delete"
    success_url = reverse_lazy("risks:risk-list")


class RiskRegisterExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate and return an Excel export of the risk register.

    Applies the same scope filtering as RiskListView; honours the same
    optional `assessment`, `status` and `priority` query parameters so that
    the export matches what the user sees in the UI. The generated file is
    also persisted as a `Report` for traceability.
    """

    permission_required = "risks.export.read"

    def get(self, request, *args, **kwargs):
        qs = Risk.objects.all()
        user = request.user
        if not user.is_superuser:
            scope_ids = user.get_allowed_scope_ids()
            if scope_ids is not None:
                qs = qs.filter(assessment__scopes__id__in=scope_ids).distinct()

        assessment_id = request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        status_filter = request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        priority = request.GET.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        from reports.constants import ReportStatus, ReportType
        from reports.generators import generate_risk_register_xlsx
        from reports.models import Report

        try:
            filename, content = generate_risk_register_xlsx(qs, user)
        except Exception:
            Report.objects.create(
                report_type=ReportType.RISK_REGISTER,
                name="Risk register",
                status=ReportStatus.FAILED,
                created_by=user,
            )
            raise

        Report.objects.create(
            report_type=ReportType.RISK_REGISTER,
            name=f"Risk register - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            status=ReportStatus.COMPLETED,
            created_by=user,
            file_content=content,
            file_name=filename,
        )

        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ── Treatment Plan ──────────────────────────────────────────

class TreatmentPlanListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskTreatmentPlan
    template_name = "risks/treatment_plan_list.html"
    context_object_name = "plans"
    permission_required = "risks.treatment.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "treatment_type",
        "target_date": "target_date",
        "progress": "progress_percentage",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "risk__reference"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("risk", "owner")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(risk__assessment_id=assessment_id)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class TreatmentPlanDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskTreatmentPlan
    template_name = "risks/treatment_plan_detail.html"
    context_object_name = "plan"
    permission_required = "risks.treatment.read"
    approval_module = "risks"
    approval_feature = "treatment"
    approve_url_name = "risks:treatment-plan-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["actions"] = self.object.actions.select_related("owner").all()
        ctx["related_action_plans"] = self.object.related_action_plans.select_related(
            "owner"
        ).all()
        return ctx


class TreatmentPlanCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = RiskTreatmentPlan
    form_class = RiskTreatmentPlanCreateForm
    template_name = "risks/treatment_plan_form.html"
    modal_template_name = "risks/treatment_plan_form_modal.html"
    permission_required = "risks.treatment.create"
    modal_title_create = _l("New treatment plan")
    modal_title_update = _l("Edit treatment plan")
    success_url = reverse_lazy("risks:treatment-plan-list")


class TreatmentPlanUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskTreatmentPlan
    form_class = RiskTreatmentPlanUpdateForm
    template_name = "risks/treatment_plan_form.html"
    modal_template_name = "risks/treatment_plan_form_modal.html"
    permission_required = "risks.treatment.update"
    modal_title_create = _l("New treatment plan")
    modal_title_update = _l("Edit treatment plan")
    success_url = reverse_lazy("risks:treatment-plan-list")


class TreatmentPlanDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, DeleteView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskTreatmentPlan
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.treatment.delete"
    success_url = reverse_lazy("risks:treatment-plan-list")


# ── Treatment Action (inline editing under a plan) ──────────


class TreatmentActionCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = TreatmentAction
    form_class = TreatmentActionCreateForm
    template_name = "risks/treatment_action_form.html"
    modal_template_name = "risks/treatment_action_form_modal.html"
    permission_required = "risks.treatment.update"
    modal_title_create = _l("New treatment action")
    modal_title_update = _l("Edit treatment action")

    def get_initial(self):
        initial = super().get_initial()
        plan_id = self.kwargs.get("plan_pk") or self.request.GET.get("treatment_plan")
        if plan_id:
            initial["treatment_plan"] = plan_id
        return initial

    def get_success_url(self):
        if self.object and self.object.treatment_plan_id:
            return reverse_lazy(
                "risks:treatment-plan-detail",
                kwargs={"pk": self.object.treatment_plan_id},
            )
        return reverse_lazy("risks:treatment-plan-list")


class TreatmentActionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UpdateView):
    model = TreatmentAction
    form_class = TreatmentActionUpdateForm
    template_name = "risks/treatment_action_form.html"
    modal_template_name = "risks/treatment_action_form_modal.html"
    permission_required = "risks.treatment.update"
    modal_title_create = _l("New treatment action")
    modal_title_update = _l("Edit treatment action")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        return qs.filter(
            treatment_plan__risk__assessment__scopes__id__in=scope_ids,
        ).distinct()

    def get_success_url(self):
        if self.object and self.object.treatment_plan_id:
            return reverse_lazy(
                "risks:treatment-plan-detail",
                kwargs={"pk": self.object.treatment_plan_id},
            )
        return reverse_lazy("risks:treatment-plan-list")


class TreatmentActionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = TreatmentAction
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.treatment.update"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        return qs.filter(
            treatment_plan__risk__assessment__scopes__id__in=scope_ids,
        ).distinct()

    def get_success_url(self):
        plan_id = self.object.treatment_plan_id if self.object else None
        if plan_id:
            return reverse_lazy(
                "risks:treatment-plan-detail", kwargs={"pk": plan_id},
            )
        return reverse_lazy("risks:treatment-plan-list")


# ── Risk Acceptance ─────────────────────────────────────────

class RiskAcceptanceListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskAcceptance
    template_name = "risks/acceptance_list.html"
    context_object_name = "acceptances"
    permission_required = "risks.acceptance.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "risk": "risk__reference",
        "valid_until": "valid_until",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "risk__reference", "risk__name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("risk", "accepted_by")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(risk__assessment_id=assessment_id)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RiskAcceptanceDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskAcceptance
    template_name = "risks/acceptance_detail.html"
    context_object_name = "acceptance"
    permission_required = "risks.acceptance.read"
    approval_module = "risks"
    approval_feature = "acceptance"
    approve_url_name = "risks:acceptance-approve"


class RiskAcceptanceCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = RiskAcceptance
    form_class = RiskAcceptanceCreateForm
    template_name = "risks/acceptance_form.html"
    modal_template_name = "risks/acceptance_form_modal.html"
    permission_required = "risks.acceptance.create"
    modal_title_create = _l("New risk acceptance")
    modal_title_update = _l("Edit risk acceptance")
    success_url = reverse_lazy("risks:acceptance-list")


class RiskAcceptanceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskAcceptance
    form_class = RiskAcceptanceUpdateForm
    template_name = "risks/acceptance_form.html"
    modal_template_name = "risks/acceptance_form_modal.html"
    permission_required = "risks.acceptance.update"
    modal_title_create = _l("New risk acceptance")
    modal_title_update = _l("Edit risk acceptance")
    success_url = reverse_lazy("risks:acceptance-list")


class RiskAcceptanceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, DeleteView):
    scope_parent_lookup = "risk__assessment__scopes"
    model = RiskAcceptance
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.acceptance.delete"
    success_url = reverse_lazy("risks:acceptance-list")


# ── Threat ──────────────────────────────────────────────────

class ThreatListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Threat
    template_name = "risks/threat_list.html"
    context_object_name = "threats"
    permission_required = "risks.threat.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "origin": "origin",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        threat_type = self.request.GET.get("type")
        if threat_type:
            qs = qs.filter(type=threat_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # When opened via "Manage" from a risk assessment workflow, keep a
        # back link so the user does not lose the assessment context.
        assessment_id = self.request.GET.get("assessment")
        ctx["parent_assessment"] = None
        if assessment_id:
            ctx["parent_assessment"] = RiskAssessment.objects.filter(pk=assessment_id).first()
        return ctx


class ThreatDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = Threat
    template_name = "risks/threat_detail.html"
    context_object_name = "threat"
    permission_required = "risks.threat.read"
    approval_module = "risks"
    approval_feature = "threat"
    approve_url_name = "risks:threat-approve"


class ThreatCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Threat
    form_class = ThreatCreateForm
    template_name = "risks/threat_form.html"
    modal_template_name = "risks/threat_form_modal.html"
    permission_required = "risks.threat.create"
    modal_title_create = _l("New threat")
    modal_title_update = _l("Edit threat")
    success_url = reverse_lazy("risks:threat-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ThreatUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ScopeFilterMixin, ApprovableUpdateMixin, UpdateView):
    model = Threat
    form_class = ThreatUpdateForm
    template_name = "risks/threat_form.html"
    modal_template_name = "risks/threat_form_modal.html"
    permission_required = "risks.threat.update"
    modal_title_create = _l("New threat")
    modal_title_update = _l("Edit threat")
    success_url = reverse_lazy("risks:threat-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ThreatDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Threat
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.threat.delete"
    success_url = reverse_lazy("risks:threat-list")


# ── Vulnerability ───────────────────────────────────────────

class VulnerabilityListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Vulnerability
    template_name = "risks/vulnerability_list.html"
    context_object_name = "vulnerabilities"
    permission_required = "risks.vulnerability.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "category": "category",
        "severity": "severity",
        "workflow_state": "workflow_state",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes")
        category = self.request.GET.get("category")
        if category:
            qs = qs.filter(category=category)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assessment_id = self.request.GET.get("assessment")
        ctx["parent_assessment"] = None
        if assessment_id:
            ctx["parent_assessment"] = RiskAssessment.objects.filter(pk=assessment_id).first()
        return ctx


class VulnerabilityDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    model = Vulnerability
    template_name = "risks/vulnerability_detail.html"
    context_object_name = "vulnerability"
    permission_required = "risks.vulnerability.read"
    approval_module = "risks"
    approval_feature = "vulnerability"
    approve_url_name = "risks:vulnerability-approve"


class VulnerabilityCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Vulnerability
    form_class = VulnerabilityCreateForm
    template_name = "risks/vulnerability_form.html"
    modal_template_name = "risks/vulnerability_form_modal.html"
    permission_required = "risks.vulnerability.create"
    modal_title_create = _l("New vulnerability")
    modal_title_update = _l("Edit vulnerability")
    success_url = reverse_lazy("risks:vulnerability-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class VulnerabilityUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, ScopeFilterMixin, ApprovableUpdateMixin, UpdateView):
    model = Vulnerability
    form_class = VulnerabilityUpdateForm
    template_name = "risks/vulnerability_form.html"
    modal_template_name = "risks/vulnerability_form_modal.html"
    permission_required = "risks.vulnerability.update"
    modal_title_create = _l("New vulnerability")
    modal_title_update = _l("Edit vulnerability")
    success_url = reverse_lazy("risks:vulnerability-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class VulnerabilityDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Vulnerability
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.vulnerability.delete"
    success_url = reverse_lazy("risks:vulnerability-list")


# ── Scale choices API (AJAX) ────────────────────────────────

@login_required
def scale_choices_api(request):
    """Return scale choices JSON for a given assessment's criteria."""
    from .forms import get_scale_choices

    assessment_id = request.GET.get("assessment")
    criteria = None
    if assessment_id:
        try:
            assessment = RiskAssessment.objects.select_related(
                "risk_criteria"
            ).get(pk=assessment_id)
            criteria = assessment.risk_criteria
        except RiskAssessment.DoesNotExist:
            pass
    l_choices = get_scale_choices("likelihood", criteria)
    i_choices = get_scale_choices("impact", criteria)
    return JsonResponse({
        "likelihood": [{"value": str(v), "label": l} for v, l in l_choices],
        "impact": [{"value": str(v), "label": l} for v, l in i_choices],
    })


# ── ISO 27005 Risk ──────────────────────────────────────────

class ISO27005RiskListView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    scope_parent_lookup = "assessment__scopes"
    model = ISO27005Risk
    template_name = "risks/iso27005_risk_list.html"
    context_object_name = "analyses"
    permission_required = "risks.iso27005.read"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "threat": "threat__name",
        "vulnerability": "vulnerability__name",
        "likelihood": "combined_likelihood",
        "impact": "max_impact",
        "risk_level": "risk_level",
    }
    default_sort = "reference"
    search_fields = ["reference", "threat__name", "vulnerability__name"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("assessment", "threat", "vulnerability")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        return qs


class ISO27005RiskDetailView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, WorkflowStepperMixin, DetailView):
    scope_parent_lookup = "assessment__scopes"
    model = ISO27005Risk
    template_name = "risks/iso27005_risk_detail.html"
    context_object_name = "analysis"
    permission_required = "risks.iso27005.read"
    approval_module = "risks"
    approval_feature = "iso27005"
    approve_url_name = "risks:iso27005-approve"


class ISO27005RiskCreateView(LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = ISO27005Risk
    form_class = ISO27005RiskCreateForm
    template_name = "risks/iso27005_risk_form.html"
    modal_template_name = "risks/iso27005_risk_form_modal.html"
    permission_required = "risks.iso27005.create"
    modal_title_create = _l("New ISO 27005 risk")
    modal_title_update = _l("Edit ISO 27005 risk")

    def get_initial(self):
        initial = super().get_initial()
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            initial["assessment"] = assessment_id
        return initial

    def get_success_url(self):
        if self.object and self.object.assessment_id:
            return reverse_lazy(
                "risks:assessment-detail", kwargs={"pk": self.object.assessment_id}
            )
        return reverse_lazy("risks:iso27005-list")


class ISO27005RiskUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, HtmxFormMixin, ApprovableUpdateMixin, UpdateView):
    scope_parent_lookup = "assessment__scopes"
    model = ISO27005Risk
    form_class = ISO27005RiskUpdateForm
    template_name = "risks/iso27005_risk_form.html"
    modal_template_name = "risks/iso27005_risk_form_modal.html"
    permission_required = "risks.iso27005.update"
    modal_title_create = _l("New ISO 27005 risk")
    modal_title_update = _l("Edit ISO 27005 risk")

    def get_success_url(self):
        if self.object and self.object.assessment_id:
            return reverse_lazy(
                "risks:assessment-detail", kwargs={"pk": self.object.assessment_id}
            )
        return reverse_lazy("risks:iso27005-list")


class ISO27005RiskDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ScopeFilterMixin, DeleteView):
    scope_parent_lookup = "assessment__scopes"
    model = ISO27005Risk
    template_name = "risks/confirm_delete.html"
    permission_required = "risks.iso27005.delete"
    success_url = reverse_lazy("risks:iso27005-list")


class ISO27005ConsolidateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Create or update a Risk entry from an ISO 27005 analysis."""

    permission_required = "risks.risk.create"

    def post(self, request, pk):
        analysis = get_object_or_404(
            ISO27005Risk.objects.select_related("assessment", "threat", "vulnerability"),
            pk=pk,
        )
        if analysis.risk:
            messages.info(request, _("This analysis is already linked to a risk."))
            return redirect("risks:assessment-detail", pk=analysis.assessment_id)

        # Generate a unique reference
        assessment_ref = analysis.assessment.reference
        existing_count = Risk.objects.filter(assessment=analysis.assessment).count()
        reference = f"{assessment_ref}-R{existing_count + 1:03d}"
        # Ensure uniqueness
        while Risk.objects.filter(reference=reference).exists():
            existing_count += 1
            reference = f"{assessment_ref}-R{existing_count + 1:03d}"

        risk = Risk.objects.create(
            assessment=analysis.assessment,
            reference=reference,
            name=f"{analysis.threat.name} × {analysis.vulnerability.name}",
            description=analysis.description,
            risk_source="iso27005_analysis",
            source_entity_id=analysis.pk,
            source_entity_type="ISO27005Risk",
            impact_confidentiality=bool(analysis.impact_confidentiality),
            impact_integrity=bool(analysis.impact_integrity),
            impact_availability=bool(analysis.impact_availability),
            initial_likelihood=analysis.combined_likelihood,
            initial_impact=analysis.max_impact,
            current_likelihood=analysis.combined_likelihood,
            current_impact=analysis.max_impact,
            created_by=request.user,
        )
        # Copy affected assets
        risk.affected_essential_assets.set(analysis.affected_essential_assets.all())
        risk.affected_support_assets.set(analysis.affected_support_assets.all())

        # Link analysis to the new risk
        analysis.risk = risk
        analysis.save(update_fields=["risk"])

        messages.success(
            request,
            _("Risk \"%(ref)s\" created from the ISO 27005 analysis.") % {"ref": reference},
        )
        return redirect("risks:assessment-detail", pk=analysis.assessment_id)
