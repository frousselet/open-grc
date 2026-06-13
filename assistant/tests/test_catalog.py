"""Guards on the curated tool allowlist."""

import uuid

from django.test import override_settings

from assistant.catalog import (
    READ_ONLY_PREFIXES,
    TOOL_CATALOG,
    active_specs,
    catalog_signatures,
    plan_schema,
)

WRITE_VERBS = ("create", "update", "delete", "transition", "approve", "batch", "set_", "link", "unlink")


def test_every_catalog_tool_is_read_only():
    for name in TOOL_CATALOG:
        assert name.startswith(READ_ONLY_PREFIXES), name
        for verb in WRITE_VERBS:
            assert verb not in name, name


def test_every_catalog_tool_exists_in_mcp_registry():
    """Drift guard: a renamed or removed MCP tool must fail CI, not production."""
    from mcp.api.views_mcp import get_mcp_server

    server = get_mcp_server()
    for name in TOOL_CATALOG:
        assert server.get_tool(name) is not None, f"{name} missing from MCP registry"


def test_plan_schema_constrains_tool_names_and_step_count():
    schema = plan_schema(3)
    steps = schema["properties"]["steps"]
    assert steps["maxItems"] == 3
    assert steps["items"]["properties"]["tool"]["enum"] == sorted(s.name for s in active_specs())
    assert "steps" in schema["required"]


def test_signatures_fit_in_a_small_prompt():
    text = catalog_signatures()
    assert len(text) < 4000
    assert text.count("\n") == len(active_specs()) - 1


def test_semantic_tool_gated_by_setting():
    with override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=False):
        assert "semantic_search_requirements" not in {s.name for s in active_specs()}
        enum = plan_schema(3)["properties"]["steps"]["items"]["properties"]["tool"]["enum"]
        assert "semantic_search_requirements" not in enum
    with override_settings(AI_ASSISTANT_SEMANTIC_ENABLED=True):
        assert "semantic_search_requirements" in {s.name for s in active_specs()}
    # Always present in the full catalog so the engine can execute it.
    assert "semantic_search_requirements" in TOOL_CATALOG


def test_detail_routes_reverse():
    pk = str(uuid.uuid4())
    for spec in TOOL_CATALOG.values():
        if not spec.detail_route:
            continue
        record = {"id": pk, spec.url_pk_field: pk}
        assert spec.record_url(record), spec.name


def test_build_card_uses_title_fields_and_subtitle():
    spec = TOOL_CATALOG["list_management_review_decisions"]
    record = {
        "id": str(uuid.uuid4()),
        "reference": "DECS-1",
        "title": "Renew SOC contract",
        "status": "in_progress",
    }
    card = spec.build_card(record)
    assert card["title"] == "DECS-1 Renew SOC contract"
    assert card["subtitle"] == "in progress"
    assert card["url"]
    assert card["icon"] == spec.icon
