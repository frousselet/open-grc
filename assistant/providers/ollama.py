"""Self-hosted Ollama backend for the assistant (optional, local LLM).

The local LLM is no longer shipped as a docker-compose sidecar, but this
client stays available for deployments that point ``AI_ASSISTANT_OLLAMA_URL``
at their own Ollama instance (``AI_ASSISTANT_PROVIDER=ollama``).

It needs two operations: a chat completion constrained to a JSON Schema
(Ollama grammar-constrained decoding via the ``format`` field) for tool
routing, and a plain-text chat completion for the final summary sentence.
"""

import json
import logging

import httpx
from django.conf import settings

from assistant.providers.base import (
    BaseClient,
    MalformedModelOutput,
    ModelNotAvailable,
    ServiceUnreachable,
)

logger = logging.getLogger(__name__)


class OllamaClient(BaseClient):
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
            raise ServiceUnreachable(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnreachable(str(exc)) from exc

    def _chat(self, messages, fmt=None, think=False):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            # Chain-of-thought on thinking models (qwen3...): required for
            # reliable multi-step routing, skipped for the summary sentence.
            "think": think,
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
            raise ServiceUnreachable(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            content = resp.json()["message"]["content"]
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedModelOutput(resp.text[:200]) from exc
        return content or ""

    def chat_json(self, messages, json_schema, think=None):
        """Chat completion constrained to ``json_schema``; returns the parsed object."""
        if think is None:
            think = settings.AI_ASSISTANT_ROUTING_THINK
        content = self._chat(messages, fmt=json_schema, think=think)
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

    def embed(self, texts):
        """Return one embedding vector per input string (Ollama embeddings API)."""
        if not texts:
            return []
        payload = {"model": settings.AI_ASSISTANT_EMBED_MODEL, "input": list(texts)}
        try:
            resp = httpx.post(
                f"{self.base_url}/api/embed", json=payload, timeout=self.timeout
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ServiceUnreachable(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnreachable(str(exc)) from exc
        if resp.status_code == 404:
            raise ModelNotAvailable(settings.AI_ASSISTANT_EMBED_MODEL)
        if resp.status_code >= 400:
            raise ServiceUnreachable(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            return list(resp.json()["embeddings"])
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedModelOutput(resp.text[:200]) from exc
