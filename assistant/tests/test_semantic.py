"""Tests for semantic search: cosine, embed-text, provider embed, MCP tool."""

import httpx
import pytest
from django.test import override_settings

from accounts.tests.factories import UserFactory
from assistant.models import SemanticIndex
from assistant.providers.base import ServiceUnreachable
from assistant.providers.mistral import MistralClient
from assistant.semantic import cosine, rank_object_ids, requirement_text
from compliance.tests.factories import RequirementFactory


# ── Pure helpers ──────────────────────────────────────────


def test_cosine_identical_and_orthogonal():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([1.0, 2.0], [2.0, 4.0]) == pytest.approx(1.0)  # same direction
    assert cosine([], [1.0]) == 0.0
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


@pytest.mark.django_db
def test_requirement_text_strips_html_and_joins():
    req = RequirementFactory.build(
        requirement_number="A.5.3", name="Segregation of duties",
        description="<p>Conflicting duties are <b>segregated</b>.</p>", guidance="",
    )
    text = requirement_text(req)
    assert "A.5.3" in text
    assert "Segregation of duties" in text
    assert "<p>" not in text and "<b>" not in text
    assert "Conflicting duties are segregated." in text


# ── Mistral embeddings ────────────────────────────────────


class FakeEmbedResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or []
        self.text = text or "{}"

    def json(self):
        return {"data": self._data}


def test_mistral_embed_parses_and_orders(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        # Return out of order to check sorting by index.
        return FakeEmbedResponse(data=[
            {"index": 1, "embedding": [0.0, 1.0]},
            {"index": 0, "embedding": [1.0, 0.0]},
        ])

    monkeypatch.setattr(httpx, "post", fake_post)
    client = MistralClient(base_url="https://api.mistral.ai/v1", model="m", api_key="k")
    out = client.embed(["a", "b"])
    assert out == [[1.0, 0.0], [0.0, 1.0]]
    assert captured["url"].endswith("/embeddings")
    assert captured["payload"]["input"] == ["a", "b"]


def test_mistral_embed_empty_input_skips_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not call the API")

    monkeypatch.setattr(httpx, "post", boom)
    assert MistralClient(api_key="k").embed([]) == []


def test_mistral_embed_auth_error_maps_to_unreachable(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeEmbedResponse(status_code=401, text="nope"))
    with pytest.raises(ServiceUnreachable):
        MistralClient(api_key="bad").embed(["x"])


# ── Ranking over the stored index ─────────────────────────


@pytest.mark.django_db
def test_rank_object_ids_orders_by_similarity():
    near = RequirementFactory(name="near")
    far = RequirementFactory(name="far")
    SemanticIndex.objects.create(
        content_type=SemanticIndex.REQUIREMENT, object_id=near.pk,
        text="near", content_hash="h1", embedding=[1.0, 0.0],
    )
    SemanticIndex.objects.create(
        content_type=SemanticIndex.REQUIREMENT, object_id=far.pk,
        text="far", content_hash="h2", embedding=[0.0, 1.0],
    )
    ranked = rank_object_ids([0.9, 0.1], SemanticIndex.REQUIREMENT, limit=5)
    assert ranked[0] == near.pk
    assert ranked[1] == far.pk


# ── MCP tool ──────────────────────────────────────────────


def _tool():
    from mcp.api.views_mcp import get_mcp_server

    return get_mcp_server().get_tool("semantic_search_requirements")


def test_semantic_tool_registered():
    assert _tool() is not None


@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=False)
@pytest.mark.django_db
def test_semantic_tool_empty_when_disabled():
    result = _tool()["handler"](UserFactory(is_superuser=True), {"query": "x"})
    assert result == {"total": 0, "items": []}


@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=True)
@pytest.mark.django_db
def test_semantic_tool_requires_permission(monkeypatch):
    monkeypatch.setattr("assistant.semantic.get_client", lambda: _FakeEmbedClient())
    result = _tool()["handler"](UserFactory(), {"query": "duties"})
    assert result["isError"] is True


class _FakeEmbedClient:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=True)
@pytest.mark.django_db
def test_semantic_tool_returns_ranked_requirements(monkeypatch):
    monkeypatch.setattr("assistant.semantic.get_client", lambda: _FakeEmbedClient())
    hit = RequirementFactory(requirement_number="A.5.3", name="Segregation of duties")
    miss = RequirementFactory(requirement_number="A.8.13", name="Information backup")
    SemanticIndex.objects.create(
        content_type=SemanticIndex.REQUIREMENT, object_id=hit.pk,
        text="seg", content_hash="h", embedding=[1.0, 0.0],
    )
    SemanticIndex.objects.create(
        content_type=SemanticIndex.REQUIREMENT, object_id=miss.pk,
        text="bak", content_hash="h", embedding=[0.2, 0.98],
    )
    result = _tool()["handler"](
        UserFactory(is_superuser=True), {"query": "séparation des tâches", "limit": 5}
    )
    assert result["total"] == 2
    assert result["items"][0]["requirement_number"] == "A.5.3"  # most similar first


# ── Reindex management command ────────────────────────────


@pytest.mark.django_db
def test_rebuild_command_embeds_and_is_idempotent(monkeypatch):
    from io import StringIO

    from django.core.management import call_command

    monkeypatch.setattr(
        "assistant.management.commands.rebuild_semantic_index.get_client",
        lambda: _FakeEmbedClient(),
    )
    RequirementFactory(name="Backup policy")
    RequirementFactory(name="Access control")

    call_command("rebuild_semantic_index", stdout=StringIO())
    assert SemanticIndex.objects.filter(content_type=SemanticIndex.REQUIREMENT).count() == 2

    # Re-running without changes re-embeds nothing (content hashes match).
    out = StringIO()
    call_command("rebuild_semantic_index", stdout=out)
    assert "0 embedded" in out.getvalue()
