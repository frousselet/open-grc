"""Views for the persistent management review workflow (ISO 27001:2022 9.3).

Kept in a dedicated module to avoid bloating reports/views.py.
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.mixins import WorkflowStepperMixin
from accounts.views import PermissionRequiredMixin
from core.mixins import SortableListMixin
from compliance.constants import ActionPlanStatus
from compliance.models import ComplianceActionPlan

from .constants import (
    MANAGEMENT_REVIEW_CANCELLABLE_STATUSES,
    MANAGEMENT_REVIEW_TRANSITIONS,
    ManagementReviewStatus,
)
from .forms import (
    DecisionPromoteForm,
    IsmsChangeForm,
    ManagementReviewCommentForm,
    ManagementReviewDecisionForm,
    ManagementReviewModelForm,
    ManagementReviewTransitionForm,
    ParticipantFormSet,
    ParticipantSignatureForm,
)
from .management_review import (
    gather_management_review_data,
    generate_management_review_docx,
    generate_management_review_pptx,
)
from .models import (
    IsmsChange,
    ManagementReview,
    ManagementReviewComment,
    ManagementReviewDecision,
    ManagementReviewParticipant,
)


log = logging.getLogger(__name__)


# ─── List ─────────────────────────────────────────────────────────────

class ManagementReviewListView(
    LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView,
):
    permission_required = "reports.management_review.read"
    model = ManagementReview
    template_name = "reports/management_review_list.html"
    context_object_name = "reviews"
    paginate_by = 25
    sortable_fields = {
        "reference": "reference",
        "title": "title",
        "status": "status",
        "planned_date": "planned_date",
        "period_end": "period_end",
        "facilitator": "facilitator__last_name",
    }
    default_sort = "planned_date"
    default_sort_order = "desc"

    def get_queryset(self):
        qs = super().get_queryset().select_related("facilitator", "approver")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(reference__icontains=q)
                | Q(description__icontains=q),
            )
        if status:
            qs = qs.filter(status=status)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["statuses"] = ManagementReviewStatus.choices
        return ctx


# ─── Detail with stepper and all sections ─────────────────────────────

class ManagementReviewDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, WorkflowStepperMixin, DetailView,
):
    permission_required = "reports.management_review.read"
    workflow_transition_url_name = "reports:management-review-transition"
    model = ManagementReview
    template_name = "reports/management_review_detail.html"
    context_object_name = "review"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        review = self.object
        user = self.request.user


        # Closure blockers (if status == held)
        if review.status == ManagementReviewStatus.HELD:
            ok, reasons = review.can_close()
            ctx["closure_ready"] = ok
            ctx["closure_blockers"] = reasons
        else:
            ctx["closure_ready"] = False
            ctx["closure_blockers"] = []

        # Aggregated data (live or snapshot)
        if review.has_snapshot:
            ctx["review_data"] = review.snapshot_data
            ctx["data_source"] = "snapshot"
        else:
            scope_ids = list(review.scopes.values_list("id", flat=True))
            try:
                ctx["review_data"] = gather_management_review_data(
                    user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                )
            except Exception:
                log.exception("Failed to gather live review data")
                ctx["review_data"] = None
            ctx["data_source"] = "live"

        ctx["participants"] = list(
            review.participants.select_related("user").all()
        )
        ctx["decisions"] = list(
            review.decisions.select_related("owner").all()
        )
        ctx["isms_changes"] = list(
            review.isms_changes.select_related("owner").all()
        )
        ctx["comments"] = list(
            review.comments.select_related("author").order_by("-created_at")[:50]
        )
        ctx["comment_form"] = ManagementReviewCommentForm()
        ctx["transitions"] = list(
            review.transitions.select_related("performed_by").all()[:30]
        )

        return ctx


# ─── Create / Update / Delete ─────────────────────────────────────────

class ManagementReviewCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView,
):
    permission_required = "reports.management_review.create"
    form_class = ManagementReviewModelForm
    template_name = "reports/management_review_persistent_form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _("Management review created."))
        return response

    def get_success_url(self):
        return self.object.get_absolute_url() if hasattr(self.object, "get_absolute_url") else (
            f"/reports/management-reviews/{self.object.pk}/"
        )


class ManagementReviewUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView,
):
    permission_required = "reports.management_review.update"
    model = ManagementReview
    form_class = ManagementReviewModelForm
    template_name = "reports/management_review_persistent_form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            ctx["participant_formset"] = ParticipantFormSet(
                self.request.POST, instance=self.object,
            )
        else:
            ctx["participant_formset"] = ParticipantFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["participant_formset"]
        if not formset.is_valid():
            return self.form_invalid(form)
        response = super().form_valid(form)
        formset.instance = self.object
        formset.save()
        messages.success(self.request, _("Management review updated."))
        return response

    def get_success_url(self):
        return f"/reports/management-reviews/{self.object.pk}/"


class ManagementReviewDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView,
):
    permission_required = "reports.management_review.delete"
    model = ManagementReview
    success_url = reverse_lazy("reports:management-review-list")
    template_name = "reports/management_review_confirm_delete.html"


# ─── Transitions ──────────────────────────────────────────────────────

class ManagementReviewTransitionView(
    LoginRequiredMixin, PermissionRequiredMixin, View,
):
    permission_required = "reports.management_review.update"

    def post(self, request, pk):
        review = get_object_or_404(ManagementReview, pk=pk)
        form = ManagementReviewTransitionForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("Invalid transition request."))
            return redirect("reports:management-review-detail", pk=pk)

        target = form.cleaned_data["target_status"]
        comment = form.cleaned_data.get("comment", "")

        # Approve permission check for closure
        if (
            target == ManagementReviewStatus.CLOSED
            and not request.user.has_perm("reports.management_review.approve")
        ):
            messages.error(request, _("You are not allowed to close this review."))
            return redirect("reports:management-review-detail", pk=pk)

        try:
            review.transition_to(target, request.user, comment=comment)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("reports:management-review-detail", pk=pk)

        # Auto-snapshot on closure
        if review.status == ManagementReviewStatus.CLOSED:
            scope_ids = list(review.scopes.values_list("id", flat=True))
            try:
                data = gather_management_review_data(
                    request.user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                )
                # Minimal JSON-safe transform: drop non-serializable fields.
                snapshot = _serialize_snapshot(data)
                review.take_snapshot(snapshot)
            except Exception:
                log.exception("Snapshot generation failed on closure")

        if review.status == ManagementReviewStatus.CLOSED:
            if review.approver_id is None:
                review.approver = request.user
                review.approved_at = timezone.now()
                review.is_approved = True
                review.approved_by = request.user
                review.save(
                    update_fields=[
                        "approver", "approved_at", "is_approved",
                        "approved_by", "updated_at",
                    ],
                )

        messages.success(request, _("Status updated."))
        return redirect("reports:management-review-detail", pk=pk)


def _serialize_snapshot(data):
    """Return a JSON-serializable dict from the gather_* output."""
    import datetime

    def _ser(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: _ser(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_ser(v) for v in value]
        if hasattr(value, "pk"):
            # Model instance: store a display string
            return str(value)
        return value

    out = {}
    for k, v in data.items():
        if k in ("company", "generated_by"):
            out[k] = str(v) if v else ""
        else:
            out[k] = _ser(v)
    return out


# ─── Export ───────────────────────────────────────────────────────────

class ManagementReviewExportView(
    LoginRequiredMixin, PermissionRequiredMixin, View,
):
    permission_required = "reports.management_review.read"

    def get(self, request, pk, fmt):
        review = get_object_or_404(ManagementReview, pk=pk)
        scope_ids = list(review.scopes.values_list("id", flat=True))

        try:
            if fmt == "pptx":
                filename, data = generate_management_review_pptx(
                    request.user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                    review=review,
                )
                ctype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            elif fmt == "docx":
                filename, data = generate_management_review_docx(
                    request.user,
                    scope_ids=scope_ids,
                    period_start=review.period_start,
                    period_end=review.period_end,
                    review=review,
                )
                ctype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                raise Http404("Unsupported format")
        except Exception:
            log.exception("Management review export failed")
            messages.error(request, _("Export failed. Please try again."))
            return redirect("reports:management-review-detail", pk=pk)

        resp = HttpResponse(data, content_type=ctype)
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


# ─── Comments ─────────────────────────────────────────────────────────

class ManagementReviewCommentCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, View,
):
    permission_required = "reports.management_review.update"

    def post(self, request, pk):
        review = get_object_or_404(ManagementReview, pk=pk)
        form = ManagementReviewCommentForm(request.POST)
        if form.is_valid():
            ManagementReviewComment.objects.create(
                review=review,
                author=request.user,
                content=form.cleaned_data["content"],
            )
            messages.success(request, _("Comment added."))
        else:
            messages.error(request, _("Comment could not be added."))
        return redirect("reports:management-review-detail", pk=pk)


# ─── Decisions ────────────────────────────────────────────────────────

class DecisionCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, View,
):
    permission_required = "reports.management_review.update"

    def get(self, request, pk):
        review = get_object_or_404(ManagementReview, pk=pk)
        form = ManagementReviewDecisionForm()
        return render(request, "reports/decision_form.html", {
            "review": review, "form": form, "action": "create",
        })

    def post(self, request, pk):
        review = get_object_or_404(ManagementReview, pk=pk)
        form = ManagementReviewDecisionForm(request.POST)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.review = review
            decision.save()
            messages.success(request, _("Decision added."))
            return redirect("reports:management-review-detail", pk=review.pk)
        return render(request, "reports/decision_form.html", {
            "review": review, "form": form, "action": "create",
        })


class DecisionUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView,
):
    permission_required = "reports.management_review.update"
    model = ManagementReviewDecision
    form_class = ManagementReviewDecisionForm
    template_name = "reports/decision_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review"] = self.object.review
        ctx["action"] = "update"
        return ctx

    def get_success_url(self):
        return f"/reports/management-reviews/{self.object.review_id}/"


class DecisionDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView,
):
    permission_required = "reports.management_review.update"
    model = ManagementReviewDecision
    template_name = "reports/decision_confirm_delete.html"

    def get_success_url(self):
        return f"/reports/management-reviews/{self.object.review_id}/"


class DecisionPromoteView(
    LoginRequiredMixin, PermissionRequiredMixin, View,
):
    permission_required = "reports.management_review.update"

    def _check_perms(self, request):
        return request.user.has_perm("compliance.action_plan.create")

    def get(self, request, pk):
        if not self._check_perms(request):
            messages.error(request, _("You lack the action plan create permission."))
            return redirect("reports:decision-detail", pk=pk)
        decision = get_object_or_404(ManagementReviewDecision, pk=pk)
        form = DecisionPromoteForm(initial={
            "name": decision.title,
            "priority": decision.priority,
            "target_date": decision.due_date,
            "gap_description": decision.description,
            "remediation_plan": decision.rationale or decision.description,
            "owner": decision.owner_id,
        })
        return render(request, "reports/decision_promote_form.html", {
            "decision": decision, "form": form,
        })

    def post(self, request, pk):
        if not self._check_perms(request):
            messages.error(request, _("You lack the action plan create permission."))
            return redirect("reports:decision-detail", pk=pk)
        decision = get_object_or_404(ManagementReviewDecision, pk=pk)
        form = DecisionPromoteForm(request.POST)
        if not form.is_valid():
            return render(request, "reports/decision_promote_form.html", {
                "decision": decision, "form": form,
            })

        cd = form.cleaned_data
        plan = ComplianceActionPlan.objects.create(
            name=cd["name"],
            description=decision.description,
            gap_description=cd["gap_description"],
            remediation_plan=cd["remediation_plan"],
            priority=cd["priority"],
            owner=cd["owner"],
            target_date=cd["target_date"],
            status=ActionPlanStatus.NEW,
            originating_review=decision.review,
            created_by=request.user,
        )
        plan.scopes.set(decision.review.scopes.all())
        decision.linked_action_plan = plan
        if decision.status == "pending":
            decision.status = "in_progress"
        decision.save(update_fields=["linked_action_plan", "status", "updated_at"])
        messages.success(
            request,
            _("Action plan %(ref)s created from decision.") % {"ref": plan.reference},
        )
        return redirect("reports:management-review-detail", pk=decision.review_id)


class DecisionDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, DetailView,
):
    permission_required = "reports.management_review.read"
    model = ManagementReviewDecision
    template_name = "reports/decision_detail.html"
    context_object_name = "decision"


# ─── ISMS Changes ─────────────────────────────────────────────────────

class IsmsChangeCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, View,
):
    permission_required = "reports.management_review.update"

    def get(self, request, pk):
        review = get_object_or_404(ManagementReview, pk=pk)
        form = IsmsChangeForm()
        return render(request, "reports/isms_change_form.html", {
            "review": review, "form": form, "action": "create",
        })

    def post(self, request, pk):
        review = get_object_or_404(ManagementReview, pk=pk)
        form = IsmsChangeForm(request.POST)
        if form.is_valid():
            change = form.save(commit=False)
            change.review = review
            change.save()
            form.save_m2m()
            messages.success(request, _("ISMS change added."))
            return redirect("reports:management-review-detail", pk=review.pk)
        return render(request, "reports/isms_change_form.html", {
            "review": review, "form": form, "action": "create",
        })


class IsmsChangeUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView,
):
    permission_required = "reports.management_review.update"
    model = IsmsChange
    form_class = IsmsChangeForm
    template_name = "reports/isms_change_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review"] = self.object.review
        ctx["action"] = "update"
        return ctx

    def get_success_url(self):
        return f"/reports/management-reviews/{self.object.review_id}/"


class IsmsChangeDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView,
):
    permission_required = "reports.management_review.update"
    model = IsmsChange
    template_name = "reports/isms_change_confirm_delete.html"

    def get_success_url(self):
        return f"/reports/management-reviews/{self.object.review_id}/"


# ─── Participant signature ────────────────────────────────────────────


class ParticipantSignatureView(LoginRequiredMixin, View):
    """Upload a graphical signature for a participant.

    Non-eIDAS qualified; the image is stored as a base64 data URI in
    ManagementReviewParticipant.signature_data and embedded in the DOCX.
    Any authenticated user can sign their own participation slot; users
    with management_review.update permission can sign on behalf of others.
    """

    def _authorized(self, request, participant):
        if request.user.has_perm("reports.management_review.update"):
            return True
        # Owner signing their own slot
        return participant.user_id == request.user.pk

    def get(self, request, pk):
        participant = get_object_or_404(ManagementReviewParticipant, pk=pk)
        if not self._authorized(request, participant):
            messages.error(request, _("You cannot sign for this participant."))
            return redirect("reports:management-review-detail", pk=participant.review_id)
        form = ParticipantSignatureForm()
        return render(request, "reports/participant_signature_form.html", {
            "participant": participant, "form": form,
        })

    def post(self, request, pk):
        import base64 as _b64
        participant = get_object_or_404(ManagementReviewParticipant, pk=pk)
        if not self._authorized(request, participant):
            messages.error(request, _("You cannot sign for this participant."))
            return redirect("reports:management-review-detail", pk=participant.review_id)

        if request.POST.get("remove"):
            participant.signature_data = ""
            participant.save(update_fields=["signature_data"])
            messages.success(request, _("Signature removed."))
            return redirect("reports:management-review-detail", pk=participant.review_id)

        form = ParticipantSignatureForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "reports/participant_signature_form.html", {
                "participant": participant, "form": form,
            })

        image = form.cleaned_data["signature_image"]
        mime = image.content_type or "image/png"
        data = _b64.b64encode(image.read()).decode("ascii")
        participant.signature_data = f"data:{mime};base64,{data}"
        if not participant.attended:
            participant.attended = True
        participant.save(update_fields=["signature_data", "attended"])
        messages.success(request, _("Signature saved."))
        return redirect("reports:management-review-detail", pk=participant.review_id)

