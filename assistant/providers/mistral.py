"""Mistral AI backend for the assistant (third-party, EU-hosted API).

Mistral exposes an OpenAI-compatible chat completions endpoint. The assistant
needs two operations: a chat completion constrained to a JSON Schema (via the
``response_format`` field) for tool routing, and a plain-text chat completion
for the final summary sentence.

Only the calling user's question and the compact, identifier-stripped record
fields produced by the read-only catalog tools leave the platform; ids and
UUIDs are scrubbed before the summary call (see ``engine._strip_identifiers``).
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


class MistralClient(BaseClient):
    def __init__(self, base_url=None, model=None, api_key=None):
        self.base_url = (base_url or settings.AI_ASSISTANT_BASE_URL).rstrip("/")
        self.model = model or settings.AI_ASSISTANT_MODEL
        self.api_key = api_key if api_key is not None else settings.AI_ASSISTANT_API_KEY
        self.timeout = httpx.Timeout(
            settings.AI_ASSISTANT_TIMEOUT,
            connect=settings.AI_ASSISTANT_CONNECT_TIMEOUT,
        )

    def _post_chat(self, payload):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            return httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ServiceUnreachable(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnreachable(str(exc)) from exc

    def _base_payload(self, messages):
        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "stream": False,
            "max_tokens": settings.AI_ASSISTANT_MAX_TOKENS,
        }

    def _raise_for_status(self, resp):
        if resp.status_code in (401, 403):
            # Never surface the key or auth detail to the caller.
            logger.error("Mistral authentication failed (HTTP %s)", resp.status_code)
            raise ServiceUnreachable("authentication failed")
        if resp.status_code == 404:
            raise ModelNotAvailable(self.model)
        if resp.status_code >= 400:
            raise ServiceUnreachable(f"HTTP {resp.status_code}: {resp.text[:200]}")

    def _content(self, resp):
        try:
            return resp.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise MalformedModelOutput(resp.text[:200]) from exc

    def chat_json(self, messages, json_schema, think=None):
        """Chat completion constrained to ``json_schema``; returns the parsed object.

        Uses Mistral custom structured output. The plan schema keeps a free-form
        ``arguments`` object, so strict mode (which requires fixed properties)
        is off; if the backend rejects the schema (HTTP 422), fall back to plain
        JSON mode. Server-side validation in the engine is the real safety net.
        """
        payload = self._base_payload(messages)
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "plan", "schema": json_schema, "strict": False},
        }
        resp = self._post_chat(payload)
        if resp.status_code == 422:
            payload["response_format"] = {"type": "json_object"}
            resp = self._post_chat(payload)
        self._raise_for_status(resp)
        content = self._content(resp)
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise MalformedModelOutput(content[:200]) from exc
        if not isinstance(parsed, dict):
            raise MalformedModelOutput(content[:200])
        return parsed

    def chat_text(self, messages):
        """Plain-text chat completion."""
        resp = self._post_chat(self._base_payload(messages))
        self._raise_for_status(resp)
        return self._content(resp).strip()

    def embed(self, texts):
        """Return one embedding vector per input string (Mistral embeddings API)."""
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": settings.AI_ASSISTANT_EMBED_MODEL, "input": list(texts)}
        try:
            resp = httpx.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ServiceUnreachable(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ServiceUnreachable(str(exc)) from exc
        self._raise_for_status(resp)
        try:
            rows = sorted(resp.json()["data"], key=lambda d: d.get("index", 0))
            return [row["embedding"] for row in rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedModelOutput(resp.text[:200]) from exc
