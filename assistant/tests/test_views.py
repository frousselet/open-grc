"""Tests for the palette partial view."""

import pytest
from django.test import override_settings
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assistant.engine import AskOutcome, ToolRun
from assistant.providers import ModelNotAvailable, ServiceUnreachable

ASK_URL = "/api/assistant/ask/"


class StubEngine:
    outcome = None
    error = None

    def __init__(self, user, language="en", client=None):
        self.user = user
        self.language = language

    def ask(self, question):
        if type(self).error is not None:
            raise type(self).error
        return type(self).outcome


@pytest.fixture
def stub_engine(monkeypatch):
    StubEngine.outcome = None
    StubEngine.error = None
    monkeypatch.setattr("assistant.views.AssistantEngine", StubEngine)
    return StubEngine


@pytest.fixture
def logged_client(client, db):
    user = UserFactory()
    client.force_login(user)
    return client


def test_url_reverses():
    assert reverse("assistant:ask") == ASK_URL


@pytest.mark.django_db
def test_login_required(client):
    response = client.post(ASK_URL, {"q": "Bonjour ?"})
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_get_not_allowed(logged_client):
    assert logged_client.get(ASK_URL).status_code == 405


@override_settings(AI_ASSISTANT_ENABLED=False)
def test_disabled_renders_friendly_state(logged_client):
    response = logged_client.post(ASK_URL, {"q": "Quelles décisions ?"})
    assert response.status_code == 200
    assert "The assistant is disabled." in response.text


def test_too_short_question_is_invalid(logged_client, stub_engine):
    response = logged_client.post(ASK_URL, {"q": "a"})
    assert response.status_code == 200
    assert "rephrasing" in response.text


def test_happy_path_renders_summary_badge_and_cards(logged_client, stub_engine):
    run = ToolRun(
        tool="list_management_review_decisions",
        label="Decisions",
        icon="bi-check2-square",
        arguments={},
        records=[{"id": "x"}],
        cards=[{
            "title": "DECS-1 Renew SOC contract",
            "subtitle": "completed",
            "url": "/reports/decisions/abc/",
            "icon": "bi-check2-square",
        }],
    )
    stub_engine.outcome = AskOutcome(
        question="q?", language="fr",
        summary="Une décision a été prise.",
        tool_runs=[run],
    )
    response = logged_client.post(ASK_URL, {"q": "Quelles décisions ont été prises ?"})
    content = response.text
    assert "Une décision a été prise." in content
    assert "ai-badge" in content
    assert 'href="/reports/decisions/abc/"' in content
    assert "DECS-1 Renew SOC contract" in content
    assert "AI-generated summary" in content
    # The disclaimer names the active provider and model.
    assert "Mistral mistral-small-latest" in content


def test_out_of_scope_question_shows_hint_not_no_records(logged_client, stub_engine):
    stub_engine.outcome = AskOutcome(question="Hello, how are you?", language="en")
    response = logged_client.post(ASK_URL, {"q": "Hello, how are you?"})
    content = response.text
    assert "only answers questions about your GRC data" in content
    assert "No matching records found." not in content
    assert "AI-generated summary" not in content


def test_tools_ran_but_zero_records_shows_no_records(logged_client, stub_engine):
    run = ToolRun(
        tool="list_risks", label="Risks", icon="bi-radioactive",
        arguments={}, records=[], cards=[],
    )
    stub_engine.outcome = AskOutcome(question="q?", language="en", tool_runs=[run])
    response = logged_client.post(ASK_URL, {"q": "Des risques critiques ouverts ?"})
    assert "No matching records found." in response.text


def test_permission_denied_note_rendered(logged_client, stub_engine):
    run = ToolRun(
        tool="list_management_reviews",
        label="Management reviews",
        icon="bi-clipboard-data",
        arguments={},
        error="permission_denied",
    )
    stub_engine.outcome = AskOutcome(question="q?", language="en", tool_runs=[run])
    response = logged_client.post(ASK_URL, {"q": "Dernière revue ?"})
    assert "lack the required permission" in response.text


def test_model_missing_shows_model_name(logged_client, stub_engine, settings):
    settings.AI_ASSISTANT_MODEL = "mistral-small-latest"
    stub_engine.error = ModelNotAvailable("mistral-small-latest")
    response = logged_client.post(ASK_URL, {"q": "Quelles décisions ?"})
    assert "mistral-small-latest" in response.text


def test_unreachable_state(logged_client, stub_engine):
    stub_engine.error = ServiceUnreachable("down")
    response = logged_client.post(ASK_URL, {"q": "Quelles décisions ?"})
    assert "unreachable" in response.text
