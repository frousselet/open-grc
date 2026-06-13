"""Tests for Ask Cairn answer feedback: model, web flow, API, admin, MCP."""

import json

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from assistant.admin import AssistantFeedbackAdmin
from assistant.engine import AskOutcome, ToolRun
from assistant.models import AssistantFeedback

ASK_URL = "/api/assistant/ask/"
FEEDBACK_URL = "/api/assistant/feedback/"
FEEDBACK_API = "/api/v1/assistant/feedback/"


# ── Fixtures (mirror test_views.py) ───────────────────────


class StubEngine:
    outcome = None

    def __init__(self, user, language="en", client=None):
        pass

    def ask(self, question):
        return type(self).outcome


@pytest.fixture
def stub_engine(monkeypatch):
    StubEngine.outcome = None
    monkeypatch.setattr("assistant.views.AssistantEngine", StubEngine)
    return StubEngine


@pytest.fixture
def logged_client(client, db):
    client.force_login(UserFactory())
    return client


def _answer_with_cards():
    run = ToolRun(
        tool="list_risks", label="Risks", icon="bi-radioactive", arguments={},
        cards=[{"title": "RISK-2 SCADA", "subtitle": "treatment planned", "url": "/risks/x/", "icon": "bi-radioactive"}],
    )
    return AskOutcome(
        question="Quels risques ?", language="fr",
        summary="Deux risques critiques.", tool_runs=[run],
    )


# ── Model ─────────────────────────────────────────────────


def test_url_reverses():
    assert reverse("assistant:feedback") == FEEDBACK_URL


@pytest.mark.django_db
def test_model_str_and_export_dict():
    fb = AssistantFeedback.objects.create(
        question="What does A.5.3 say?", rating="up", comment="useful",
        summary="Segregation of duties.", results=[{"tool": "list_requirements"}],
        provider="mistral", model_name="mistral-small-latest",
    )
    assert "What does A.5.3 say" in str(fb)
    data = fb.as_export_dict()
    assert data["rating"] == "up"
    assert data["comment"] == "useful"
    assert data["results"] == [{"tool": "list_requirements"}]
    assert data["model"] == "mistral-small-latest"
    assert data["user"] is None


# ── Web flow (session-backed capture) ─────────────────────


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_answer_shows_feedback_widget_and_records(logged_client, stub_engine):
    stub_engine.outcome = _answer_with_cards()
    ask = logged_client.post(ASK_URL, {"q": "Quels risques critiques ?"})
    assert "assistant-feedback" in ask.text
    assert "Was this helpful?" in ask.text

    token = logged_client.session["assistant_last_answer"]["token"]
    resp = logged_client.post(
        FEEDBACK_URL, {"answer_id": token, "rating": "up", "comment": "Très utile"}
    )
    assert resp.status_code == 200
    assert "Thanks for your feedback." in resp.text

    fb = AssistantFeedback.objects.get()
    assert fb.rating == "up"
    assert fb.comment == "Très utile"
    assert fb.question == "Quels risques ?"      # taken from the stashed answer
    assert fb.summary == "Deux risques critiques."
    assert fb.results and fb.results[0]["tool"] == "list_risks"
    assert fb.user is not None


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_feedback_rejects_unknown_token(logged_client, stub_engine):
    stub_engine.outcome = _answer_with_cards()
    logged_client.post(ASK_URL, {"q": "Quels risques ?"})
    resp = logged_client.post(FEEDBACK_URL, {"answer_id": "bogus", "rating": "up"})
    assert resp.status_code == 200
    assert "Could not record your feedback." in resp.text
    assert AssistantFeedback.objects.count() == 0


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_feedback_rejects_invalid_rating(logged_client, stub_engine):
    stub_engine.outcome = _answer_with_cards()
    logged_client.post(ASK_URL, {"q": "Quels risques ?"})
    token = logged_client.session["assistant_last_answer"]["token"]
    resp = logged_client.post(FEEDBACK_URL, {"answer_id": token, "rating": "sideways"})
    assert "Could not record your feedback." in resp.text
    assert AssistantFeedback.objects.count() == 0


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_feedback_is_one_shot(logged_client, stub_engine):
    stub_engine.outcome = _answer_with_cards()
    logged_client.post(ASK_URL, {"q": "Quels risques ?"})
    token = logged_client.session["assistant_last_answer"]["token"]
    logged_client.post(FEEDBACK_URL, {"answer_id": token, "rating": "up"})
    # Second submission with the same (now cleared) token is refused.
    resp = logged_client.post(FEEDBACK_URL, {"answer_id": token, "rating": "down"})
    assert "Could not record your feedback." in resp.text
    assert AssistantFeedback.objects.count() == 1


@pytest.mark.django_db
def test_feedback_login_required(client):
    resp = client.post(FEEDBACK_URL, {"answer_id": "x", "rating": "up"})
    assert resp.status_code == 302


# ── REST API ──────────────────────────────────────────────


@pytest.mark.django_db
def test_api_create_open_to_authenticated():
    user = UserFactory()
    api = APIClient()
    api.force_authenticate(user)
    resp = api.post(
        FEEDBACK_API,
        {"question": "Q?", "language": "fr", "rating": "up", "comment": "ok"},
        format="json",
    )
    assert resp.status_code == 201
    fb = AssistantFeedback.objects.get()
    assert fb.user == user
    assert fb.rating == "up"


@pytest.mark.django_db
def test_api_create_requires_authentication():
    resp = APIClient().post(FEEDBACK_API, {"question": "Q?", "rating": "up"}, format="json")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_api_list_forbidden_without_permission():
    api = APIClient()
    api.force_authenticate(UserFactory())
    assert api.get(FEEDBACK_API).status_code == 403


@pytest.mark.django_db
def test_api_list_and_export_with_permission():
    AssistantFeedback.objects.create(question="Q?", rating="down", comment="meh")
    api = APIClient()
    api.force_authenticate(UserFactory(is_superuser=True, is_staff=True))
    assert api.get(FEEDBACK_API).status_code == 200
    export = api.get(FEEDBACK_API + "export/")
    assert export.status_code == 200
    assert export.data["count"] == 1
    assert export.data["feedback"][0]["rating"] == "down"


# ── Django admin export action ────────────────────────────


@pytest.mark.django_db
def test_admin_export_action_returns_json():
    AssistantFeedback.objects.create(
        question="Q?", rating="up", comment="great", summary="S",
    )
    model_admin = AssistantFeedbackAdmin(AssistantFeedback, AdminSite())
    response = model_admin.export_as_json(None, AssistantFeedback.objects.all())
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert "attachment" in response["Content-Disposition"]
    payload = json.loads(response.content)
    assert payload["count"] == 1
    assert payload["feedback"][0]["rating"] == "up"


# ── MCP tool ──────────────────────────────────────────────


def _fb_tool():
    from mcp.api.views_mcp import get_mcp_server

    return get_mcp_server().get_tool("list_assistant_feedback")


def test_mcp_tool_registered():
    tool = _fb_tool()
    assert tool is not None
    assert "rating" in tool["inputSchema"]["properties"]


@pytest.mark.django_db
def test_mcp_tool_requires_permission():
    result = _fb_tool()["handler"](UserFactory(), {})
    assert result["isError"] is True


@pytest.mark.django_db
def test_mcp_tool_lists_for_superuser():
    AssistantFeedback.objects.create(question="Q?", rating="up", comment="c")
    result = _fb_tool()["handler"](UserFactory(is_superuser=True), {})
    assert result["total"] == 1
    assert result["items"][0]["rating"] == "up"


# ── In-app Administration list + export ───────────────────

LIST_URL = "/api/assistant/feedback/list/"
EXPORT_URL = "/api/assistant/feedback/export/"


def test_admin_list_urls_reverse():
    assert reverse("assistant:feedback-list") == LIST_URL
    assert reverse("assistant:feedback-export") == EXPORT_URL


@pytest.mark.django_db
def test_admin_list_forbidden_without_permission(client):
    client.force_login(UserFactory())
    assert client.get(LIST_URL).status_code == 403


@pytest.mark.django_db
def test_admin_list_visible_with_permission(client):
    AssistantFeedback.objects.create(question="Quelle exigence ?", rating="down", comment="confus")
    client.force_login(UserFactory(is_superuser=True, is_staff=True))
    response = client.get(LIST_URL)
    assert response.status_code == 200
    assert "Quelle exigence ?" in response.text


@pytest.mark.django_db
def test_admin_list_filters_by_rating(client):
    AssistantFeedback.objects.create(question="Up one", rating="up")
    AssistantFeedback.objects.create(question="Down one", rating="down")
    client.force_login(UserFactory(is_superuser=True))
    response = client.get(LIST_URL, {"rating": "up"})
    assert "Up one" in response.text
    assert "Down one" not in response.text


@pytest.mark.django_db
def test_admin_export_downloads_json(client):
    AssistantFeedback.objects.create(question="Q?", rating="up", comment="great")
    client.force_login(UserFactory(is_superuser=True))
    response = client.get(EXPORT_URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert "attachment" in response["Content-Disposition"]
    payload = json.loads(response.content)
    assert payload["count"] == 1
    assert payload["feedback"][0]["comment"] == "great"


@pytest.mark.django_db
def test_admin_export_forbidden_without_permission(client):
    client.force_login(UserFactory())
    assert client.get(EXPORT_URL).status_code == 403


# ── Mark corrected / exclude from exports ─────────────────


@pytest.mark.django_db
def test_model_mark_resolved_and_unresolved():
    user = UserFactory()
    fb = AssistantFeedback.objects.create(question="Q?", rating="down")
    fb.mark_resolved(user)
    assert fb.is_resolved and fb.resolved_by == user and fb.resolved_at is not None
    fb.mark_unresolved()
    assert not fb.is_resolved and fb.resolved_by is None and fb.resolved_at is None


@pytest.mark.django_db
def test_list_defaults_to_open_and_hides_corrected(client):
    AssistantFeedback.objects.create(question="Still open one", rating="down")
    AssistantFeedback.objects.create(question="Already fixed one", rating="down", is_resolved=True)
    client.force_login(UserFactory(is_superuser=True))
    response = client.get(LIST_URL)
    assert "Still open one" in response.text
    assert "Already fixed one" not in response.text
    # status=all shows everything
    response_all = client.get(LIST_URL, {"status": "all"})
    assert "Already fixed one" in response_all.text


@pytest.mark.django_db
def test_resolve_view_marks_corrected_and_redirects(client):
    fb = AssistantFeedback.objects.create(question="Q?", rating="down")
    user = UserFactory(is_superuser=True)
    client.force_login(user)
    url = reverse("assistant:feedback-resolve", args=[fb.pk])
    response = client.post(url, {"next_qs": "status=open"})
    assert response.status_code == 302
    fb.refresh_from_db()
    assert fb.is_resolved and fb.resolved_by == user
    # reopen
    client.post(url, {"action": "reopen"})
    fb.refresh_from_db()
    assert not fb.is_resolved


@pytest.mark.django_db
def test_resolve_redirect_only_keeps_whitelisted_filters(client):
    fb = AssistantFeedback.objects.create(question="Q?", rating="down")
    client.force_login(UserFactory(is_superuser=True))
    url = reverse("assistant:feedback-resolve", args=[fb.pk])
    # Untrusted junk (and an external-looking value) must not reach the redirect.
    response = client.post(url, {"next_qs": "status=resolved&evil=//evil.com&x=1"})
    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("/api/assistant/feedback/list/")
    assert "status=resolved" in location
    assert "evil" not in location and "evil.com" not in location


@pytest.mark.django_db
def test_resolve_view_requires_permission(client):
    fb = AssistantFeedback.objects.create(question="Q?", rating="down")
    client.force_login(UserFactory())
    url = reverse("assistant:feedback-resolve", args=[fb.pk])
    assert client.post(url).status_code == 403


@pytest.mark.django_db
def test_inapp_export_excludes_corrected_by_default(client):
    AssistantFeedback.objects.create(question="open", rating="down")
    AssistantFeedback.objects.create(question="fixed", rating="down", is_resolved=True)
    client.force_login(UserFactory(is_superuser=True))
    payload = json.loads(client.get(EXPORT_URL).content)
    assert payload["count"] == 1
    assert payload["feedback"][0]["question"] == "open"
    # status=all includes corrected
    payload_all = json.loads(client.get(EXPORT_URL, {"status": "all"}).content)
    assert payload_all["count"] == 2


@pytest.mark.django_db
def test_api_export_excludes_corrected_unless_flag():
    AssistantFeedback.objects.create(question="open", rating="down")
    AssistantFeedback.objects.create(question="fixed", rating="down", is_resolved=True)
    api = APIClient()
    api.force_authenticate(UserFactory(is_superuser=True))
    assert api.get(FEEDBACK_API + "export/").data["count"] == 1
    assert api.get(FEEDBACK_API + "export/", {"include_resolved": "true"}).data["count"] == 2


@pytest.mark.django_db
def test_api_resolve_and_unresolve_actions():
    fb = AssistantFeedback.objects.create(question="Q?", rating="down")
    admin = UserFactory(is_superuser=True)
    api = APIClient()
    api.force_authenticate(admin)
    resp = api.post(f"{FEEDBACK_API}{fb.pk}/resolve/")
    assert resp.status_code == 200 and resp.data["is_resolved"] is True
    fb.refresh_from_db()
    assert fb.is_resolved and fb.resolved_by == admin
    resp = api.post(f"{FEEDBACK_API}{fb.pk}/unresolve/")
    assert resp.data["is_resolved"] is False


@pytest.mark.django_db
def test_mcp_list_excludes_corrected_unless_flag():
    AssistantFeedback.objects.create(question="open", rating="down")
    AssistantFeedback.objects.create(question="fixed", rating="down", is_resolved=True)
    admin = UserFactory(is_superuser=True)
    assert _fb_tool()["handler"](admin, {})["total"] == 1
    assert _fb_tool()["handler"](admin, {"include_resolved": True})["total"] == 2
