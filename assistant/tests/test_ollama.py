"""Unit tests for the Ollama HTTP client (no real sockets)."""

import json

import httpx
import pytest

from assistant.ollama import (
    MalformedModelOutput,
    ModelNotAvailable,
    OllamaClient,
    OllamaUnreachable,
)


class FakeResponse:
    def __init__(self, status_code=200, content="", text=""):
        self.status_code = status_code
        self._content = content
        self.text = text or json.dumps({"message": {"content": content}})

    def json(self):
        return {"message": {"content": self._content}}


def _patch_post(monkeypatch, responses):
    """Patch httpx.post with a queue of responses or exceptions."""
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "payload": dict(json)})
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


def test_chat_json_returns_parsed_object(monkeypatch):
    calls = _patch_post(monkeypatch, [FakeResponse(content='{"done": true}')])
    client = OllamaClient(base_url="http://test:11434", model="test-model")
    result = client.chat_json([{"role": "user", "content": "hi"}], {"type": "object"})
    assert result == {"done": True}
    payload = calls[0]["payload"]
    assert payload["model"] == "test-model"
    assert payload["format"] == {"type": "object"}
    assert payload["options"]["temperature"] == 0
    assert payload["options"]["num_ctx"] > 0
    assert payload["stream"] is False


def test_model_not_pulled_maps_to_model_not_available(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(status_code=404, text="model not found")])
    client = OllamaClient(base_url="http://test:11434")
    with pytest.raises(ModelNotAvailable):
        client.chat_text([{"role": "user", "content": "hi"}])


def test_connect_error_maps_to_unreachable(monkeypatch):
    _patch_post(monkeypatch, [httpx.ConnectError("refused")])
    client = OllamaClient(base_url="http://test:11434")
    with pytest.raises(OllamaUnreachable):
        client.chat_text([{"role": "user", "content": "hi"}])


def test_timeout_maps_to_unreachable(monkeypatch):
    _patch_post(monkeypatch, [httpx.ReadTimeout("slow")])
    client = OllamaClient(base_url="http://test:11434")
    with pytest.raises(OllamaUnreachable):
        client.chat_text([{"role": "user", "content": "hi"}])


def test_server_error_maps_to_unreachable(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(status_code=500, text="boom")])
    client = OllamaClient(base_url="http://test:11434")
    with pytest.raises(OllamaUnreachable):
        client.chat_text([{"role": "user", "content": "hi"}])


def test_non_json_content_raises_malformed_output(monkeypatch):
    _patch_post(monkeypatch, [FakeResponse(content="not json at all")])
    client = OllamaClient(base_url="http://test:11434")
    with pytest.raises(MalformedModelOutput):
        client.chat_json([{"role": "user", "content": "hi"}], {"type": "object"})


def test_think_flag_retried_without_on_rejection(monkeypatch):
    rejection = FakeResponse(status_code=400)
    rejection.text = 'model does not support "think"'
    calls = _patch_post(monkeypatch, [rejection, FakeResponse(content="ok")])
    client = OllamaClient(base_url="http://test:11434")
    assert client.chat_text([{"role": "user", "content": "hi"}]) == "ok"
    assert "think" in calls[0]["payload"]
    assert "think" not in calls[1]["payload"]
