"""Web views for the EBIOS RM module (workshops W0..W5).

Mounted under `/risks/assessments/<assessment_pk>/ebios/...`. The views are
class-based, scope-filtered, permission-gated and HTMX-friendly: any view
that handles a form save returns a partial when the request carries the
`HX-Request` header.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, DetailView, UpdateView

from accounts.mixins import ScopeFilterMixin
from accounts.views import PermissionRequiredMixin
from core.mixins import HtmxFormMixin
from risks.constants import (
    EBIOS_WORKSHOP_COUNT,
    EbiosIterationType,
    EbiosWorkshopNumber,
    EbiosWorkshopStatus,
)


# ── Stepper context builder ──────────────────────────────────


_WORKSHOP_SHORT_LABELS = {
    0: _("Framework"),
    1: _("Baseline"),
    2: _("Sources"),
    3: _("Strategic"),
    4: _("Operational"),
    5: _("Treatment"),
}


def build_ebios_stepper_context(assessment, current_workshop=None):
    """Return the dict consumed by `risks/ebios/_workshop_stepper.html`.

    Mirrors the structure of `compliance.AssessmentDetailView`:
    - `ebios_workshops` (list of dicts with state in done/current/next/future)
    - `rejected_workshops` (list of dicts for the bottom branch)
    - `ebios_next_workshop` (the workshop ready to be started, or None)
    - `branch_line_color`, `branch_line_opacity` (SVG branch styling hints)
    """
    qs = assessment.ebios_workshops.filter(
        iteration_type=EbiosIterationType.STRATEGIC,
    ).order_by("iteration_number", "workshop_number")
    workshops = list(qs)

    # Identify the "current" workshop = the lowest-numbered non-validated.
    current_idx = None
    for i, w in enumerate(workshops):
        if w.status != EbiosWorkshopStatus.VALIDATED:
            current_idx = i
            break

    next_action = None
    steps = []
    rejected = []
    for i, w in enumerate(workshops):
        short_label = _WORKSHOP_SHORT_LABELS.get(w.workshop_number, "")
        if w.status == EbiosWorkshopStatus.REJECTED:
            # Rejected workshops live on the bottom branch, mirroring the
            # compliance "cancelled" pill. They keep their workshop_number
            # as the label so the user can navigate back to them.
            rejected.append({
                "pk": str(w.pk),
                "workshop_number": w.workshop_number,
                "label": w.get_workshop_number_display(),
                "short_label": short_label,
                "status": w.status,
                "state": "rejected",
                "is_current": current_workshop is not None and current_workshop.pk == w.pk,
            })
            continue

        if w.status == EbiosWorkshopStatus.VALIDATED:
            state = "done"
        elif w.status == EbiosWorkshopStatus.IN_PROGRESS:
            state = "current"
        elif w.status == EbiosWorkshopStatus.UNDER_REVIEW:
            state = "review"
        elif current_idx is not None and i == current_idx:
            # not_started AND it's the first non-validated workshop -> next CTA
            state = "next"
            next_action = w
        else:
            state = "future"

        steps.append({
            "pk": str(w.pk),
            "workshop_number": w.workshop_number,
            "label": w.get_workshop_number_display(),
            "short_label": short_label,
            "status": w.status,
            "state": state,
            "is_current": current_workshop is not None and current_workshop.pk == w.pk,
        })

    return {
        "ebios_workshops": workshops,  # backwards-compat for templates expecting the queryset
        "ebios_stepper_steps": steps,
        "ebios_rejected_steps": rejected,
        "ebios_next_action": next_action,
        "ebios_branch_line_color": "var(--danger)" if rejected else "var(--border-light)",
        "ebios_branch_line_opacity": "1" if rejected else "0.3",
    }
from risks.forms_ebios import (
    AttackPathStepForm,
    AttackTechniqueForm,
    BaselineGapForm,
    EbiosSummaryForm,
    EcosystemStakeholderForm,
    FearedEventForm,
    OperationalScenarioForm,
    PACSMeasureForm,
    RiskSourceForm,
    RiskSourceObjectivePairForm,
    SecurityBaselineForm,
    StrategicScenarioForm,
    StudyFrameworkForm,
    TargetedObjectiveForm,
    WorkshopRejectForm,
)
from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosSummary,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    OperationalScenario,
    PACSMeasure,
    Risk,
    RiskAssessment,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)


# ── Workshop transitions ──────────────────────────────────────


class _WorkshopTransitionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base class for workshop status transitions.

    Subclasses set `target_status` and override `_check_preconditions(workshop)`
    to enforce the porte de validation.
    """

    permission_required = "risks.ebios_assessment.update"
    target_status: str = ""

    def _check_preconditions(self, workshop):
        """Return a list of error strings; empty list when the transition is OK."""
        return []

    def post(self, request, assessment_pk, workshop_pk):
        workshop = get_object_or_404(
            EbiosWorkshopProgress.objects.select_related("assessment"),
            pk=workshop_pk,
            assessment_id=assessment_pk,
        )
        errors = self._check_preconditions(workshop)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect(
                "risks:ebios-workshop-detail",
                assessment_pk=assessment_pk, workshop_pk=workshop_pk,
            )
        workshop.status = self.target_status
        if self.target_status == EbiosWorkshopStatus.IN_PROGRESS and not workshop.started_at:
            workshop.started_at = timezone.now()
        if self.target_status == EbiosWorkshopStatus.VALIDATED:
            workshop.validated_by = request.user
            workshop.validated_at = timezone.now()
        workshop.save()
        messages.success(request, _("Workshop status updated."))
        return redirect(
            "risks:ebios-workshop-detail",
            assessment_pk=assessment_pk, workshop_pk=workshop_pk,
        )


class WorkshopStartView(_WorkshopTransitionView):
    target_status = EbiosWorkshopStatus.IN_PROGRESS

    def _check_preconditions(self, workshop):
        if workshop.status not in (
            EbiosWorkshopStatus.NOT_STARTED,
            EbiosWorkshopStatus.REJECTED,
        ):
            return [_("Workshop is already in progress or beyond.")]
        # Workshops other than W0 require the previous workshop to be validated.
        if workshop.workshop_number > 0:
            prev = workshop.assessment.ebios_workshops.filter(
                workshop_number=workshop.workshop_number - 1,
                iteration_type=workshop.iteration_type,
                iteration_number=workshop.iteration_number,
            ).first()
            if prev and prev.status != EbiosWorkshopStatus.VALIDATED:
                return [
                    _("Workshop %(num)d must be validated before workshop %(next)d can start.")
                    % {"num": prev.workshop_number, "next": workshop.workshop_number}
                ]
        return []


class WorkshopSubmitView(_WorkshopTransitionView):
    """Move a workshop from in_progress to under_review."""

    target_status = EbiosWorkshopStatus.UNDER_REVIEW

    def _check_preconditions(self, workshop):
        if workshop.status != EbiosWorkshopStatus.IN_PROGRESS:
            return [_("Only in-progress workshops can be submitted for review.")]
        return []


class WorkshopValidateView(_WorkshopTransitionView):
    permission_required = "risks.ebios_assessment.validate"
    target_status = EbiosWorkshopStatus.VALIDATED

    def _check_preconditions(self, workshop):
        if workshop.status not in (
            EbiosWorkshopStatus.IN_PROGRESS,
            EbiosWorkshopStatus.UNDER_REVIEW,
        ):
            return [_("Only in-progress or under-review workshops can be validated.")]
        return []


class WorkshopRejectView(_WorkshopTransitionView):
    permission_required = "risks.ebios_assessment.validate"
    target_status = EbiosWorkshopStatus.REJECTED

    def _check_preconditions(self, workshop):
        if workshop.status not in (
            EbiosWorkshopStatus.IN_PROGRESS,
            EbiosWorkshopStatus.UNDER_REVIEW,
        ):
            return [_("Only in-progress or under-review workshops can be rejected.")]
        return []

    def post(self, request, assessment_pk, workshop_pk):
        workshop = get_object_or_404(
            EbiosWorkshopProgress.objects.select_related("assessment"),
            pk=workshop_pk,
            assessment_id=assessment_pk,
        )
        errors = self._check_preconditions(workshop)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect(
                "risks:ebios-workshop-detail",
                assessment_pk=assessment_pk, workshop_pk=workshop_pk,
            )
        form = WorkshopRejectForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("A rejection reason is required."))
            return redirect(
                "risks:ebios-workshop-detail",
                assessment_pk=assessment_pk, workshop_pk=workshop_pk,
            )
        workshop.status = EbiosWorkshopStatus.REJECTED
        workshop.rejection_reason = form.cleaned_data["rejection_reason"]
        workshop.save()
        messages.success(request, _("Workshop rejected."))
        return redirect(
            "risks:ebios-workshop-detail",
            assessment_pk=assessment_pk, workshop_pk=workshop_pk,
        )


# ── Workshop detail (dispatcher) ──────────────────────────────


WORKSHOP_TEMPLATES = {
    EbiosWorkshopNumber.W0: "risks/ebios/workshop_w0.html",
    EbiosWorkshopNumber.W1: "risks/ebios/workshop_w1.html",
    EbiosWorkshopNumber.W2: "risks/ebios/workshop_w2.html",
    EbiosWorkshopNumber.W3: "risks/ebios/workshop_w3.html",
    EbiosWorkshopNumber.W4: "risks/ebios/workshop_w4.html",
    EbiosWorkshopNumber.W5: "risks/ebios/workshop_w5.html",
}


class WorkshopDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Dispatcher view picking the template per workshop_number.

    The detail page hosts the entity tables, forms and the workshop sidebar
    with status + CTA buttons (Start / Submit / Validate / Reject).
    """

    permission_required = "risks.ebios_assessment.read"
    model = EbiosWorkshopProgress
    context_object_name = "workshop"
    pk_url_kwarg = "workshop_pk"

    def get_queryset(self):
        return EbiosWorkshopProgress.objects.select_related(
            "assessment", "validated_by",
        ).filter(assessment_id=self.kwargs["assessment_pk"])

    def get_template_names(self):
        workshop = self.get_object()
        return [WORKSHOP_TEMPLATES.get(workshop.workshop_number, "risks/ebios/workshop_generic.html")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        workshop = ctx["workshop"]
        assessment = workshop.assessment
        ctx["assessment"] = assessment
        ctx["reject_form"] = WorkshopRejectForm()
        ctx.update(build_ebios_stepper_context(assessment, current_workshop=workshop))

        # Action eligibility flags consumed by the sidebar template
        ctx["can_start"] = workshop.status in (
            EbiosWorkshopStatus.NOT_STARTED, EbiosWorkshopStatus.REJECTED,
        )
        ctx["can_submit"] = workshop.status == EbiosWorkshopStatus.IN_PROGRESS
        ctx["can_validate"] = workshop.status in (
            EbiosWorkshopStatus.IN_PROGRESS, EbiosWorkshopStatus.UNDER_REVIEW,
        )
        ctx["can_reject"] = workshop.status in (
            EbiosWorkshopStatus.IN_PROGRESS, EbiosWorkshopStatus.UNDER_REVIEW,
        )

        # Per-workshop entity context
        if workshop.workshop_number == EbiosWorkshopNumber.W0:
            ctx["study_framework"] = assessment.ebios_study_framework
        elif workshop.workshop_number == EbiosWorkshopNumber.W1:
            baseline = assessment.ebios_security_baseline
            ctx["baseline"] = baseline
            ctx["feared_events"] = baseline.feared_events.select_related("essential_asset").all()
            ctx["baseline_gaps"] = baseline.gaps.select_related("linked_requirement").all()
        elif workshop.workshop_number == EbiosWorkshopNumber.W2:
            ctx["risk_sources"] = assessment.ebios_risk_sources.prefetch_related(
                "targeted_objectives",
            ).all()
            ctx["sr_ov_pairs"] = assessment.ebios_sr_ov_pairs.select_related(
                "risk_source", "targeted_objective",
            ).all()
        elif workshop.workshop_number == EbiosWorkshopNumber.W3:
            ctx["ecosystem_stakeholders"] = assessment.ebios_ecosystem_stakeholders.all()
            ctx["strategic_scenarios"] = assessment.ebios_strategic_scenarios.select_related(
                "sr_ov_pair", "consolidated_risk",
            ).prefetch_related("attack_path_steps").all()
        elif workshop.workshop_number == EbiosWorkshopNumber.W4:
            ctx["operational_scenarios"] = assessment.ebios_operational_scenarios.select_related(
                "strategic_scenario", "consolidated_risk",
            ).prefetch_related("attack_techniques__mitre_technique").all()
        elif workshop.workshop_number == EbiosWorkshopNumber.W5:
            summary = assessment.ebios_summary
            ctx["summary"] = summary
            ctx["pacs_measures"] = summary.pacs_measures.select_related("owner").all()
        return ctx


# ── Study framework (W0) edit ────────────────────────────────


class StudyFrameworkUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_assessment.update"
    model = StudyFramework
    form_class = StudyFrameworkForm
    template_name = "risks/ebios/study_framework_form.html"

    def get_success_url(self):
        workshop = self.object.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W0,
        ).first()
        if workshop:
            return reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": self.object.assessment_id, "workshop_pk": workshop.pk},
            )
        return reverse("risks:assessment-detail", kwargs={"pk": self.object.assessment_id})


# ── Security baseline (W1) edit + inline feared events / gaps ─


class SecurityBaselineUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, HtmxFormMixin, UpdateView,
):
    permission_required = "risks.ebios_baseline.update"
    model = SecurityBaseline
    form_class = SecurityBaselineForm
    template_name = "risks/ebios/security_baseline_form.html"

    def get_success_url(self):
        workshop = self.object.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        if workshop:
            return reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": self.object.assessment_id, "workshop_pk": workshop.pk},
            )
        return reverse("risks:assessment-detail", kwargs={"pk": self.object.assessment_id})


class FearedEventCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Inline create of a FearedEvent under a given SecurityBaseline."""

    permission_required = "risks.ebios_baseline.create"

    def get(self, request, baseline_pk):
        from django.shortcuts import render
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = FearedEventForm()
        return render(
            request,
            "risks/ebios/feared_event_form.html",
            {"form": form, "baseline": baseline, "feared_event": None},
        )

    def post(self, request, baseline_pk):
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = FearedEventForm(request.POST)
        if not form.is_valid():
            from django.shortcuts import render
            return render(
                request,
                "risks/ebios/feared_event_form.html",
                {"form": form, "baseline": baseline, "feared_event": None},
                status=400,
            )
        feared = form.save(commit=False)
        feared.baseline = baseline
        feared.created_by = request.user
        feared.save()
        workshop = baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return HttpResponseRedirect(
            reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": baseline.assessment_id, "workshop_pk": workshop.pk},
            )
        )


class FearedEventUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_baseline.update"
    model = FearedEvent
    form_class = FearedEventForm
    template_name = "risks/ebios/feared_event_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["baseline"] = self.object.baseline
        ctx["feared_event"] = self.object
        return ctx

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


class FearedEventDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_baseline.delete"
    model = FearedEvent
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


class BaselineGapCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_baseline.create"

    def get(self, request, baseline_pk):
        from django.shortcuts import render
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = BaselineGapForm()
        return render(
            request,
            "risks/ebios/baseline_gap_form.html",
            {"form": form, "baseline": baseline, "gap": None},
        )

    def post(self, request, baseline_pk):
        baseline = get_object_or_404(SecurityBaseline, pk=baseline_pk)
        form = BaselineGapForm(request.POST)
        if not form.is_valid():
            from django.shortcuts import render
            return render(
                request,
                "risks/ebios/baseline_gap_form.html",
                {"form": form, "baseline": baseline, "gap": None},
                status=400,
            )
        gap = form.save(commit=False)
        gap.baseline = baseline
        gap.created_by = request.user
        gap.save()
        workshop = baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return HttpResponseRedirect(
            reverse(
                "risks:ebios-workshop-detail",
                kwargs={"assessment_pk": baseline.assessment_id, "workshop_pk": workshop.pk},
            )
        )


class BaselineGapUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_baseline.update"
    model = BaselineGap
    form_class = BaselineGapForm
    template_name = "risks/ebios/baseline_gap_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["baseline"] = self.object.baseline
        ctx["gap"] = self.object
        return ctx

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


class BaselineGapDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_baseline.delete"
    model = BaselineGap
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        workshop = self.object.baseline.assessment.ebios_workshops.filter(
            workshop_number=EbiosWorkshopNumber.W1,
        ).first()
        return reverse(
            "risks:ebios-workshop-detail",
            kwargs={
                "assessment_pk": self.object.baseline.assessment_id,
                "workshop_pk": workshop.pk,
            },
        )


# ── Workshop redirect helpers ─────────────────────────────────


def _redirect_to_workshop(assessment, workshop_number):
    """Return a HttpResponseRedirect to the assessment's workshop detail page."""
    workshop = assessment.ebios_workshops.filter(
        workshop_number=workshop_number,
        iteration_type=EbiosIterationType.STRATEGIC,
    ).order_by("-iteration_number").first()
    return HttpResponseRedirect(reverse(
        "risks:ebios-workshop-detail",
        kwargs={"assessment_pk": assessment.pk, "workshop_pk": workshop.pk},
    ))


# ── Workshop W2 views ────────────────────────────────────────


class RiskSourceCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_risk_source.create"

    def get(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        return render(request, "risks/ebios/risk_source_form.html", {
            "form": RiskSourceForm(), "assessment": assessment, "risk_source": None,
        })

    def post(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = RiskSourceForm(request.POST)
        if not form.is_valid():
            return render(request, "risks/ebios/risk_source_form.html", {
                "form": form, "assessment": assessment, "risk_source": None,
            }, status=400)
        rs = form.save(commit=False)
        rs.assessment = assessment
        rs.created_by = request.user
        rs.save()
        return _redirect_to_workshop(assessment, EbiosWorkshopNumber.W2)


class RiskSourceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_risk_source.update"
    model = RiskSource
    form_class = RiskSourceForm
    template_name = "risks/ebios/risk_source_form.html"
    context_object_name = "risk_source"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.object.assessment
        return ctx

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W2).url


class RiskSourceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_risk_source.delete"
    model = RiskSource
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W2).url


class TargetedObjectiveCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_risk_source.create"

    def get(self, request, risk_source_pk):
        from django.shortcuts import render
        risk_source = get_object_or_404(RiskSource, pk=risk_source_pk)
        return render(request, "risks/ebios/targeted_objective_form.html", {
            "form": TargetedObjectiveForm(), "risk_source": risk_source, "objective": None,
        })

    def post(self, request, risk_source_pk):
        from django.shortcuts import render
        risk_source = get_object_or_404(RiskSource, pk=risk_source_pk)
        form = TargetedObjectiveForm(request.POST)
        if not form.is_valid():
            return render(request, "risks/ebios/targeted_objective_form.html", {
                "form": form, "risk_source": risk_source, "objective": None,
            }, status=400)
        obj = form.save(commit=False)
        obj.risk_source = risk_source
        obj.created_by = request.user
        obj.save()
        form.save_m2m()
        return _redirect_to_workshop(risk_source.assessment, EbiosWorkshopNumber.W2)


class TargetedObjectiveUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_risk_source.update"
    model = TargetedObjective
    form_class = TargetedObjectiveForm
    template_name = "risks/ebios/targeted_objective_form.html"
    context_object_name = "objective"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["risk_source"] = self.object.risk_source
        return ctx

    def get_success_url(self):
        return _redirect_to_workshop(self.object.risk_source.assessment, EbiosWorkshopNumber.W2).url


class TargetedObjectiveDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_risk_source.delete"
    model = TargetedObjective
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.risk_source.assessment, EbiosWorkshopNumber.W2).url


class SrOvPairCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_risk_source.create"

    def get(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = RiskSourceObjectivePairForm()
        # Filter the SR and OV dropdowns to this assessment's retained entities
        form.fields["risk_source"].queryset = RiskSource.objects.filter(
            assessment=assessment, is_retained=True,
        )
        form.fields["targeted_objective"].queryset = TargetedObjective.objects.filter(
            risk_source__assessment=assessment, is_retained=True,
        )
        return render(request, "risks/ebios/sr_ov_pair_form.html", {
            "form": form, "assessment": assessment, "pair": None,
        })

    def post(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = RiskSourceObjectivePairForm(request.POST)
        form.fields["risk_source"].queryset = RiskSource.objects.filter(assessment=assessment)
        form.fields["targeted_objective"].queryset = TargetedObjective.objects.filter(
            risk_source__assessment=assessment,
        )
        if not form.is_valid():
            return render(request, "risks/ebios/sr_ov_pair_form.html", {
                "form": form, "assessment": assessment, "pair": None,
            }, status=400)
        pair = form.save(commit=False)
        pair.assessment = assessment
        pair.created_by = request.user
        pair.save()
        return _redirect_to_workshop(assessment, EbiosWorkshopNumber.W2)


class SrOvPairUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_risk_source.update"
    model = RiskSourceObjectivePair
    form_class = RiskSourceObjectivePairForm
    template_name = "risks/ebios/sr_ov_pair_form.html"
    context_object_name = "pair"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.object.assessment
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["risk_source"].queryset = RiskSource.objects.filter(
            assessment=self.object.assessment,
        )
        form.fields["targeted_objective"].queryset = TargetedObjective.objects.filter(
            risk_source__assessment=self.object.assessment,
        )
        return form

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W2).url


class SrOvPairDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_risk_source.delete"
    model = RiskSourceObjectivePair
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W2).url


# ── Workshop W3 views ────────────────────────────────────────


class EcosystemStakeholderCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_ecosystem.create"

    def get(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        return render(request, "risks/ebios/ecosystem_form.html", {
            "form": EcosystemStakeholderForm(), "assessment": assessment, "stakeholder": None,
        })

    def post(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = EcosystemStakeholderForm(request.POST)
        if not form.is_valid():
            return render(request, "risks/ebios/ecosystem_form.html", {
                "form": form, "assessment": assessment, "stakeholder": None,
            }, status=400)
        s = form.save(commit=False)
        s.assessment = assessment
        s.created_by = request.user
        s.save()
        form.save_m2m()
        return _redirect_to_workshop(assessment, EbiosWorkshopNumber.W3)


class EcosystemStakeholderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_ecosystem.update"
    model = EcosystemStakeholder
    form_class = EcosystemStakeholderForm
    template_name = "risks/ebios/ecosystem_form.html"
    context_object_name = "stakeholder"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.object.assessment
        return ctx

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W3).url


class EcosystemStakeholderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_ecosystem.delete"
    model = EcosystemStakeholder
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W3).url


class StrategicScenarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_strategic.create"

    def get(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = StrategicScenarioForm()
        form.fields["sr_ov_pair"].queryset = RiskSourceObjectivePair.objects.filter(
            assessment=assessment, is_retained=True,
        )
        form.fields["targeted_feared_events"].queryset = FearedEvent.objects.filter(
            baseline__assessment=assessment,
        )
        return render(request, "risks/ebios/strategic_scenario_form.html", {
            "form": form, "assessment": assessment, "scenario": None,
        })

    def post(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = StrategicScenarioForm(request.POST)
        form.fields["sr_ov_pair"].queryset = RiskSourceObjectivePair.objects.filter(
            assessment=assessment,
        )
        form.fields["targeted_feared_events"].queryset = FearedEvent.objects.filter(
            baseline__assessment=assessment,
        )
        if not form.is_valid():
            return render(request, "risks/ebios/strategic_scenario_form.html", {
                "form": form, "assessment": assessment, "scenario": None,
            }, status=400)
        scenario = form.save(commit=False)
        scenario.assessment = assessment
        scenario.created_by = request.user
        scenario.save()
        form.save_m2m()
        return _redirect_to_workshop(assessment, EbiosWorkshopNumber.W3)


class StrategicScenarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_strategic.update"
    model = StrategicScenario
    form_class = StrategicScenarioForm
    template_name = "risks/ebios/strategic_scenario_form.html"
    context_object_name = "scenario"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.object.assessment
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["sr_ov_pair"].queryset = RiskSourceObjectivePair.objects.filter(
            assessment=self.object.assessment,
        )
        form.fields["targeted_feared_events"].queryset = FearedEvent.objects.filter(
            baseline__assessment=self.object.assessment,
        )
        return form

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W3).url


class StrategicScenarioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_strategic.delete"
    model = StrategicScenario
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W3).url


class AttackPathStepCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_strategic.create"

    def get(self, request, scenario_pk):
        from django.shortcuts import render
        scenario = get_object_or_404(StrategicScenario, pk=scenario_pk)
        form = AttackPathStepForm()
        form.fields["stakeholder"].queryset = EcosystemStakeholder.objects.filter(
            assessment=scenario.assessment,
        )
        return render(request, "risks/ebios/attack_path_step_form.html", {
            "form": form, "scenario": scenario, "step": None,
        })

    def post(self, request, scenario_pk):
        from django.shortcuts import render
        scenario = get_object_or_404(StrategicScenario, pk=scenario_pk)
        form = AttackPathStepForm(request.POST)
        form.fields["stakeholder"].queryset = EcosystemStakeholder.objects.filter(
            assessment=scenario.assessment,
        )
        if not form.is_valid():
            return render(request, "risks/ebios/attack_path_step_form.html", {
                "form": form, "scenario": scenario, "step": None,
            }, status=400)
        step = form.save(commit=False)
        step.scenario = scenario
        step.created_by = request.user
        step.save()
        return _redirect_to_workshop(scenario.assessment, EbiosWorkshopNumber.W3)


class AttackPathStepUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_strategic.update"
    model = AttackPathStep
    form_class = AttackPathStepForm
    template_name = "risks/ebios/attack_path_step_form.html"
    context_object_name = "step"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scenario"] = self.object.scenario
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["stakeholder"].queryset = EcosystemStakeholder.objects.filter(
            assessment=self.object.scenario.assessment,
        )
        return form

    def get_success_url(self):
        return _redirect_to_workshop(self.object.scenario.assessment, EbiosWorkshopNumber.W3).url


class AttackPathStepDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_strategic.delete"
    model = AttackPathStep
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.scenario.assessment, EbiosWorkshopNumber.W3).url


# ── Workshop W4 views ────────────────────────────────────────


class OperationalScenarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_operational.create"

    def get(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = OperationalScenarioForm()
        form.fields["strategic_scenario"].queryset = StrategicScenario.objects.filter(
            assessment=assessment, is_retained=True,
        )
        return render(request, "risks/ebios/operational_scenario_form.html", {
            "form": form, "assessment": assessment, "scenario": None,
        })

    def post(self, request, assessment_pk):
        from django.shortcuts import render
        assessment = get_object_or_404(RiskAssessment, pk=assessment_pk)
        form = OperationalScenarioForm(request.POST)
        form.fields["strategic_scenario"].queryset = StrategicScenario.objects.filter(
            assessment=assessment,
        )
        if not form.is_valid():
            return render(request, "risks/ebios/operational_scenario_form.html", {
                "form": form, "assessment": assessment, "scenario": None,
            }, status=400)
        scenario = form.save(commit=False)
        scenario.assessment = assessment
        scenario.created_by = request.user
        scenario.save()
        form.save_m2m()
        return _redirect_to_workshop(assessment, EbiosWorkshopNumber.W4)


class OperationalScenarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_operational.update"
    model = OperationalScenario
    form_class = OperationalScenarioForm
    template_name = "risks/ebios/operational_scenario_form.html"
    context_object_name = "scenario"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.object.assessment
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["strategic_scenario"].queryset = StrategicScenario.objects.filter(
            assessment=self.object.assessment,
        )
        return form

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W4).url


class OperationalScenarioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_operational.delete"
    model = OperationalScenario
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W4).url


class OperationalScenarioConsolidateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Materialise an OperationalScenario into a Risk in the unified register."""

    permission_required = "risks.risk.create"

    def post(self, request, pk):
        scenario = get_object_or_404(OperationalScenario, pk=pk)
        if scenario.consolidated_risk_id:
            messages.info(
                request,
                _("This operational scenario is already consolidated as %(ref)s.")
                % {"ref": scenario.consolidated_risk.reference},
            )
            return _redirect_to_workshop(scenario.assessment, EbiosWorkshopNumber.W4)
        from risks.constants import RiskSourceType
        risk = Risk.objects.create(
            assessment=scenario.assessment,
            name=scenario.name,
            description=scenario.description,
            risk_source=RiskSourceType.EBIOS_OPERATIONAL,
            source_entity_id=scenario.pk,
            source_entity_type="risks.OperationalScenario",
            initial_likelihood=scenario.likelihood_v,
            initial_impact=scenario.gravity_level,
            current_likelihood=scenario.likelihood_v,
            current_impact=scenario.gravity_level,
            criteria_snapshot=scenario.criteria_snapshot,
            created_by=request.user,
        )
        risk.affected_support_assets.set(scenario.targeted_support_assets.all())
        scenario.consolidated_risk = risk
        scenario.save(update_fields=["consolidated_risk"])
        messages.success(
            request,
            _("Operational scenario consolidated as risk %(ref)s.") % {"ref": risk.reference},
        )
        return _redirect_to_workshop(scenario.assessment, EbiosWorkshopNumber.W4)


class AttackTechniqueCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_operational.create"

    def get(self, request, scenario_pk):
        from django.shortcuts import render
        scenario = get_object_or_404(OperationalScenario, pk=scenario_pk)
        form = AttackTechniqueForm()
        return render(request, "risks/ebios/attack_technique_form.html", {
            "form": form, "scenario": scenario, "technique": None,
        })

    def post(self, request, scenario_pk):
        from django.shortcuts import render
        scenario = get_object_or_404(OperationalScenario, pk=scenario_pk)
        form = AttackTechniqueForm(request.POST)
        if not form.is_valid():
            return render(request, "risks/ebios/attack_technique_form.html", {
                "form": form, "scenario": scenario, "technique": None,
            }, status=400)
        technique = form.save(commit=False)
        technique.scenario = scenario
        technique.created_by = request.user
        try:
            technique.full_clean()
        except Exception as exc:
            form.add_error(None, exc)
            return render(request, "risks/ebios/attack_technique_form.html", {
                "form": form, "scenario": scenario, "technique": None,
            }, status=400)
        technique.save()
        return _redirect_to_workshop(scenario.assessment, EbiosWorkshopNumber.W4)


class AttackTechniqueUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_operational.update"
    model = AttackTechnique
    form_class = AttackTechniqueForm
    template_name = "risks/ebios/attack_technique_form.html"
    context_object_name = "technique"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["scenario"] = self.object.scenario
        return ctx

    def get_success_url(self):
        return _redirect_to_workshop(self.object.scenario.assessment, EbiosWorkshopNumber.W4).url


class AttackTechniqueDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_operational.delete"
    model = AttackTechnique
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.scenario.assessment, EbiosWorkshopNumber.W4).url


# ── Workshop W5 views ────────────────────────────────────────


class EbiosSummaryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_summary.update"
    model = EbiosSummary
    form_class = EbiosSummaryForm
    template_name = "risks/ebios/ebios_summary_form.html"
    context_object_name = "summary"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.assessment, EbiosWorkshopNumber.W5).url


class EbiosSummaryCaptureMappingsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Capture the before/after risk mapping snapshots from the W5 page.

    POST body fields: `slot` ∈ {"before", "after", "both"}.
    """

    permission_required = "risks.ebios_summary.update"

    def post(self, request, pk):
        summary = get_object_or_404(EbiosSummary, pk=pk)
        slot = request.POST.get("slot", "both")
        capture_before = slot in ("before", "both")
        capture_after = slot in ("after", "both")
        summary.capture_risk_mappings(
            capture_before=capture_before, capture_after=capture_after,
        )
        messages.success(request, _("Risk mapping snapshot captured."))
        return _redirect_to_workshop(summary.assessment, EbiosWorkshopNumber.W5)


class PACSMeasureCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "risks.ebios_summary.create"

    def get(self, request, summary_pk):
        from django.shortcuts import render
        summary = get_object_or_404(EbiosSummary, pk=summary_pk)
        return render(request, "risks/ebios/pacs_measure_form.html", {
            "form": PACSMeasureForm(), "summary": summary, "measure": None,
        })

    def post(self, request, summary_pk):
        from django.shortcuts import render
        summary = get_object_or_404(EbiosSummary, pk=summary_pk)
        form = PACSMeasureForm(request.POST)
        if not form.is_valid():
            return render(request, "risks/ebios/pacs_measure_form.html", {
                "form": form, "summary": summary, "measure": None,
            }, status=400)
        measure = form.save(commit=False)
        measure.summary = summary
        measure.created_by = request.user
        measure.save()
        form.save_m2m()
        return _redirect_to_workshop(summary.assessment, EbiosWorkshopNumber.W5)


class PACSMeasureUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "risks.ebios_summary.update"
    model = PACSMeasure
    form_class = PACSMeasureForm
    template_name = "risks/ebios/pacs_measure_form.html"
    context_object_name = "measure"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["summary"] = self.object.summary
        return ctx

    def get_success_url(self):
        return _redirect_to_workshop(self.object.summary.assessment, EbiosWorkshopNumber.W5).url


class PACSMeasureDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "risks.ebios_summary.delete"
    model = PACSMeasure
    template_name = "risks/ebios/confirm_delete.html"

    def get_success_url(self):
        return _redirect_to_workshop(self.object.summary.assessment, EbiosWorkshopNumber.W5).url
