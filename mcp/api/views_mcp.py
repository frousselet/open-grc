"""
MCP Streamable HTTP transport endpoint.

Implements the MCP 2025-03-26 Streamable HTTP transport:
- POST /mcp: Accept JSON-RPC requests, return JSON-RPC responses
- GET /mcp: SSE stream for server-initiated notifications (optional)
"""

import json
import logging
import secrets

from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mcp.api.authentication import OAuthTokenAuthentication
from mcp.server import McpServer
from mcp.tools import register_all_tools

logger = logging.getLogger(__name__)

# Singleton server instance (tools registered once)
_server = None
_server_lock = False


def get_mcp_server():
    """Get or create the singleton MCP server with all tools registered."""
    global _server, _server_lock
    if _server is None and not _server_lock:
        _server_lock = True
        srv = McpServer()
        register_all_tools(srv)
        _server = srv
        _server_lock = False
    return _server


@method_decorator(csrf_exempt, name="dispatch")
class McpEndpointView(View):
    """MCP Streamable HTTP endpoint."""

    def dispatch(self, request, *args, **kwargs):
        # Allow DELETE without strict authentication so clients can always
        # disconnect (e.g. when the token has already expired).
        if request.method == "DELETE":
            self._try_authenticate(request)
            return self.delete(request)

        # Authenticate via OAuth Bearer token
        auth = OAuthTokenAuthentication()
        try:
            result = auth.authenticate(request)
        except Exception as e:
            logger.exception("Authentication error in MCP endpoint")
            return JsonResponse(
                {
                    "error": "authentication_failed",
                    "message": "Authentication failed.",
                },
                status=401,
            )

        if result is None:
            return JsonResponse(
                {"error": "authentication_required", "message": "Bearer token required."},
                status=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.user, request.auth = result

        # Check MCP access permission
        user = request.user
        if not user.is_superuser and not user.has_perm("system.mcp.access"):
            return JsonResponse(
                {"error": "access_denied", "message": "MCP access not permitted."},
                status=403,
            )

        return super().dispatch(request, *args, **kwargs)

    def _try_authenticate(self, request):
        """Best-effort authentication for DELETE — never raises."""
        from django.contrib.auth.models import AnonymousUser

        request.auth = None
        if not hasattr(request, "user") or request.user is None:
            request.user = AnonymousUser()
        try:
            auth = OAuthTokenAuthentication()
            result = auth.authenticate(request)
            if result is not None:
                request.user, request.auth = result
        except Exception:
            pass

    def post(self, request):
        """Handle JSON-RPC requests from MCP clients."""
        content_type = request.content_type or ""
        if "json" not in content_type and content_type != "":
            return JsonResponse(
                {"error": "invalid_content_type", "message": "Content-Type must be application/json"},
                status=415,
            )

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
                status=200,
            )

        server = get_mcp_server()
        result = server.handle_request(body, request.user)

        if result is None:
            # Notification: no response needed, return 202
            return JsonResponse({}, status=202)

        # Add session ID header
        response = JsonResponse(result, safe=False)
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id:
            response["Mcp-Session-Id"] = session_id
        return response

    def get(self, request):
        """SSE stream for server-initiated notifications.
        Currently returns an empty stream since we don't have server-push features yet.
        """
        def event_stream():
            # Send initial comment to keep connection alive
            yield ": MCP SSE stream connected\n\n"
            # We don't currently have server-initiated notifications
            # The stream stays open for future use
            yield "event: endpoint\ndata: /api/v1/mcp\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id:
            response["Mcp-Session-Id"] = session_id
        return response

    def delete(self, request):
        """Terminate an MCP session and revoke the access token."""
        # Revoke the access token so the session is truly closed.
        if getattr(request, "auth", None) is not None:
            try:
                request.auth.delete()
            except Exception:
                logger.debug("Token already deleted during session termination")
        return JsonResponse({"status": "session_terminated"}, status=200)


@csrf_exempt
def mcp_metadata_view(request):
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728).
    Helps MCP clients discover the authorization server.
    """
    if request.method != "GET":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    # Build base URL from request
    scheme = request.scheme
    host = request.get_host()
    base_url = f"{scheme}://{host}"

    return JsonResponse({
        "resource": f"{base_url}/api/v1/mcp",
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base_url}/api/v1/mcp/.well-known/oauth-protected-resource",
    })
