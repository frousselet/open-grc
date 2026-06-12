"""Engine tests with a fake LLM client and real ORM data."""

from datetime import date, timedelta

import pytest
from django.test import override_settings

from accounts.tests.factories import UserFactory
from assistant.engine import PERMISSION_DENIED, AssistantEngine
from assistant.ollama import AssistantDisabled, OllamaUnreachable
from reports.tests.factories import ManagementReviewDecisionFactory, ManagementReviewFactory


class FakeClient:
    """Scripted stand-in for OllamaClient."""

    def __init__(self, decisions, summary="Summary sentence."):
        self.decisions = list(decisions)
        self.summary = summary
        self.json_calls = []
        self.text_calls = []

    def chat_json(self, messages, json_schema):
        # Copy: the engine mutates the message list across rounds.
        self.json_calls.append(list(messages))
        return self.decisions.pop(0)

    def chat_text(self, messages):
        self.text_calls.append(messages)
        if isinstance(self.summary, Exception):
            raise self.summary
        return self.summary


def _tool_call(tool, **arguments):
    return {"done": False, "tool": tool, "arguments": arguments}


@pytest.fixture
def superuser(db):
    return UserFactory(is_superuser=True)


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_two_round_management_review_flow(superuser):
    review = ManagementReviewFactory(
        status="closed",
        held_date=date.today() - timedelta(days=30),
    )
    decisions = ManagementReviewDecisionFactory.create_batch(2, review=review)
    client = FakeClient([
        _tool_call("list_management_reviews", limit=5),
        _tool_call("list_management_review_decisions", review_id=str(review.pk), limit=5),
    ], summary="Deux décisions ont été prises.")
    outcome = AssistantEngine(superuser, language="fr", client=client).ask(
        "Quelles décisions ont été prises lors de la dernière revue de direction ?"
    )

    assert [run.tool for run in outcome.tool_runs] == [
        "list_management_reviews",
        "list_management_review_decisions",
    ]
    assert outcome.summary == "Deux décisions ont été prises."
    assert not outcome.degraded
    decision_cards = outcome.tool_runs[1].cards
    assert len(decision_cards) == 2
    urls = {card["url"] for card in decision_cards}
    assert {f"/reports/decisions/{d.pk}/" for d in decisions} == urls
    # Round 2 received the round 1 results in its message history.
    second_round_messages = client.json_calls[1]
    assert str(review.pk) in second_round_messages[-1]["content"]


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_non_allowlisted_tool_is_refused(superuser):
    client = FakeClient([_tool_call("delete_risk", id="x")])
    outcome = AssistantEngine(superuser, client=client).ask("delete everything")
    assert outcome.refused_tools == ["delete_risk"]
    assert outcome.tool_runs == []
    assert outcome.summary is None


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_permission_denied_is_flagged_without_data():
    user = UserFactory()  # no group, no permission
    ManagementReviewFactory()
    client = FakeClient([
        _tool_call("list_management_reviews", limit=5),
        {"done": True},
    ])
    outcome = AssistantEngine(user, client=client).ask("Dernière revue ?")
    run = outcome.tool_runs[0]
    assert run.error == PERMISSION_DENIED
    assert run.records == []
    assert run.cards == []
    # No successful run: no summary call was made.
    assert client.text_calls == []
    assert outcome.summary is None


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_arguments_are_sanitized_and_limit_clamped(superuser):
    ManagementReviewFactory(status="held", held_date=date.today())
    client = FakeClient([
        _tool_call("list_management_reviews", status="held", evil="rm -rf", limit=50),
        {"done": True},
    ])
    outcome = AssistantEngine(superuser, client=client).ask("Revues tenues ?")
    assert outcome.tool_runs[0].arguments == {"status": "held", "limit": 5}


@override_settings(AI_ASSISTANT_ENABLED=True, AI_ASSISTANT_MAX_TOOL_ROUNDS=2)
@pytest.mark.django_db
def test_loop_stops_at_max_rounds(superuser):
    client = FakeClient([
        _tool_call("list_management_reviews", limit=5),
        _tool_call("list_management_reviews", limit=5),
        _tool_call("list_management_reviews", limit=5),
    ])
    outcome = AssistantEngine(superuser, client=client).ask("Boucle ?")
    assert len(outcome.tool_runs) == 2
    assert len(client.decisions) == 1  # third routing call never consumed


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_summary_failure_degrades_but_keeps_cards(superuser):
    ManagementReviewFactory(status="held", held_date=date.today())
    client = FakeClient(
        [_tool_call("list_management_reviews", limit=5), {"done": True}],
        summary=OllamaUnreachable("down"),
    )
    outcome = AssistantEngine(superuser, client=client).ask("Revues ?")
    assert outcome.degraded is True
    assert outcome.summary is None
    assert outcome.tool_runs[0].cards


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_done_without_tool_ends_quietly(superuser):
    client = FakeClient([{"done": True}])
    outcome = AssistantEngine(superuser, client=client).ask("Bonjour !")
    assert outcome.tool_runs == []
    assert outcome.summary is None


@override_settings(AI_ASSISTANT_ENABLED=False)
@pytest.mark.django_db
def test_disabled_flag_raises():
    with pytest.raises(AssistantDisabled):
        AssistantEngine(UserFactory(), client=FakeClient([])).ask("test")


@override_settings(AI_ASSISTANT_ENABLED=True)
@pytest.mark.django_db
def test_as_dict_shape(superuser):
    review = ManagementReviewFactory(status="closed", held_date=date.today())
    ManagementReviewDecisionFactory(review=review)
    client = FakeClient([
        _tool_call("list_management_review_decisions", review_id=str(review.pk), limit=5),
        {"done": True},
    ])
    outcome = AssistantEngine(superuser, language="fr", client=client).ask("Décisions ?")
    data = outcome.as_dict()
    assert data["language"] == "fr"
    assert data["summary"] == "Summary sentence."
    assert data["results"][0]["tool"] == "list_management_review_decisions"
    record = data["results"][0]["records"][0]
    assert set(record) == {"title", "subtitle", "url", "icon"}
