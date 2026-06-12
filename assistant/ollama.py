"""Minimal HTTP client for the optional Ollama sidecar.

The assistant only needs two operations: a chat completion constrained to a
JSON Schema (Ollama grammar-constrained decoding via the ``format`` field) for
tool routing, and a plain-text chat completion for the final summary sentence.
"""

import json
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class AssistantError(Exception):
    """Base class for assistant failures."""


class AssistantDisabled(AssistantError):
    """The AI assistant feature flag is off."""


class OllamaUnreachable(AssistantError):
    """The Ollama sidecar cannot be reached or returned a server error."""


class ModelNotAvailable(AssistantError):
    """The configured model is not pulled on the Ollama instance."""


class MalformedModelOutput(AssistantError):
    """The model returned content that does not parse as expected."""


class OllamaClient:
    def __init__(self, base_url=None, model=None):
        self.base_url = (base_url or settings.AI_ASSISTANT_OLLAMA_URL).rstrip("/")
        self.model = model or settings.AI_ASSISTANT_MODEL
        self.timeout = httpx.Timeout(
            settings.AI_ASSISTANT_TIMEOUT,
            connect=settings.AI_ASSISTANT_CONNECT_TIMEOUT,
        )

    def _post_chat(self, payload):
        try:
            return httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise OllamaUnreachable(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise OllamaUnreachable(str(exc)) from exc

    def _chat(self, messages, fmt=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            # "think" disables chain-of-thought on thinking models (qwen3...):
            # routing latency matters more than reasoning depth here.
            "think": False,
            "options": {"temperature": 0, "num_ctx": settings.AI_ASSISTANT_NUM_CTX},
            "keep_alive": "30m",
        }
        if fmt is not None:
            payload["format"] = fmt
        resp = self._post_chat(payload)
        if resp.status_code == 400 and "think" in resp.text:
            # Older Ollama versions / non-thinking models reject the flag.
            payload.pop("think", None)
            resp = self._post_chat(payload)
        if resp.status_code == 404:
            raise ModelNotAvailable(self.model)
        if resp.status_code >= 400:
            raise OllamaUnreachable(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            content = resp.json()["message"]["content"]
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedModelOutput(resp.text[:200]) from exc
        return content or ""

    def chat_json(self, messages, json_schema):
        """Chat completion constrained to ``json_schema``; returns the parsed object."""
        content = self._chat(messages, fmt=json_schema)
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise MalformedModelOutput(content[:200]) from exc
        if not isinstance(parsed, dict):
            raise MalformedModelOutput(content[:200])
        return parsed

    def chat_text(self, messages):
        """Plain-text chat completion."""
        return self._chat(messages).strip()
