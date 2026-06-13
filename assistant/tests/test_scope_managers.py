"""Surfacing scope managers (the responsible users) to the assistant.

Regression for feedback: "Qui est responsable du périmètre X ?" found the
scope but could not name the responsible, because managers were only exposed
as UUIDs (stripped before the summary) and were not in the summary fields.
"""

import uuid

import pytest

from accounts.tests.factories import UserFactory
from assistant.catalog import TOOL_CATALOG
from assistant.engine import _strip_identifiers
from context.tests.factories import ScopeFactory


@pytest.mark.django_db
def test_scope_manager_names_returns_display_names():
    scope = ScopeFactory()
    user = UserFactory(first_name="Elise", last_name="Moreau")
    scope.managers.add(user)
    assert user.display_name in scope.manager_names


def test_list_scopes_compact_record_includes_manager_names():
    spec = TOOL_CATALOG["list_scopes"]
    record = {
        "id": str(uuid.uuid4()),
        "reference": "SCOP-1",
        "name": "Voltara Group",
        "workflow_state": "validated",
        "manager_names": ["Elise Moreau"],
    }
    assert spec.compact_record(record)["manager_names"] == ["Elise Moreau"]


def test_summary_stage_keeps_manager_names_but_strips_ids():
    data = {
        "id": str(uuid.uuid4()),
        "name": "Voltara Group",
        "manager_names": ["Elise Moreau"],
    }
    cleaned = _strip_identifiers(data)
    assert "id" not in cleaned
    assert cleaned["manager_names"] == ["Elise Moreau"]
