from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from assistant.engine import AssistantEngine
from assistant.providers import (
    AssistantDisabled,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)

QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500

# Human-friendly names for the configured LLM backend, shown in the disclaimer.
PROVIDER_LABELS = {"mistral": "Mistral", "ollama": "Ollama"}


def _powered_by():
    """Return the "<Provider> <model>" label for the active backend."""
    provider = (settings.AI_ASSISTANT_PROVIDER or "").lower()
    label = PROVIDER_LABELS.get(provider, provider.title() or "AI")
    return f"{label} {settings.AI_ASSISTANT_MODEL}"


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
            context["outcome"] = engine.ask(question)
        except AssistantDisabled:
            context["error_code"] = "disabled"
        except ModelNotAvailable:
            context["error_code"] = "model_missing"
        except ServiceUnreachable:
            context["error_code"] = "unreachable"
        except MalformedModelOutput:
            context["error_code"] = "model_error"
        return render(request, "assistant/_answer.html", context)
