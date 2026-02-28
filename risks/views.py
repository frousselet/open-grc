from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
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
from .constants import (
    DEFAULT_IMPACT_SCALES,
    DEFAULT_LIKELIHOOD_SCALES,
    DEFAULT_RISK_LEVELS,
    DEFAULT_RISK_MATRIX,
)
from .forms import (
    ImpactFormSet,
    ISO27005RiskForm,
    LikelihoodFormSet,
    RiskAcceptanceForm,
    RiskAssessmentForm,
    RiskCriteriaForm,
    RiskForm,
    RiskLevelFormSet,
    RiskTreatmentPlanForm,
    ThreatForm,
    VulnerabilityForm,
)
from .models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskTreatmentPlan,
    Threat,
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


class ApproveView(LoginRequiredMixin, View):
    """Generic approve view for risks domain models."""

    model = None
    permission_feature = None
    success_url = None

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
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


# ── Dashboard ───────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "risks/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment_count"] = RiskAssessment.objects.count()
        ctx["assessment_by_status"] = (
            RiskAssessment.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        ctx["risk_count"] = Risk.objects.count()
        ctx["risk_by_status"] = (
            Risk.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        ctx["risk_by_priority"] = (
            Risk.objects.values("priority")
            .annotate(count=Count("id"))
            .order_by("priority")
        )
        ctx["treatment_plan_count"] = RiskTreatmentPlan.objects.count()
        ctx["treatment_in_progress"] = RiskTreatmentPlan.objects.filter(
            status="in_progress"
        ).count()
        ctx["threat_count"] = Threat.objects.count()
        ctx["vulnerability_count"] = Vulnerability.objects.count()
        ctx["acceptance_count"] = RiskAcceptance.objects.filter(
            status="active"
        ).count()

        # Risk matrices (before / after treatment)
        criteria = RiskCriteria.objects.filter(is_default=True).first()
        if not criteria:
            criteria = RiskCriteria.objects.filter(status="active").first()
        all_risks = Risk.objects.all()
        if criteria:
            ctx["matrix_criteria"] = criteria
            ctx["matrix_current"] = build_risk_matrix(
                all_risks, criteria, "current_likelihood", "current_impact"
            )
            ctx["matrix_residual"] = build_risk_matrix(
                all_risks, criteria, "residual_likelihood", "residual_impact"
            )
        # Fallback to default 5×5 matrix if no criteria or build returned None
        if not ctx.get("matrix_current"):
            ctx["matrix_current"] = build_default_risk_matrix(
                all_risks, "current_likelihood", "current_impact"
            )
        if not ctx.get("matrix_residual"):
            ctx["matrix_residual"] = build_default_risk_matrix(
                all_risks, "residual_likelihood", "residual_impact"
            )
        return ctx


# ── Risk Assessment ─────────────────────────────────────────

class RiskAssessmentListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = RiskAssessment
    template_name = "risks/assessment_list.html"
    context_object_name = "assessments"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope", "assessor", "risk_criteria")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RiskAssessmentDetailView(LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = RiskAssessment
    template_name = "risks/assessment_detail.html"
    context_object_name = "assessment"
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


class RiskAssessmentCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = RiskAssessment
    form_class = RiskAssessmentForm
    template_name = "risks/assessment_form.html"
    success_url = reverse_lazy("risks:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RiskAssessmentUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = RiskAssessment
    form_class = RiskAssessmentForm
    template_name = "risks/assessment_form.html"
    success_url = reverse_lazy("risks:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RiskAssessmentDeleteView(LoginRequiredMixin, DeleteView):
    model = RiskAssessment
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:assessment-list")


# ── Risk Criteria ───────────────────────────────────────────

class RiskCriteriaListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = RiskCriteria
    template_name = "risks/criteria_list.html"
    context_object_name = "criteria_list"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RiskCriteriaDetailView(LoginRequiredMixin, ScopeFilterMixin, HistoryMixin, DetailView):
    model = RiskCriteria
    template_name = "risks/criteria_detail.html"
    context_object_name = "criteria"

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


class RiskCriteriaCreateView(LoginRequiredMixin, CreatedByMixin, CriteriaFormsetMixin, CreateView):
    model = RiskCriteria
    form_class = RiskCriteriaForm
    template_name = "risks/criteria_form.html"
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


class RiskCriteriaUpdateView(LoginRequiredMixin, CriteriaFormsetMixin, ScopeFilterMixin, UpdateView):
    model = RiskCriteria
    form_class = RiskCriteriaForm
    template_name = "risks/criteria_form.html"
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


class RiskCriteriaDeleteView(LoginRequiredMixin, DeleteView):
    model = RiskCriteria
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:criteria-list")


# ── Risk ────────────────────────────────────────────────────

class RiskListView(LoginRequiredMixin, ListView):
    model = Risk
    template_name = "risks/risk_list.html"
    context_object_name = "risks"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("assessment", "risk_owner")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        priority = self.request.GET.get("priority")
        if priority:
            qs = qs.filter(priority=priority)
        return qs


class RiskDetailView(LoginRequiredMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = Risk
    template_name = "risks/risk_detail.html"
    context_object_name = "risk"
    approval_module = "risks"
    approval_feature = "risk"
    approve_url_name = "risks:risk-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["treatment_plans"] = self.object.treatment_plans.all()
        ctx["acceptances"] = self.object.acceptances.all()
        ctx["iso27005_sources"] = self.object.iso27005_sources.select_related("threat", "vulnerability").all()
        return ctx


class RiskCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Risk
    form_class = RiskForm
    template_name = "risks/risk_form.html"
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


class RiskUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = Risk
    form_class = RiskForm
    template_name = "risks/risk_form.html"
    success_url = reverse_lazy("risks:risk-list")


class RiskDeleteView(LoginRequiredMixin, DeleteView):
    model = Risk
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:risk-list")


# ── Treatment Plan ──────────────────────────────────────────

class TreatmentPlanListView(LoginRequiredMixin, ListView):
    model = RiskTreatmentPlan
    template_name = "risks/treatment_plan_list.html"
    context_object_name = "plans"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("risk", "owner")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(risk__assessment_id=assessment_id)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class TreatmentPlanDetailView(LoginRequiredMixin, ApprovalContextMixin, HistoryMixin, DetailView):
    model = RiskTreatmentPlan
    template_name = "risks/treatment_plan_detail.html"
    context_object_name = "plan"
    approval_module = "risks"
    approval_feature = "treatment"
    approve_url_name = "risks:treatment-plan-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["actions"] = self.object.actions.select_related("owner").all()
        return ctx


class TreatmentPlanCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = RiskTreatmentPlan
    form_class = RiskTreatmentPlanForm
    template_name = "risks/treatment_plan_form.html"
    success_url = reverse_lazy("risks:treatment-plan-list")


class TreatmentPlanUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = RiskTreatmentPlan
    form_class = RiskTreatmentPlanForm
    template_name = "risks/treatment_plan_form.html"
    success_url = reverse_lazy("risks:treatment-plan-list")


class TreatmentPlanDeleteView(LoginRequiredMixin, DeleteView):
    model = RiskTreatmentPlan
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:treatment-plan-list")


# ── Risk Acceptance ─────────────────────────────────────────

class RiskAcceptanceListView(LoginRequiredMixin, ListView):
    model = RiskAcceptance
    template_name = "risks/acceptance_list.html"
    context_object_name = "acceptances"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("risk", "accepted_by")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(risk__assessment_id=assessment_id)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RiskAcceptanceDetailView(LoginRequiredMixin, HistoryMixin, DetailView):
    model = RiskAcceptance
    template_name = "risks/acceptance_detail.html"
    context_object_name = "acceptance"


class RiskAcceptanceCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = RiskAcceptance
    form_class = RiskAcceptanceForm
    template_name = "risks/acceptance_form.html"
    success_url = reverse_lazy("risks:acceptance-list")


class RiskAcceptanceUpdateView(LoginRequiredMixin, UpdateView):
    model = RiskAcceptance
    form_class = RiskAcceptanceForm
    template_name = "risks/acceptance_form.html"
    success_url = reverse_lazy("risks:acceptance-list")


class RiskAcceptanceDeleteView(LoginRequiredMixin, DeleteView):
    model = RiskAcceptance
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:acceptance-list")


# ── Threat ──────────────────────────────────────────────────

class ThreatListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Threat
    template_name = "risks/threat_list.html"
    context_object_name = "threats"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope")
        threat_type = self.request.GET.get("type")
        if threat_type:
            qs = qs.filter(type=threat_type)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class ThreatDetailView(LoginRequiredMixin, ScopeFilterMixin, HistoryMixin, DetailView):
    model = Threat
    template_name = "risks/threat_detail.html"
    context_object_name = "threat"


class ThreatCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Threat
    form_class = ThreatForm
    template_name = "risks/threat_form.html"
    success_url = reverse_lazy("risks:threat-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ThreatUpdateView(LoginRequiredMixin, ScopeFilterMixin, UpdateView):
    model = Threat
    form_class = ThreatForm
    template_name = "risks/threat_form.html"
    success_url = reverse_lazy("risks:threat-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ThreatDeleteView(LoginRequiredMixin, DeleteView):
    model = Threat
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:threat-list")


# ── Vulnerability ───────────────────────────────────────────

class VulnerabilityListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Vulnerability
    template_name = "risks/vulnerability_list.html"
    context_object_name = "vulnerabilities"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope")
        category = self.request.GET.get("category")
        if category:
            qs = qs.filter(category=category)
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class VulnerabilityDetailView(LoginRequiredMixin, ScopeFilterMixin, HistoryMixin, DetailView):
    model = Vulnerability
    template_name = "risks/vulnerability_detail.html"
    context_object_name = "vulnerability"


class VulnerabilityCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Vulnerability
    form_class = VulnerabilityForm
    template_name = "risks/vulnerability_form.html"
    success_url = reverse_lazy("risks:vulnerability-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class VulnerabilityUpdateView(LoginRequiredMixin, ScopeFilterMixin, UpdateView):
    model = Vulnerability
    form_class = VulnerabilityForm
    template_name = "risks/vulnerability_form.html"
    success_url = reverse_lazy("risks:vulnerability-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class VulnerabilityDeleteView(LoginRequiredMixin, DeleteView):
    model = Vulnerability
    template_name = "risks/confirm_delete.html"
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

class ISO27005RiskListView(LoginRequiredMixin, ListView):
    model = ISO27005Risk
    template_name = "risks/iso27005_risk_list.html"
    context_object_name = "analyses"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("assessment", "threat", "vulnerability")
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        return qs


class ISO27005RiskDetailView(LoginRequiredMixin, HistoryMixin, DetailView):
    model = ISO27005Risk
    template_name = "risks/iso27005_risk_detail.html"
    context_object_name = "analysis"


class ISO27005RiskCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = ISO27005Risk
    form_class = ISO27005RiskForm
    template_name = "risks/iso27005_risk_form.html"

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


class ISO27005RiskUpdateView(LoginRequiredMixin, UpdateView):
    model = ISO27005Risk
    form_class = ISO27005RiskForm
    template_name = "risks/iso27005_risk_form.html"

    def get_success_url(self):
        if self.object and self.object.assessment_id:
            return reverse_lazy(
                "risks:assessment-detail", kwargs={"pk": self.object.assessment_id}
            )
        return reverse_lazy("risks:iso27005-list")


class ISO27005RiskDeleteView(LoginRequiredMixin, DeleteView):
    model = ISO27005Risk
    template_name = "risks/confirm_delete.html"
    success_url = reverse_lazy("risks:iso27005-list")


class ISO27005ConsolidateView(LoginRequiredMixin, View):
    """Create or update a Risk entry from an ISO 27005 analysis."""

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
