"""Tests for MCP server core (JSON-RPC handler)."""

import json

import pytest

from mcp.server import McpServer, PROTOCOL_VERSION, jsonrpc_error, jsonrpc_result

pytestmark = pytest.mark.django_db


class TestJsonRpcHelpers:
    def test_jsonrpc_result(self):
        r = jsonrpc_result({"foo": "bar"}, 1)
        assert r["jsonrpc"] == "2.0"
        assert r["result"] == {"foo": "bar"}
        assert r["id"] == 1

    def test_jsonrpc_error(self):
        r = jsonrpc_error(-32600, "Invalid Request", 42)
        assert r["error"]["code"] == -32600
        assert r["error"]["message"] == "Invalid Request"
        assert r["id"] == 42


class TestMcpServer:
    def _make_server(self):
        srv = McpServer()
        # Register a simple test tool
        srv.register_tool(
            "echo",
            "Echo back the input",
            {"type": "object", "properties": {"message": {"type": "string"}}},
            lambda user, args: {"echoed": args.get("message", "")},
        )
        return srv

    def test_initialize(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }), None)
        assert result["result"]["protocolVersion"] == PROTOCOL_VERSION
        assert "tools" in result["result"]["capabilities"]

    def test_ping(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping",
        }), None)
        assert result["result"] == {}

    def test_tools_list(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
        }), None)
        tools = result["result"]["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "echo"

    def test_tools_call(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "hello"},
            },
        }), None)
        content = result["result"]["content"]
        assert content[0]["type"] == "text"
        data = json.loads(content[0]["text"])
        assert data["echoed"] == "hello"

    def test_unknown_method(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "unknown/method",
        }), None)
        assert "error" in result
        assert result["error"]["code"] == -32601

    def test_unknown_tool(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "nonexistent"},
        }), None)
        assert "error" in result
        assert result["error"]["code"] == -32602

    def test_parse_error(self):
        srv = self._make_server()
        result = srv.handle_request("not json at all", None)
        assert result["error"]["code"] == -32700

    def test_invalid_request_no_jsonrpc(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({"id": 1, "method": "ping"}), None)
        assert result["error"]["code"] == -32600

    def test_notification_no_response(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps({
            "jsonrpc": "2.0",
            "method": "initialized",
        }), None)
        # Notifications should return None (no response)
        assert result is None

    def test_batch_request(self):
        srv = self._make_server()
        result = srv.handle_request(json.dumps([
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]), None)
        assert isinstance(result, list)
        assert len(result) == 2
