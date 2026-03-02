"""
MCP (Model Context Protocol) server core implementation.

Implements JSON-RPC 2.0 over Streamable HTTP transport.
Protocol version: 2025-03-26
"""

import json
import logging
import uuid

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-03-26"

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def jsonrpc_error(code, message, req_id=None, data=None):
    resp = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": req_id,
    }
    if data is not None:
        resp["error"]["data"] = data
    return resp


def jsonrpc_result(result, req_id):
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": req_id,
    }


class McpServer:
    """Stateless MCP server that processes JSON-RPC requests."""

    def __init__(self):
        self._tools = {}  # name -> ToolDefinition

    def register_tool(self, name, description, input_schema, handler):
        """Register an MCP tool.

        Args:
            name: Unique tool name
            description: Human-readable description
            input_schema: JSON Schema for tool parameters
            handler: callable(user, arguments) -> result
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler,
        }

    def handle_request(self, body, user):
        """Process a JSON-RPC request and return a response dict (or None for notifications)."""
        try:
            msg = json.loads(body) if isinstance(body, (str, bytes)) else body
        except (json.JSONDecodeError, TypeError):
            return jsonrpc_error(PARSE_ERROR, "Parse error")

        # Handle batch requests
        if isinstance(msg, list):
            results = []
            for item in msg:
                result = self._dispatch(item, user)
                if result is not None:
                    results.append(result)
            return results if results else None

        return self._dispatch(msg, user)

    def _dispatch(self, msg, user):
        if not isinstance(msg, dict):
            return jsonrpc_error(INVALID_REQUEST, "Invalid Request")

        if msg.get("jsonrpc") != "2.0":
            return jsonrpc_error(INVALID_REQUEST, "Invalid Request: jsonrpc must be '2.0'", msg.get("id"))

        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})

        # Notifications have no id
        is_notification = "id" not in msg

        if not method or not isinstance(method, str):
            if is_notification:
                return None
            return jsonrpc_error(INVALID_REQUEST, "Invalid Request: method is required", req_id)

        handler = self._get_method_handler(method)
        if handler is None:
            if is_notification:
                return None
            return jsonrpc_error(METHOD_NOT_FOUND, f"Method not found: {method}", req_id)

        try:
            result = handler(params, user)
            if is_notification:
                return None
            return jsonrpc_result(result, req_id)
        except InvalidParamsError as e:
            if is_notification:
                return None
            return jsonrpc_error(INVALID_PARAMS, str(e), req_id)
        except Exception as e:
            logger.exception("MCP method %s failed", method)
            if is_notification:
                return None
            return jsonrpc_error(INTERNAL_ERROR, f"Internal error: {e}", req_id)

    def _get_method_handler(self, method):
        handlers = {
            "initialize": self._handle_initialize,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
        }
        return handlers.get(method)

    def _handle_initialize(self, params, user):
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "Open GRC MCP Server",
                "version": "1.0.0",
            },
        }

    def _handle_ping(self, params, user):
        return {}

    def _handle_tools_list(self, params, user):
        tools = []
        for tool_def in self._tools.values():
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"],
            })

        # Handle pagination cursor (optional)
        cursor = (params or {}).get("cursor")
        return {"tools": tools}

    def _handle_tools_call(self, params, user):
        if not params or "name" not in params:
            raise InvalidParamsError("Tool name is required.")

        tool_name = params["name"]
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            raise InvalidParamsError(f"Unknown tool: {tool_name}")

        tool_def = self._tools[tool_name]
        result = tool_def["handler"](user, arguments)

        # Wrap result in MCP content format
        if isinstance(result, dict) and "content" in result and "isError" in result:
            return result

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, default=str, ensure_ascii=False),
                }
            ],
            "isError": False,
        }


class InvalidParamsError(Exception):
    pass
