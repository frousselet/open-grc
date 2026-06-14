import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView

from assistant.engine import AssistantEngine
from assistant.models import AssistantFeedback
from assistant.providers import (
    AssistantDisabled,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)
from core.mixins import SortableListMixin

FEEDBACK_READ_PERM = "system.assistant_feedback.read"

QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500
COMMENT_MAX_LENGTH = 2000

# Key under which the last rendered answer is stashed in the session so that
# feedback is bound to the server-generated answer (faithful, not spoofable).
ANSWER_SESSION_KEY = "assistant_last_answer"

# Human-friendly names for the configured LLM backend, shown in the disclaimer.
PROVIDER_LABELS = {
    "mistral": "Mistral",
    "openai": "OpenAI",
    "openai-compatible": "OpenAI",
    "anthropic": "Claude",
    "claude": "Claude",
    "ollama": "Ollama",
}


def _powered_by():
    """Return the "<Provider> <model>" label for the active backend."""
    provider = (settings.AI_ASSISTANT_PROVIDER or "").lower()
    label = PROVIDER_LABELS.get(provider, provider.title() or "AI")
    return f"{label} {settings.AI_ASSISTANT_MODEL}"


def _stash_answer(request, outcome):
    """Store the answer in the session and return its feedback token.

    Only successful answers (a summary or at least one record card) are
    stashed; the token is rendered in the partial and posted back with the
    rating so the feedback row carries the exact server-generated response.
    """
    if not (outcome.summary or outcome.has_cards):
        request.session.pop(ANSWER_SESSION_KEY, None)
        return None
    token = uuid.uuid4().hex
    request.session[ANSWER_SESSION_KEY] = {
        "token": token,
        "question": outcome.question,
        "language": outcome.language,
        "summary": outcome.summary or "",
        "results": [
            {"tool": run.tool, "label": str(run.label), "records": run.cards}
            for run in outcome.tool_runs
            if not run.error
        ],
        "degraded": outcome.degraded,
        "refused_tools": [str(t) for t in outcome.refused_tools],
        "provider": settings.AI_ASSISTANT_PROVIDER,
        "model_name": settings.AI_ASSISTANT_MODEL,
    }
    return token


class AskAssistantView(LoginRequiredMixin, View):
    """Answer a natural-language question with the palette HTML partial.

    Always returns 200 with the partial; error states are rendered inside it
    so the palette JavaScript keeps a single happy path.
    """

    http_method_names = ["post"]

    def post(self, request):
        question = (request.POST.get("q") or "").strip()
        context = {
            "model_name": settings.AI_ASSISTANT_MODEL,
            "powered_by": _powered_by(),
        }
        if not (QUESTION_MIN_LENGTH <= len(question) <= QUESTION_MAX_LENGTH):
            context["error_code"] = "invalid"
            return render(request, "assistant/_answer.html", context)
        engine = AssistantEngine(
            request.user,
            language=getattr(request, "LANGUAGE_CODE", "en"),
        )
        try:
            outcome = engine.ask(question)
            context["outcome"] = outcome
            context["feedback_token"] = _stash_answer(request, outcome)
        except AssistantDisabled:
            context["error_code"] = "disabled"
        except ModelNotAvailable:
            context["error_code"] = "model_missing"
        except ServiceUnreachable:
            context["error_code"] = "unreachable"
        except MalformedModelOutput:
            context["error_code"] = "model_error"
        return render(request, "assistant/_answer.html", context)


class AssistantFeedbackView(LoginRequiredMixin, View):
    """Record thumbs up/down (and an optional comment) on the last answer.

    The answer content is read from the session (stashed by AskAssistantView),
    not from the client, so the stored feedback faithfully reflects what the
    LLM produced. Returns a small confirmation partial.
    """

    http_method_names = ["post"]

    def post(self, request):
        token = (request.POST.get("answer_id") or "").strip()
        rating = (request.POST.get("rating") or "").strip()
        comment = (request.POST.get("comment") or "").strip()[:COMMENT_MAX_LENGTH]
        stashed = request.session.get(ANSWER_SESSION_KEY)
        valid = (
            rating in (AssistantFeedback.RATING_UP, AssistantFeedback.RATING_DOWN)
            and stashed
            and stashed.get("token") == token
        )
        if not valid:
            return render(request, "assistant/_feedback_done.html", {"error": True})
        AssistantFeedback.objects.create(
            user=request.user,
            question=stashed["question"],
            language=stashed.get("language", ""),
            rating=rating,
            comment=comment,
            summary=stashed.get("summary", ""),
            results=stashed.get("results", []),
            degraded=stashed.get("degraded", False),
            refused_tools=stashed.get("refused_tools", []),
            provider=stashed.get("provider", ""),
            model_name=stashed.get("model_name", ""),
        )
        # One feedback per answer: drop the stash to block double submission.
        request.session.pop(ANSWER_SESSION_KEY, None)
        return render(request, "assistant/_feedback_done.html", {"error": False})


def _filtered_feedback(request):
    """Apply the shared admin-list filters (status, rating, language, search, period).

    ``status`` defaults to "open": corrected feedback is hidden, so the list
    focuses on actionable items and the Export button (which mirrors this
    filter) excludes corrected feedback by default. ``resolved`` shows only
    corrected, ``all`` shows everything.
    """
    qs = AssistantFeedback.objects.select_related("user", "resolved_by")
    status = request.GET.get("status") or "open"
    rating = request.GET.get("rating")
    language = request.GET.get("language")
    search = request.GET.get("q")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if status == "open":
        qs = qs.filter(is_resolved=False)
    elif status == "resolved":
        qs = qs.filter(is_resolved=True)
    if rating in (AssistantFeedback.RATING_UP, AssistantFeedback.RATING_DOWN):
        qs = qs.filter(rating=rating)
    if language:
        qs = qs.filter(language=language)
    if search:
        qs = qs.filter(
            Q(question__icontains=search)
            | Q(comment__icontains=search)
            | Q(summary__icontains=search)
        )
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


class AssistantFeedbackListView(
    LoginRequiredMixin, PermissionRequiredMixin, SortableListMixin, ListView
):
    """In-app Administration page listing Ask Cairn answer feedback."""

    model = AssistantFeedback
    template_name = "assistant/feedback_list.html"
    context_object_name = "feedbacks"
    paginate_by = 50
    permission_required = FEEDBACK_READ_PERM
    sortable_fields = {"date": "created_at", "rating": "rating", "language": "language"}
    default_sort = "date"
    default_sort_order = "desc"

    def get_queryset(self):
        return self._apply_sorting(_filtered_feedback(self.request))


class AssistantFeedbackExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Download the (filtered) feedback set as structured JSON for an LLM."""

    permission_required = FEEDBACK_READ_PERM
    http_method_names = ["get"]

    def get(self, request):
        feedback = [
            fb.as_export_dict()
            for fb in _filtered_feedback(request).order_by("-created_at")
        ]
        response = JsonResponse(
            {"count": len(feedback), "feedback": feedback},
            json_dumps_params={"ensure_ascii": False, "indent": 2},
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="assistant_feedback.json"'
        return response


class AssistantFeedbackResolveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Mark a feedback as corrected (or reopen it), excluding it from exports."""

    permission_required = FEEDBACK_READ_PERM
    http_method_names = ["post"]

    # Only these list filters are echoed back into the redirect; rebuilding the
    # query string from a whitelist keeps untrusted input out of the redirect
    # target (the host is always the fixed feedback-list path).
    FILTER_KEYS = ("status", "rating", "q", "date_from", "date_to")

    def post(self, request, pk):
        feedback = get_object_or_404(AssistantFeedback, pk=pk)
        if request.POST.get("action") == "reopen":
            feedback.mark_unresolved()
            messages.success(request, _("Feedback reopened."))
        else:
            feedback.mark_resolved(request.user)
            messages.success(request, _("Feedback marked as corrected."))
        return redirect(f"{reverse('assistant:feedback-list')}{self._safe_query(request)}")

    def _safe_query(self, request):
        posted = QueryDict(request.POST.get("next_qs", ""))
        clean = QueryDict(mutable=True)
        for key in self.FILTER_KEYS:
            value = posted.get(key)
            if value:
                clean[key] = value
        encoded = clean.urlencode()
        return f"?{encoded}" if encoded else ""


class RebuildSemanticIndexView(LoginRequiredMixin, View):
    """Trigger an on-demand background refresh of the requirement index.

    Lives on the Company settings page (in-app Administration), gated by the
    same permission as other system configuration changes. The rebuild runs in
    a guarded background thread so the request returns immediately.
    """

    http_method_names = ["post"]

    def post(self, request):
        if not (
            request.user.is_superuser
            or request.user.has_perm("system.config.update")
        ):
            messages.error(request, _("You do not have the required permissions."))
            return redirect("accounts:company-settings")
        if not settings.AI_ASSISTANT_SEMANTIC_ENABLED:
            messages.error(request, _("Semantic search is disabled."))
            return redirect("accounts:company-settings")

        from assistant.semantic import rebuild_index_async

        if rebuild_index_async():
            messages.success(
                request,
                _("The semantic index update has started; it runs in the background."),
            )
        else:
            messages.info(request, _("A semantic index update is already running."))
        return redirect("accounts:company-settings")
