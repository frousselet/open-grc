"""Provider-neutral contract for the Ask Cairn assistant backend.

The assistant only needs two operations from any LLM backend: a chat
completion constrained to a JSON Schema (for tool routing) and a plain-text
chat completion (for the final summary sentence). The engine depends only on
this small surface, so the concrete backend is selected at runtime from
``settings.AI_ASSISTANT_PROVIDER`` without the engine knowing which one runs.
"""

from django.conf import settings


class AssistantError(Exception):
    """Base class for assistant failures."""


class AssistantDisabled(AssistantError):
    """The AI assistant feature flag is off."""


class ServiceUnreachable(AssistantError):
    """The LLM backend cannot be reached or returned a server error."""


class ModelNotAvailable(AssistantError):
    """The configured model is unknown to the backend."""


class MalformedModelOutput(AssistantError):
    """The model returned content that does not parse as expected."""


class BaseClient:
    """Interface every provider client implements.

    ``chat_json(messages, json_schema)`` returns the parsed object the model
    produced under the schema constraint; ``chat_text(messages)`` returns a
    plain string. Implementations raise the exceptions above on failure.
    """

    def chat_json(self, messages, json_schema, think=None):  # pragma: no cover
        raise NotImplementedError

    def chat_text(self, messages):  # pragma: no cover
        raise NotImplementedError

    def embed(self, texts):  # pragma: no cover
        """Return one embedding vector (list[float]) per input string."""
        raise NotImplementedError


def get_client():
    """Return the configured provider client.

    ``mistral`` (third-party API) is the default; ``ollama`` (self-hosted
    local LLM) remains selectable for those who point it at their own
    instance.
    """
    provider = (settings.AI_ASSISTANT_PROVIDER or "mistral").lower()
    if provider == "ollama":
        from assistant.providers.ollama import OllamaClient

        return OllamaClient()
    if provider == "mistral":
        from assistant.providers.mistral import MistralClient

        return MistralClient()
    raise ServiceUnreachable(f"Unknown AI assistant provider: {provider!r}")
