"""Guards on the curated tool allowlist."""

import uuid

from assistant.catalog import READ_ONLY_PREFIXES, TOOL_CATALOG, catalog_signatures, routing_schema

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


def test_routing_schema_constrains_tool_names():
    schema = routing_schema()
    assert schema["properties"]["tool"]["enum"] == sorted(TOOL_CATALOG)
    assert "done" in schema["required"]


def test_signatures_fit_in_a_small_prompt():
    text = catalog_signatures()
    assert len(text) < 4000
    assert text.count("\n") == len(TOOL_CATALOG) - 1


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
