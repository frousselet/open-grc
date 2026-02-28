import json
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import ApprovableUpdateMixin, ApprovalContextMixin, ScopeFilterMixin
from .forms import (
    ComplianceActionPlanForm,
    ComplianceAssessmentForm,
    FrameworkForm,
    FrameworkImportForm,
    RequirementForm,
    RequirementMappingForm,
    SectionForm,
)
from .import_utils import (
    execute_import,
    generate_sample_excel,
    generate_sample_json,
    parse_excel,
    parse_json,
    validate_parsed_data,
)
from .models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)

User = get_user_model()
logger = logging.getLogger(__name__)


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
    """Generic approve view for compliance domain models."""

    model = None
    permission_feature = None
    success_url = None

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"compliance.{feature}.approve"
        if not request.user.is_superuser and not request.user.has_perm(codename):
            messages.error(request, "Vous n'avez pas la permission d'approuver cet élément.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        obj.is_approved = True
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["is_approved", "approved_by", "approved_at"])
        messages.success(request, "Élément approuvé.")
        return redirect(request.META.get("HTTP_REFERER", self.success_url or "/"))


# ── Dashboard ───────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "compliance/dashboard.html"

    def _filter_scoped(self, qs):
        user = self.request.user
        if user.is_superuser:
            return qs
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        model = qs.model
        if hasattr(model, "scope"):
            return qs.filter(scope_id__in=scope_ids)
        if model._meta.many_to_many and any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        frameworks = self._filter_scoped(Framework.objects.all())
        ctx["framework_count"] = frameworks.count()
        ctx["frameworks"] = frameworks.filter(status="active")[:10]
        ctx["requirement_count"] = self._filter_scoped(Requirement.objects.all()).count()
        ctx["non_compliant_count"] = self._filter_scoped(
            Requirement.objects.filter(compliance_status="non_compliant")
        ).count()
        ctx["assessment_count"] = self._filter_scoped(
            ComplianceAssessment.objects.all()
        ).count()
        ctx["action_plan_count"] = self._filter_scoped(
            ComplianceActionPlan.objects.all()
        ).count()
        ctx["overdue_plans"] = self._filter_scoped(
            ComplianceActionPlan.objects.filter(
                target_date__lt=timezone.now().date()
            ).exclude(status__in=["completed", "cancelled"])
        ).count()
        ctx["mapping_count"] = RequirementMapping.objects.count()
        return ctx


# ── Framework ──────────────────────────────────────────────

class FrameworkListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = Framework
    template_name = "compliance/framework_list.html"
    context_object_name = "frameworks"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        type_filter = self.request.GET.get("type")
        if type_filter:
            qs = qs.filter(type=type_filter)
        return qs


class FrameworkDetailView(
    LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView
):
    model = Framework
    template_name = "compliance/framework_detail.html"
    context_object_name = "framework"
    approve_url_name = "compliance:framework-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fw = self.object
        ctx["sections"] = fw.sections.filter(parent_section__isnull=True).order_by("order")
        ctx["requirements"] = fw.requirements.select_related("section", "owner").order_by(
            "section__order", "order"
        )
        ctx["assessments"] = fw.assessments.order_by("-assessment_date")[:10]
        return ctx


class FrameworkCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Framework
    form_class = FrameworkForm
    template_name = "compliance/framework_form.html"
    success_url = reverse_lazy("compliance:framework-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class FrameworkUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Framework
    form_class = FrameworkForm
    template_name = "compliance/framework_form.html"
    success_url = reverse_lazy("compliance:framework-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class FrameworkDeleteView(LoginRequiredMixin, DeleteView):
    model = Framework
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:framework-list")


# ── Framework Import ──────────────────────────────────────


class FrameworkImportView(LoginRequiredMixin, FormView):
    template_name = "compliance/framework_import.html"
    form_class = FrameworkImportForm

    def form_valid(self, form):
        uploaded = form.cleaned_data["file"]
        ext = uploaded.name.rsplit(".", 1)[-1].lower()

        try:
            if ext == "json":
                parsed = parse_json(uploaded)
            else:
                parsed = parse_excel(uploaded)
        except json.JSONDecodeError as exc:
            form.add_error("file", f"JSON invalide : {exc}")
            return self.form_invalid(form)
        except Exception as exc:
            logger.exception("Erreur lors du parsing du fichier d'import")
            form.add_error("file", f"Erreur de lecture du fichier : {exc}")
            return self.form_invalid(form)

        existing_fw = form.cleaned_data.get("existing_framework")
        errors, warnings = validate_parsed_data(parsed, existing_framework=existing_fw)

        if errors:
            for error in errors:
                form.add_error(None, error)
            return self.form_invalid(form)

        # Store in session for preview step
        owner = form.cleaned_data.get("owner")
        session_data = {
            "parsed": parsed,
            "owner_id": str(owner.pk) if owner else None,
            "warnings": warnings,
            "existing_framework_id": str(existing_fw.pk) if existing_fw else None,
        }
        self.request.session["framework_import"] = session_data
        return redirect(reverse("compliance:framework-import-preview"))


class FrameworkImportPreviewView(LoginRequiredMixin, TemplateView):
    template_name = "compliance/framework_import_preview.html"

    def dispatch(self, request, *args, **kwargs):
        if "framework_import" not in request.session:
            messages.warning(request, "Aucune donnée d'import en session. Veuillez d'abord charger un fichier.")
            return redirect(reverse("compliance:framework-import"))
        return super().dispatch(request, *args, **kwargs)

    def _get_existing_framework(self, import_data):
        fw_id = import_data.get("existing_framework_id")
        if fw_id:
            return Framework.objects.filter(pk=fw_id).first()
        return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import_data = self.request.session["framework_import"]
        parsed = import_data["parsed"]
        ctx["framework"] = parsed["framework"]
        ctx["sections"] = parsed["sections"]
        ctx["stats"] = parsed["stats"]
        ctx["warnings"] = import_data.get("warnings", [])
        existing_fw = self._get_existing_framework(import_data)
        ctx["existing_framework"] = existing_fw
        return ctx

    def post(self, request, *args, **kwargs):
        import_data = request.session.get("framework_import")
        if not import_data:
            messages.warning(request, "Aucune donnée d'import en session.")
            return redirect(reverse("compliance:framework-import"))

        parsed = import_data["parsed"]
        existing_fw = self._get_existing_framework(import_data)

        if existing_fw:
            owner = existing_fw.owner
        else:
            owner = User.objects.get(pk=import_data["owner_id"])

        try:
            framework = execute_import(
                parsed,
                owner=owner,
                created_by=request.user,
                existing_framework=existing_fw,
            )
        except Exception as exc:
            logger.exception("Erreur lors de l'import du référentiel")
            messages.error(request, f"Erreur lors de l'import : {exc}")
            return redirect(reverse("compliance:framework-import"))

        del request.session["framework_import"]

        if existing_fw:
            msg = (
                f"Import dans \"{framework.reference} — {framework.name}\" effectué "
                f"({parsed['stats']['section_count']} sections, "
                f"{parsed['stats']['requirement_count']} exigences ajoutées)."
            )
        else:
            msg = (
                f"Référentiel \"{framework.reference} — {framework.name}\" importé avec succès "
                f"({parsed['stats']['section_count']} sections, "
                f"{parsed['stats']['requirement_count']} exigences)."
            )
        messages.success(request, msg)
        return redirect(reverse("compliance:framework-detail", args=[framework.pk]))


class FrameworkImportSampleView(LoginRequiredMixin, View):
    """Serve a sample import file (JSON or Excel)."""

    def get(self, request):
        fmt = request.GET.get("format", "json")
        if fmt == "xlsx":
            buf = generate_sample_excel()
            response = HttpResponse(
                buf.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="exemple_referentiel.xlsx"'
        else:
            buf = generate_sample_json()
            response = HttpResponse(
                buf.getvalue(),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = 'attachment; filename="exemple_referentiel.json"'
        return response


# ── Requirement ────────────────────────────────────────────

class RequirementListView(LoginRequiredMixin, ListView):
    model = Requirement
    template_name = "compliance/requirement_list.html"
    context_object_name = "requirements"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("framework", "section")
        framework_filter = self.request.GET.get("framework")
        if framework_filter:
            qs = qs.filter(framework_id=framework_filter)
        status_filter = self.request.GET.get("compliance_status")
        if status_filter:
            qs = qs.filter(compliance_status=status_filter)
        return qs


class RequirementDetailView(
    LoginRequiredMixin, ApprovalContextMixin, HistoryMixin, DetailView
):
    model = Requirement
    template_name = "compliance/requirement_detail.html"
    context_object_name = "requirement"
    approve_url_name = "compliance:requirement-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = self.object
        ctx["action_plans"] = req.action_plans.all()[:10]
        ctx["mappings_source"] = req.mappings_as_source.select_related(
            "target_requirement__framework"
        )
        ctx["mappings_target"] = req.mappings_as_target.select_related(
            "source_requirement__framework"
        )
        return ctx


class RequirementCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = Requirement
    form_class = RequirementForm
    template_name = "compliance/requirement_form.html"
    success_url = reverse_lazy("compliance:requirement-list")


class RequirementUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = Requirement
    form_class = RequirementForm
    template_name = "compliance/requirement_form.html"
    success_url = reverse_lazy("compliance:requirement-list")


class RequirementDeleteView(LoginRequiredMixin, DeleteView):
    model = Requirement
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:requirement-list")


# ── Assessment ─────────────────────────────────────────────

class AssessmentListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = ComplianceAssessment
    template_name = "compliance/assessment_list.html"
    context_object_name = "assessments"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("scope", "framework", "assessor")


class AssessmentDetailView(
    LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView
):
    model = ComplianceAssessment
    template_name = "compliance/assessment_detail.html"
    context_object_name = "assessment"
    approval_feature = "assessment"
    approve_url_name = "compliance:assessment-approve"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["results"] = self.object.results.select_related("requirement").order_by(
            "requirement__order"
        )
        return ctx


class AssessmentCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = ComplianceAssessment
    form_class = ComplianceAssessmentForm
    template_name = "compliance/assessment_form.html"
    success_url = reverse_lazy("compliance:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class AssessmentUpdateView(
    LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView
):
    model = ComplianceAssessment
    form_class = ComplianceAssessmentForm
    template_name = "compliance/assessment_form.html"
    success_url = reverse_lazy("compliance:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class AssessmentDeleteView(LoginRequiredMixin, DeleteView):
    model = ComplianceAssessment
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:assessment-list")


# ── Mapping ────────────────────────────────────────────────

class MappingListView(LoginRequiredMixin, ListView):
    model = RequirementMapping
    template_name = "compliance/mapping_list.html"
    context_object_name = "mappings"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related(
            "source_requirement__framework",
            "target_requirement__framework",
        )


class MappingDetailView(LoginRequiredMixin, DetailView):
    model = RequirementMapping
    template_name = "compliance/mapping_detail.html"
    context_object_name = "mapping"


class MappingCreateView(LoginRequiredMixin, CreateView):
    model = RequirementMapping
    form_class = RequirementMappingForm
    template_name = "compliance/mapping_form.html"
    success_url = reverse_lazy("compliance:mapping-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class MappingUpdateView(LoginRequiredMixin, UpdateView):
    model = RequirementMapping
    form_class = RequirementMappingForm
    template_name = "compliance/mapping_form.html"
    success_url = reverse_lazy("compliance:mapping-list")


class MappingDeleteView(LoginRequiredMixin, DeleteView):
    model = RequirementMapping
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:mapping-list")


# ── Action Plan ────────────────────────────────────────────

class ActionPlanListView(LoginRequiredMixin, ScopeFilterMixin, ListView):
    model = ComplianceActionPlan
    template_name = "compliance/action_plan_list.html"
    context_object_name = "action_plans"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("scope", "owner", "requirement")
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class ActionPlanDetailView(
    LoginRequiredMixin, ScopeFilterMixin, ApprovalContextMixin, HistoryMixin, DetailView
):
    model = ComplianceActionPlan
    template_name = "compliance/action_plan_detail.html"
    context_object_name = "action_plan"
    approval_feature = "action_plan"
    approve_url_name = "compliance:action-plan-approve"


class ActionPlanCreateView(LoginRequiredMixin, CreatedByMixin, CreateView):
    model = ComplianceActionPlan
    form_class = ComplianceActionPlanForm
    template_name = "compliance/action_plan_form.html"
    success_url = reverse_lazy("compliance:action-plan-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActionPlanUpdateView(
    LoginRequiredMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView
):
    model = ComplianceActionPlan
    form_class = ComplianceActionPlanForm
    template_name = "compliance/action_plan_form.html"
    success_url = reverse_lazy("compliance:action-plan-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActionPlanDeleteView(LoginRequiredMixin, DeleteView):
    model = ComplianceActionPlan
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:action-plan-list")
