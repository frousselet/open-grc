"""Tests for semantic index maintenance: signal prune, rebuild helpers, view."""

import pytest
from django.test import override_settings
from django.urls import reverse

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from assistant import semantic
from assistant.models import SemanticIndex, content_hash
from compliance.tests.factories import RequirementFactory


class _FakeEmbedClient:
    def embed(self, texts):
        return [[float(len(t)), 1.0] for t in texts]


def _index_row(req, model="test-embed"):
    SemanticIndex.objects.create(
        content_type=SemanticIndex.REQUIREMENT,
        object_id=req.pk,
        text="x",
        content_hash=content_hash(model, "x"),
        embedding=[1.0, 0.0],
        model_name=model,
    )


def _grant(user, codename):
    perm = PermissionFactory(codename=codename)
    group = GroupFactory()
    group.permissions.add(perm)
    group.users.add(user)
    if hasattr(user, "_custom_perm_cache"):
        del user._custom_perm_cache


# ── post_delete signal ────────────────────────────────────


@pytest.mark.django_db
def test_deleting_requirement_prunes_its_embedding():
    req = RequirementFactory(name="To be deleted")
    _index_row(req)
    assert SemanticIndex.objects.filter(object_id=req.pk).exists()

    req.delete()

    assert not SemanticIndex.objects.filter(object_id=req.pk).exists()


# ── rebuild_index (synchronous) ───────────────────────────


@pytest.mark.django_db
def test_rebuild_index_embeds_idempotently_and_prunes(monkeypatch):
    monkeypatch.setattr("assistant.semantic.get_client", lambda: _FakeEmbedClient())
    RequirementFactory(name="Backup policy")
    req2 = RequirementFactory(name="Access control")

    result = semantic.rebuild_index()
    assert result == {"embedded": 2, "pruned": 0}

    # Idempotent: nothing changed, nothing re-embedded.
    assert semantic.rebuild_index() == {"embedded": 0, "pruned": 0}

    # Deleting the index row (not the requirement) makes it re-embed just that one.
    SemanticIndex.objects.filter(object_id=req2.pk).delete()
    assert semantic.rebuild_index() == {"embedded": 1, "pruned": 0}


# ── rebuild_index_async (guarded) ─────────────────────────


@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=False)
def test_rebuild_async_is_noop_when_semantic_disabled():
    assert semantic.rebuild_index_async() is False


# ── index_status ──────────────────────────────────────────


@pytest.mark.django_db
@override_settings(
    AI_ASSISTANT_SEMANTIC_ENABLED=True,
    AI_ASSISTANT_PROVIDER="mistral",
    AI_ASSISTANT_EMBED_MODEL="mistral-embed",
)
def test_index_status_reports_counts_and_capability():
    req = RequirementFactory(name="Indexed one")
    RequirementFactory(name="Not indexed")
    _index_row(req)

    status = semantic.index_status()
    assert status["enabled"] is True
    assert status["embeddings_supported"] is True
    assert status["embed_model"] == "mistral-embed"
    assert status["indexed"] == 1
    assert status["total"] == 2
    assert status["last_updated"] is not None


@pytest.mark.django_db
@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=True, AI_ASSISTANT_PROVIDER="anthropic")
def test_index_status_flags_provider_without_embeddings():
    assert semantic.index_status()["embeddings_supported"] is False


# ── RebuildSemanticIndexView ──────────────────────────────


@pytest.mark.django_db
@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=True)
def test_rebuild_view_requires_permission(client, monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "assistant.semantic.rebuild_index_async",
        lambda **kw: calls.setdefault("started", True) or True,
    )
    user = UserFactory()  # no system.config.update permission
    client.force_login(user)
    resp = client.post(reverse("assistant:rebuild-semantic-index"))
    assert resp.status_code == 302
    assert "started" not in calls  # blocked before any rebuild


@pytest.mark.django_db
@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=False)
def test_rebuild_view_reports_disabled(client, monkeypatch):
    started = {}
    monkeypatch.setattr(
        "assistant.semantic.rebuild_index_async",
        lambda **kw: started.setdefault("called", True),
    )
    user = UserFactory()
    _grant(user, "system.config.update")
    client.force_login(user)
    resp = client.post(reverse("assistant:rebuild-semantic-index"))
    assert resp.status_code == 302
    # Disabled short-circuits before touching the rebuild helper.
    assert "called" not in started


@pytest.mark.django_db
@override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=True)
def test_rebuild_view_starts_rebuild_with_permission(client, monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "assistant.semantic.rebuild_index_async",
        lambda **kw: calls.setdefault("started", True) or True,
    )
    user = UserFactory()
    _grant(user, "system.config.update")
    client.force_login(user)
    resp = client.post(reverse("assistant:rebuild-semantic-index"))
    assert resp.status_code == 302
    assert calls.get("started") is True
