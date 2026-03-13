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
from django.utils.translation import gettext as _
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
from core.mixins import HtmxFormMixin, SortableListMixin
from .forms import (
    AssessmentResultForm,
    ComplianceActionPlanForm,
    ComplianceAssessmentForm,
    FindingForm,
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
from .constants import (
    ASSESSMENT_EDITABLE_STATUSES,
    ASSESSMENT_FROZEN_STATUSES,
    ASSESSMENT_TOGGLEABLE_STATUSES,
    AssessmentStatus,
    ComplianceStatus,
    FindingType,
    FINDING_REFERENCE_PREFIXES,
)
from .models import (
    AssessmentResult,
    ComplianceActionPlan,
    ComplianceAssessment,
    Finding,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)
from context.models import Scope

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
        from core.models import VersioningConfig

        obj = get_object_or_404(self.model, pk=pk)
        if not VersioningConfig.is_approval_enabled(self.model):
            messages.error(request, _("Approval is disabled for this item type."))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        feature = self.permission_feature or self.model._meta.model_name
        codename = f"compliance.{feature}.approve"
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
    template_name = "compliance/dashboard.html"

    def _filter_scoped(self, qs):
        user = self.request.user
        if user.is_superuser:
            return qs
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        model = qs.model
        if any(f.name == "scopes" for f in model._meta.many_to_many):
            return qs.filter(scopes__id__in=scope_ids).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is not None:
            ctx["user_scopes"] = Scope.objects.filter(id__in=scope_ids).select_related("parent_scope")
        from django.db.models import OuterRef, Subquery

        latest_assessment = ComplianceAssessment.objects.filter(
            framework=OuterRef("pk")
        ).order_by("-assessment_date", "-created_at")

        frameworks = self._filter_scoped(Framework.objects.all())
        ctx["framework_count"] = frameworks.count()
        ctx["frameworks"] = frameworks.filter(status="active").annotate(
            latest_compliance=Subquery(
                latest_assessment.values("overall_compliance_level")[:1]
            ),
        )[:10]
        ctx["requirement_count"] = self._filter_scoped(Requirement.objects.all()).count()
        ctx["non_compliant_count"] = self._filter_scoped(
            Requirement.objects.filter(
                compliance_status__in=["major_non_conformity", "minor_non_conformity"]
            )
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

class FrameworkListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = Framework
    template_name = "compliance/framework_list.html"
    context_object_name = "frameworks"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "type": "type",
        "category": "category",
        "compliance": "compliance_level",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "short_name"]

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
            "section__order", "requirement_number"
        )
        ctx["assessments"] = fw.assessments.order_by("-assessment_date")[:10]
        return ctx


class FrameworkCreateView(LoginRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Framework
    form_class = FrameworkForm
    template_name = "compliance/framework_form.html"
    modal_template_name = "compliance/framework_form_modal.html"
    success_url = reverse_lazy("compliance:framework-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class FrameworkUpdateView(LoginRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView):
    model = Framework
    form_class = FrameworkForm
    template_name = "compliance/framework_form.html"
    modal_template_name = "compliance/framework_form_modal.html"
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
            form.add_error("file", _("Invalid JSON: %(error)s") % {"error": exc})
            return self.form_invalid(form)
        except Exception as exc:
            logger.exception("Error while parsing the import file")
            form.add_error("file", _("File reading error: %(error)s") % {"error": exc})
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
            messages.warning(request, _("No import data in session. Please upload a file first."))
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
            messages.warning(request, _("No import data in session."))
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
            logger.exception("Error during framework import")
            messages.error(request, _("Import error: %(error)s") % {"error": exc})
            return redirect(reverse("compliance:framework-import"))

        del request.session["framework_import"]

        if existing_fw:
            msg = _(
                "Import into \"%(reference)s — %(name)s\" completed "
                "(%(section_count)s sections, "
                "%(requirement_count)s requirements added)."
            ) % {
                "reference": framework.reference,
                "name": framework.name,
                "section_count": parsed['stats']['section_count'],
                "requirement_count": parsed['stats']['requirement_count'],
            }
        else:
            msg = _(
                "Framework \"%(reference)s — %(name)s\" imported successfully "
                "(%(section_count)s sections, "
                "%(requirement_count)s requirements)."
            ) % {
                "reference": framework.reference,
                "name": framework.name,
                "section_count": parsed['stats']['section_count'],
                "requirement_count": parsed['stats']['requirement_count'],
            }
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
            response["Content-Disposition"] = 'attachment; filename="sample_framework.xlsx"'
        else:
            buf = generate_sample_json()
            response = HttpResponse(
                buf.getvalue(),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = 'attachment; filename="sample_framework.json"'
        return response


# ── Requirement ────────────────────────────────────────────

class RequirementListView(LoginRequiredMixin, SortableListMixin, ListView):
    model = Requirement
    template_name = "compliance/requirement_list.html"
    context_object_name = "requirements"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "requirement_number": "requirement_number",
        "name": "name",
        "framework": "framework__name",
        "type": "type",
        "compliance": "compliance_status",
        "priority": "priority",
    }
    default_sort = "reference"
    search_fields = ["reference", "requirement_number", "name", "framework__name"]

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

    def get_success_url(self):
        return reverse("compliance:requirement-detail", kwargs={"pk": self.object.pk})


class RequirementUpdateView(LoginRequiredMixin, ApprovableUpdateMixin, UpdateView):
    model = Requirement
    form_class = RequirementForm
    template_name = "compliance/requirement_form.html"

    def get_success_url(self):
        return reverse("compliance:requirement-detail", kwargs={"pk": self.object.pk})


class RequirementDeleteView(LoginRequiredMixin, DeleteView):
    model = Requirement
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:requirement-list")


# ── Assessment ─────────────────────────────────────────────

class AssessmentListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = ComplianceAssessment
    template_name = "compliance/assessment_list.html"
    context_object_name = "assessments"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "date": "assessment_start_date",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name"]

    def get_queryset(self):
        return (
            super().get_queryset()
            .prefetch_related("scopes", "frameworks")
            .select_related("assessor")
        )


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
        assessment = self.object
        ctx["results"] = assessment.results.select_related("requirement").order_by(
            "requirement__requirement_number"
        )
        # Build sections_with_results for grouped display
        result_data = _build_sections_with_results(assessment)
        ctx["sections_with_results"] = result_data["framework_groups"]
        ctx["multi_framework"] = result_data["multi_framework"]
        # Progress counts
        results_qs = assessment.results.all()
        total = results_qs.count()
        # Applicable results: exclude results for non-applicable requirements
        # AND results whose status is NOT_APPLICABLE
        applicable_results_qs = results_qs.exclude(
            compliance_status=ComplianceStatus.NOT_APPLICABLE,
        ).filter(requirement__is_applicable=True)
        # Total applicable requirements (denominator for coverage)
        fw_req_count = applicable_results_qs.count()
        # Evaluated = truly assessed (has findings, compliant, NC, etc.)
        # Excludes NOT_ASSESSED and EVALUATED ("Evaluation planned")
        truly_evaluated = applicable_results_qs.exclude(
            compliance_status__in=[
                ComplianceStatus.NOT_ASSESSED,
                ComplianceStatus.EVALUATED,
            ]
        ).count()
        # Covered = applicable requirements actively touched (not NOT_ASSESSED)
        covered = applicable_results_qs.exclude(
            compliance_status=ComplianceStatus.NOT_ASSESSED,
        ).count()
        ctx["results_total"] = covered
        ctx["results_evaluated"] = truly_evaluated
        ctx["results_progress"] = round(truly_evaluated * 100 / covered) if covered else 0
        ctx["has_results"] = total > 0
        ctx["fw_req_count"] = fw_req_count
        ctx["coverage_pct"] = round(covered * 100 / fw_req_count) if fw_req_count else 0
        # Compliance: average level of truly assessed results only
        # (exclude NOT_ASSESSED, NOT_APPLICABLE, and EVALUATED which is just "planned")
        assessed_qs = applicable_results_qs.exclude(
            compliance_status__in=[
                ComplianceStatus.NOT_ASSESSED,
                ComplianceStatus.NOT_APPLICABLE,
                ComplianceStatus.EVALUATED,
            ]
        )
        assessed_count = assessed_qs.count()
        if assessed_count > 0:
            from django.db.models import Avg
            avg = assessed_qs.aggregate(avg=Avg("compliance_level"))["avg"] or 0
            ctx["compliance_pct"] = round(avg)
        else:
            ctx["compliance_pct"] = 0
        # Findings (constats)
        findings = assessment.findings.select_related("assessor").prefetch_related(
            "requirements"
        ).order_by("reference")
        ctx["findings"] = findings
        ctx["findings_count"] = findings.count()
        # Counts by finding type
        finding_type_counts = {}
        for ft in FindingType:
            count = findings.filter(finding_type=ft.value).count()
            if count:
                finding_type_counts[ft.value] = {
                    "label": ft.label,
                    "count": count,
                    "prefix": FINDING_REFERENCE_PREFIXES.get(ft.value, ""),
                }
        ctx["finding_type_counts"] = finding_type_counts
        # Status-based lock flags
        from compliance.constants import (
            ASSESSMENT_FROZEN_STATUSES,
            ASSESSMENT_LOCKED_STATUSES,
            ASSESSMENT_STATUS_TRANSITIONS,
        )
        ctx["is_locked"] = assessment.status in ASSESSMENT_LOCKED_STATUSES
        ctx["is_frozen"] = assessment.status not in ASSESSMENT_EDITABLE_STATUSES
        ctx["is_toggleable"] = assessment.status in ASSESSMENT_TOGGLEABLE_STATUSES
        ctx["is_initializable"] = assessment.status not in ASSESSMENT_FROZEN_STATUSES
        next_statuses = ASSESSMENT_STATUS_TRANSITIONS.get(assessment.status, [])
        ctx["next_status"] = next_statuses[0] if next_statuses else None
        ctx["next_status_label"] = (
            AssessmentStatus(next_statuses[0]).label if next_statuses else ""
        )
        return ctx


class AssessmentCreateView(LoginRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = ComplianceAssessment
    form_class = ComplianceAssessmentForm
    template_name = "compliance/assessment_form.html"
    modal_template_name = "compliance/assessment_form_modal.html"
    success_url = reverse_lazy("compliance:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class AssessmentUpdateView(
    LoginRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView
):
    model = ComplianceAssessment
    form_class = ComplianceAssessmentForm
    template_name = "compliance/assessment_form.html"
    modal_template_name = "compliance/assessment_form_modal.html"
    success_url = reverse_lazy("compliance:assessment-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class AssessmentTransitionView(LoginRequiredMixin, View):
    """Advance an assessment to its next workflow status."""

    def post(self, request, pk):
        assessment = get_object_or_404(ComplianceAssessment, pk=pk)
        new_status = request.POST.get("status")
        try:
            assessment.transition_to(new_status)
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("compliance:assessment-detail", pk=assessment.pk)


class AssessmentDeleteView(LoginRequiredMixin, DeleteView):
    model = ComplianceAssessment
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:assessment-list")


# ── Assessment Results ─────────────────────────────────────


def _natural_sort_key(value):
    """Return a sort key that orders numeric parts numerically.

    E.g. "4.1.a" -> [4, '.', 1, '.a'], "10.1" -> [10, '.', 1]
    so that 4.1 < 5.1 < 10.1 instead of "10.1" < "4.1" < "5.1".
    """
    import re
    parts = re.split(r'(\d+)', value)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _build_sections_with_results(assessment):
    """Build a list of framework groups, each containing sections with results.

    When the assessment has a single framework, returns:
        {"multi_framework": False,
         "framework_groups": [{"framework": fw, "sections": sections_list}]}

    When multiple frameworks, returns:
        {"multi_framework": True,
         "framework_groups": [{"framework": fw, "sections": sections_list}, ...]}

    Each sections_list entry:
        {"section": Section|None, "requirements": [{"requirement": Req, "result": Result|None,
          "finding_counts": {type: count}}, ...],
          "evaluated": int, "total": int, "status_counts": dict}
    """
    results_map = {
        r.requirement_id: r
        for r in assessment.results.select_related(
            "requirement", "assessed_by"
        ).all()
    }
    requirements = assessment.get_all_requirements().select_related(
        "section", "framework"
    )

    # Build finding counts per requirement for this assessment
    finding_counts_map = {}  # requirement_id -> {finding_type: count}
    for finding in assessment.findings.prefetch_related("requirements").all():
        for req in finding.requirements.all():
            if req.pk not in finding_counts_map:
                finding_counts_map[req.pk] = {}
            ft = finding.finding_type
            finding_counts_map[req.pk][ft] = finding_counts_map[req.pk].get(ft, 0) + 1

    def _empty_status_counts():
        return {
            "compliant": 0, "strength": 0, "evaluated": 0,
            "major_nc": 0, "minor_nc": 0, "observation": 0,
            "improvement": 0, "not_assessed": 0, "not_applicable": 0,
        }

    # Map finding types to severity for worst-finding detection
    _FINDING_WORST_KEY = {
        "major_nc": 0, "minor_nc": 1, "observation": 2,
        "improvement": 3, "strength": 4,
    }

    def _classify_entry(entry):
        """Return the display category key for a requirement entry."""
        if entry["has_findings"]:
            worst = min(entry["finding_counts"].keys(),
                        key=lambda ft: _FINDING_WORST_KEY.get(ft, 99))
            return worst
        result = entry["result"]
        if not result or result.compliance_status == ComplianceStatus.NOT_ASSESSED:
            return "not_assessed"
        status_map = {
            ComplianceStatus.COMPLIANT: "compliant",
            ComplianceStatus.STRENGTH: "strength",
            ComplianceStatus.EVALUATED: "evaluated",
            ComplianceStatus.NOT_APPLICABLE: "not_applicable",
            ComplianceStatus.MAJOR_NON_CONFORMITY: "major_nc",
            ComplianceStatus.MINOR_NON_CONFORMITY: "minor_nc",
            ComplianceStatus.OBSERVATION: "observation",
            ComplianceStatus.IMPROVEMENT_OPPORTUNITY: "improvement",
        }
        return status_map.get(result.compliance_status, "not_assessed")

    def _build_sections_list(reqs_iter):
        """Build sorted sections list from an iterable of requirements."""
        sections_dict = {}
        no_section_reqs = []

        for req in reqs_iter:
            result = results_map.get(req.pk)
            has_findings = req.pk in finding_counts_map
            entry = {
                "requirement": req,
                "result": result,
                "finding_counts": finding_counts_map.get(req.pk, {}),
                "has_findings": has_findings,
            }
            if req.section_id:
                if req.section_id not in sections_dict:
                    sections_dict[req.section_id] = {
                        "section": req.section,
                        "requirements": [],
                        "evaluated": 0,
                        "total": 0,
                        "status_counts": _empty_status_counts(),
                    }
                sections_dict[req.section_id]["requirements"].append(entry)
                sections_dict[req.section_id]["total"] += 1
                cat = _classify_entry(entry)
                sections_dict[req.section_id]["status_counts"][cat] += 1
                if req.is_applicable and (has_findings or (result and result.compliance_status != ComplianceStatus.NOT_ASSESSED)):
                    sections_dict[req.section_id]["evaluated"] += 1
            else:
                no_section_reqs.append(entry)

        sections_list = sorted(
            sections_dict.values(),
            key=lambda s: _natural_sort_key(s["section"].reference),
        )

        for section_data in sections_list:
            section_data["requirements"].sort(
                key=lambda e: _natural_sort_key(
                    e["requirement"].requirement_number or e["requirement"].reference
                ),
            )

        if no_section_reqs:
            no_section_reqs.sort(
                key=lambda e: _natural_sort_key(
                    e["requirement"].requirement_number or e["requirement"].reference
                ),
            )
            evaluated = sum(
                1 for e in no_section_reqs
                if e["requirement"].is_applicable and (e["has_findings"] or (e["result"] and e["result"].compliance_status != ComplianceStatus.NOT_ASSESSED))
            )
            sc = _empty_status_counts()
            for e in no_section_reqs:
                sc[_classify_entry(e)] += 1
            sections_list.append({
                "section": None,
                "requirements": no_section_reqs,
                "evaluated": evaluated,
                "total": len(no_section_reqs),
                "status_counts": sc,
            })

        return sections_list

    frameworks = list(assessment.frameworks.all().order_by("name"))
    multi_framework = len(frameworks) > 1

    if multi_framework:
        # Group requirements by framework
        reqs_by_fw = {}
        for req in requirements:
            reqs_by_fw.setdefault(req.framework_id, []).append(req)

        framework_groups = []
        for fw in frameworks:
            fw_reqs = reqs_by_fw.get(fw.pk, [])
            framework_groups.append({
                "framework": fw,
                "sections": _build_sections_list(fw_reqs),
            })
    else:
        framework_groups = [{
            "framework": frameworks[0] if frameworks else None,
            "sections": _build_sections_list(requirements),
        }]

    return {
        "multi_framework": multi_framework,
        "framework_groups": framework_groups,
    }


def _check_assessment_not_frozen(assessment):
    """Return an HTTP 403 response if the assessment is frozen, else None."""
    if assessment.status in ASSESSMENT_FROZEN_STATUSES:
        return HttpResponse(
            _("This assessment is locked and cannot be modified."),
            status=403,
        )
    return None


def _check_assessment_toggleable(assessment):
    """Return an HTTP 403 response if toggles are not allowed, else None."""
    if assessment.status not in ASSESSMENT_TOGGLEABLE_STATUSES:
        return HttpResponse(
            _("This assessment is locked and cannot be modified."),
            status=403,
        )
    return None


def _check_assessment_editable(assessment):
    """Return an HTTP 403 response if the assessment is not in an editable status, else None."""
    if assessment.status not in ASSESSMENT_EDITABLE_STATUSES:
        return HttpResponse(
            _("This assessment is locked and cannot be modified."),
            status=403,
        )
    return None


class FrozenAssessmentGuardMixin:
    """Block POST/PUT/PATCH/DELETE on frozen assessments (COMPLETED/CLOSED)."""

    def dispatch(self, request, *args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            assessment = get_object_or_404(
                ComplianceAssessment, pk=kwargs.get("assessment_pk")
            )
            frozen = _check_assessment_not_frozen(assessment)
            if frozen:
                return frozen
        return super().dispatch(request, *args, **kwargs)


class EditableAssessmentGuardMixin:
    """Block POST/PUT/PATCH/DELETE unless assessment is IN_PROGRESS."""

    def dispatch(self, request, *args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            assessment = get_object_or_404(
                ComplianceAssessment, pk=kwargs.get("assessment_pk")
            )
            error = _check_assessment_editable(assessment)
            if error:
                return error
        return super().dispatch(request, *args, **kwargs)


class InitializeResultsView(LoginRequiredMixin, View):
    """Bulk-create AssessmentResult for all requirements (applicable and non-applicable)."""

    def post(self, request, pk):
        assessment = get_object_or_404(ComplianceAssessment, pk=pk)
        frozen = _check_assessment_not_frozen(assessment)
        if frozen:
            return frozen
        requirements = assessment.get_all_requirements()
        existing_req_ids = set(
            assessment.results.values_list("requirement_id", flat=True)
        )
        now = timezone.now()
        new_results = []
        for req in requirements:
            if req.pk in existing_req_ids:
                continue
            if req.is_applicable:
                new_results.append(
                    AssessmentResult(
                        assessment=assessment,
                        requirement=req,
                        compliance_status=ComplianceStatus.NOT_ASSESSED,
                        compliance_level=0,
                        assessed_by=request.user,
                        assessed_at=now,
                    )
                )
            else:
                new_results.append(
                    AssessmentResult(
                        assessment=assessment,
                        requirement=req,
                        compliance_status=ComplianceStatus.NOT_APPLICABLE,
                        compliance_level=100,
                        assessed_by=request.user,
                        assessed_at=now,
                    )
                )
        if new_results:
            AssessmentResult.objects.bulk_create(new_results, ignore_conflicts=True)
            assessment.recalculate_counts()
        if request.headers.get("HX-Request") == "true":
            return HttpResponse(
                status=204,
                headers={"HX-Trigger": "formSaved"},
            )
        return redirect(reverse("compliance:assessment-detail", args=[pk]))


class AssessmentResultCreateView(EditableAssessmentGuardMixin, LoginRequiredMixin, HtmxFormMixin, CreateView):
    model = AssessmentResult
    form_class = AssessmentResultForm
    template_name = "compliance/assessment_result_form.html"
    modal_template_name = "compliance/assessment_result_form_modal.html"
    modal_title_create = _("Evaluate requirement")

    def get_assessment(self):
        return get_object_or_404(
            ComplianceAssessment, pk=self.kwargs["assessment_pk"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["assessment"] = self.get_assessment()
        req_pk = self.request.GET.get("requirement")
        if req_pk:
            kwargs["requirement_instance"] = get_object_or_404(
                Requirement, pk=req_pk
            )
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.get_assessment()
        req_pk = self.request.GET.get("requirement")
        if req_pk:
            ctx["requirement_obj"] = get_object_or_404(Requirement, pk=req_pk)
        return ctx

    def form_valid(self, form):
        assessment = self.get_assessment()
        form.instance.assessment = assessment
        form.instance.assessed_by = self.request.user
        form.instance.assessed_at = timezone.now()
        # If requirement was disabled in the form, set it from the URL param
        req_pk = self.request.GET.get("requirement")
        if req_pk and not form.cleaned_data.get("requirement"):
            form.instance.requirement = get_object_or_404(Requirement, pk=req_pk)
        response = super().form_valid(form)
        assessment.recalculate_counts()
        return response

    def get_success_url(self):
        return reverse(
            "compliance:assessment-detail",
            args=[self.kwargs["assessment_pk"]],
        )


class AssessmentResultUpdateView(EditableAssessmentGuardMixin, LoginRequiredMixin, HtmxFormMixin, UpdateView):
    model = AssessmentResult
    form_class = AssessmentResultForm
    template_name = "compliance/assessment_result_form.html"
    modal_template_name = "compliance/assessment_result_form_modal.html"
    modal_title_update = _("Edit evaluation")

    def get_assessment(self):
        return get_object_or_404(
            ComplianceAssessment, pk=self.kwargs["assessment_pk"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["assessment"] = self.get_assessment()
        kwargs["requirement_instance"] = self.object.requirement
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.get_assessment()
        ctx["requirement_obj"] = self.object.requirement
        return ctx

    def form_valid(self, form):
        form.instance.assessed_by = self.request.user
        form.instance.assessed_at = timezone.now()
        # Ensure requirement is preserved when field is disabled
        if not form.cleaned_data.get("requirement"):
            form.instance.requirement = self.object.requirement
        # Enforce non-applicable status for non-applicable requirements
        if not self.object.requirement.is_applicable:
            form.instance.compliance_status = ComplianceStatus.NOT_APPLICABLE
            form.instance.compliance_level = 100
        response = super().form_valid(form)
        self.get_assessment().recalculate_counts()
        return response

    def get_success_url(self):
        return reverse(
            "compliance:assessment-detail",
            args=[self.kwargs["assessment_pk"]],
        )


class AssessmentResultDeleteView(EditableAssessmentGuardMixin, LoginRequiredMixin, DeleteView):
    model = AssessmentResult
    template_name = "compliance/confirm_delete.html"

    def get_assessment(self):
        return get_object_or_404(
            ComplianceAssessment, pk=self.kwargs["assessment_pk"]
        )

    def form_valid(self, form):
        assessment = self.get_assessment()
        response = super().form_valid(form)
        assessment.recalculate_counts()
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(
                status=204,
                headers={"HX-Trigger": "formSaved"},
            )
        return response

    def get_success_url(self):
        return reverse(
            "compliance:assessment-detail",
            args=[self.kwargs["assessment_pk"]],
        )


class ToggleResultEvaluatedView(LoginRequiredMixin, View):
    """Toggle a requirement between evaluated (compliant/100%) and not evaluated.

    Creates the AssessmentResult on the fly if it doesn't exist yet.
    """

    def post(self, request, assessment_pk, requirement_pk):
        assessment = get_object_or_404(ComplianceAssessment, pk=assessment_pk)
        error = _check_assessment_toggleable(assessment)
        if error:
            return error
        requirement = get_object_or_404(
            assessment.get_all_requirements(), pk=requirement_pk
        )
        # Don't toggle if requirement is non-applicable
        if not requirement.is_applicable:
            return HttpResponse(status=409)
        # Don't toggle if requirement has findings
        if assessment.findings.filter(requirements=requirement).exists():
            return HttpResponse(status=409)
        result, created = AssessmentResult.objects.get_or_create(
            assessment=assessment,
            requirement=requirement,
            defaults={
                "compliance_status": ComplianceStatus.EVALUATED,
                "compliance_level": 50,
                "assessed_by": request.user,
                "assessed_at": timezone.now(),
            },
        )
        if not created:
            # Cycle: NOT_ASSESSED → EVALUATED → COMPLIANT → NOT_ASSESSED
            if result.compliance_status == ComplianceStatus.NOT_ASSESSED:
                result.compliance_status = ComplianceStatus.EVALUATED
                result.compliance_level = 50
            elif result.compliance_status == ComplianceStatus.EVALUATED:
                result.compliance_status = ComplianceStatus.COMPLIANT
                result.compliance_level = 100
            else:
                result.compliance_status = ComplianceStatus.NOT_ASSESSED
                result.compliance_level = 0
            result.assessed_by = request.user
            result.assessed_at = timezone.now()
            result.save()
        assessment.recalculate_counts()
        return HttpResponse(status=204, headers={"HX-Trigger": "formSaved"})


class BulkToggleEvaluatedView(LoginRequiredMixin, View):
    """Toggle all applicable requirements (without findings) to EVALUATED or back to NOT_ASSESSED."""

    def post(self, request, pk):
        assessment = get_object_or_404(ComplianceAssessment, pk=pk)
        error = _check_assessment_toggleable(assessment)
        if error:
            return error
        now = timezone.now()

        # IDs of requirements that have findings — those are locked
        finding_req_ids = set(
            assessment.findings.values_list("requirements__id", flat=True)
        )
        finding_req_ids.discard(None)

        # Ensure all requirements have a result (like InitializeResultsView)
        all_requirements = assessment.get_all_requirements()
        existing_req_ids = set(
            assessment.results.values_list("requirement_id", flat=True)
        )
        new_results = []
        for req in all_requirements.filter(is_applicable=True):
            if req.pk not in existing_req_ids:
                new_results.append(
                    AssessmentResult(
                        assessment=assessment, requirement=req,
                        compliance_status=ComplianceStatus.NOT_ASSESSED,
                        compliance_level=0,
                        assessed_by=request.user, assessed_at=now,
                    )
                )
        for req in all_requirements.filter(is_applicable=False):
            if req.pk not in existing_req_ids:
                new_results.append(
                    AssessmentResult(
                        assessment=assessment, requirement=req,
                        compliance_status=ComplianceStatus.NOT_APPLICABLE,
                        compliance_level=100,
                        assessed_by=request.user, assessed_at=now,
                    )
                )
        if new_results:
            AssessmentResult.objects.bulk_create(new_results, ignore_conflicts=True)

        # Now toggle all applicable results
        results = assessment.results.select_related("requirement").filter(
            requirement__is_applicable=True,
        )
        toggleable = [r for r in results if r.requirement_id not in finding_req_ids]
        any_not_assessed = any(
            r.compliance_status == ComplianceStatus.NOT_ASSESSED for r in toggleable
        )
        for result in toggleable:
            if any_not_assessed:
                if result.compliance_status == ComplianceStatus.NOT_ASSESSED:
                    result.compliance_status = ComplianceStatus.EVALUATED
                    result.compliance_level = 50
                    result.assessed_by = request.user
                    result.assessed_at = now
                    result.save()
            else:
                if result.compliance_status == ComplianceStatus.EVALUATED:
                    result.compliance_status = ComplianceStatus.NOT_ASSESSED
                    result.compliance_level = 0
                    result.assessed_by = request.user
                    result.assessed_at = now
                    result.save()
        assessment.recalculate_counts()
        return HttpResponse(status=204, headers={"HX-Trigger": "formSaved"})


class AssessmentResultsTableBodyView(LoginRequiredMixin, View):
    """Return the results table body partial for HTMX refresh."""

    def get(self, request, pk):
        from django.template.loader import render_to_string

        assessment = get_object_or_404(ComplianceAssessment, pk=pk)
        result_data = _build_sections_with_results(assessment)
        html = render_to_string(
            "compliance/assessment_results_table_body.html",
            {
                "sections_with_results": result_data["framework_groups"],
                "multi_framework": result_data["multi_framework"],
                "assessment": assessment,
                "is_frozen": assessment.status not in ASSESSMENT_EDITABLE_STATUSES,
                "is_toggleable": assessment.status in ASSESSMENT_TOGGLEABLE_STATUSES,
            },
            request=request,
        )
        return HttpResponse(html)


# ── Findings ──────────────────────────────────────────────


class FindingCreateView(EditableAssessmentGuardMixin, LoginRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = Finding
    form_class = FindingForm
    template_name = "compliance/finding_form.html"
    modal_template_name = "compliance/finding_form_modal.html"
    modal_title_create = _("Add finding")

    def get_assessment(self):
        return get_object_or_404(
            ComplianceAssessment, pk=self.kwargs["assessment_pk"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["assessment"] = self.get_assessment()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.get_assessment()
        return ctx

    def form_valid(self, form):
        assessment = self.get_assessment()
        form.instance.assessment = assessment
        form.instance.assessor = self.request.user
        response = super().form_valid(form)
        assessment.apply_findings_to_results()
        return response

    def get_success_url(self):
        return reverse(
            "compliance:assessment-detail",
            args=[self.kwargs["assessment_pk"]],
        )


class FindingUpdateView(EditableAssessmentGuardMixin, LoginRequiredMixin, HtmxFormMixin, UpdateView):
    model = Finding
    form_class = FindingForm
    template_name = "compliance/finding_form.html"
    modal_template_name = "compliance/finding_form_modal.html"
    modal_title_update = _("Edit finding")

    def get_assessment(self):
        return get_object_or_404(
            ComplianceAssessment, pk=self.kwargs["assessment_pk"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["assessment"] = self.get_assessment()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.get_assessment()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        self.get_assessment().apply_findings_to_results()
        return response

    def get_success_url(self):
        return reverse(
            "compliance:assessment-detail",
            args=[self.kwargs["assessment_pk"]],
        )


class FindingDeleteView(EditableAssessmentGuardMixin, LoginRequiredMixin, DeleteView):
    model = Finding
    template_name = "compliance/confirm_delete.html"

    def get_assessment(self):
        return get_object_or_404(
            ComplianceAssessment, pk=self.kwargs["assessment_pk"]
        )

    def delete(self, request, *args, **kwargs):
        assessment = self.get_assessment()
        self.object = self.get_object()
        self.object.delete()
        assessment.apply_findings_to_results()
        if request.headers.get("HX-Request") == "true":
            return HttpResponse(
                status=204,
                headers={"HX-Trigger": "formSaved"},
            )
        return HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "compliance:assessment-detail",
            args=[self.kwargs["assessment_pk"]],
        )


class FindingsTableBodyView(LoginRequiredMixin, View):
    """Return the findings table body partial for HTMX refresh."""

    def get(self, request, pk):
        from django.template.loader import render_to_string

        assessment = get_object_or_404(ComplianceAssessment, pk=pk)
        findings = assessment.findings.select_related("assessor").prefetch_related(
            "requirements"
        ).order_by("reference")
        html = render_to_string(
            "compliance/findings_table_body.html",
            {
                "findings": findings,
                "assessment": assessment,
                "is_frozen": assessment.status not in ASSESSMENT_EDITABLE_STATUSES,
            },
            request=request,
        )
        return HttpResponse(html)


# ── Mapping ────────────────────────────────────────────────

class MappingListView(LoginRequiredMixin, SortableListMixin, ListView):
    model = RequirementMapping
    template_name = "compliance/mapping_list.html"
    context_object_name = "mappings"
    paginate_by = 25
    sortable_fields = {
        "source": "source_requirement__reference",
        "target": "target_requirement__reference",
        "type": "mapping_type",
        "coverage": "coverage_level",
    }
    default_sort = "source"
    search_fields = [
        "source_requirement__reference",
        "source_requirement__name",
        "target_requirement__reference",
        "target_requirement__name",
    ]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "source_requirement__framework",
            "target_requirement__framework",
        )


class MappingDetailView(LoginRequiredMixin, DetailView):
    model = RequirementMapping
    template_name = "compliance/mapping_detail.html"
    context_object_name = "mapping"


class MappingCreateView(LoginRequiredMixin, HtmxFormMixin, CreateView):
    model = RequirementMapping
    form_class = RequirementMappingForm
    template_name = "compliance/mapping_form.html"
    modal_template_name = "compliance/mapping_form_modal.html"
    success_url = reverse_lazy("compliance:mapping-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class MappingUpdateView(LoginRequiredMixin, HtmxFormMixin, UpdateView):
    model = RequirementMapping
    form_class = RequirementMappingForm
    template_name = "compliance/mapping_form.html"
    modal_template_name = "compliance/mapping_form_modal.html"
    success_url = reverse_lazy("compliance:mapping-list")


class MappingDeleteView(LoginRequiredMixin, DeleteView):
    model = RequirementMapping
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:mapping-list")


# ── Action Plan ────────────────────────────────────────────

class ActionPlanListView(LoginRequiredMixin, ScopeFilterMixin, SortableListMixin, ListView):
    model = ComplianceActionPlan
    template_name = "compliance/action_plan_list.html"
    context_object_name = "action_plans"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "name": "name",
        "priority": "priority",
        "target_date": "target_date",
        "progress": "progress_percentage",
        "status": "status",
    }
    default_sort = "reference"
    search_fields = ["reference", "name", "requirement__reference"]

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("scopes").select_related("owner", "requirement")
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


class ActionPlanCreateView(LoginRequiredMixin, HtmxFormMixin, CreatedByMixin, CreateView):
    model = ComplianceActionPlan
    form_class = ComplianceActionPlanForm
    template_name = "compliance/action_plan_form.html"
    modal_template_name = "compliance/action_plan_form_modal.html"
    success_url = reverse_lazy("compliance:action-plan-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActionPlanUpdateView(
    LoginRequiredMixin, HtmxFormMixin, ApprovableUpdateMixin, ScopeFilterMixin, UpdateView
):
    model = ComplianceActionPlan
    form_class = ComplianceActionPlanForm
    template_name = "compliance/action_plan_form.html"
    modal_template_name = "compliance/action_plan_form_modal.html"
    success_url = reverse_lazy("compliance:action-plan-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ActionPlanDeleteView(LoginRequiredMixin, DeleteView):
    model = ComplianceActionPlan
    template_name = "compliance/confirm_delete.html"
    success_url = reverse_lazy("compliance:action-plan-list")
