"""Web views for OAuth credential management and authorization."""

import json
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mcp.models import OAuthApplication, OAuthAuthorizationCode
from mcp.models.oauth import _generate_client_secret


@csrf_exempt
def oauth_authorization_server_metadata(request):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    if request.method != "GET":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    scheme = request.scheme
    host = request.get_host()
    base_url = f"{scheme}://{host}"

    return JsonResponse({
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/api/v1/oauth/token/",
        "registration_endpoint": f"{base_url}/api/v1/oauth/register/",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "scopes_supported": ["claudeai"],
    })


class OAuthAuthorizeView(View):
    """OAuth 2.0 Authorization Endpoint (Authorization Code + PKCE)."""

    def get(self, request):
        response_type = request.GET.get("response_type")
        client_id = request.GET.get("client_id")
        redirect_uri = request.GET.get("redirect_uri")
        code_challenge = request.GET.get("code_challenge")
        code_challenge_method = request.GET.get("code_challenge_method", "S256")
        state = request.GET.get("state", "")
        scope = request.GET.get("scope", "")

        # Validate required params
        if response_type != "code":
            return JsonResponse(
                {"error": "unsupported_response_type", "error_description": "Only response_type=code is supported."},
                status=400,
            )

        if not client_id or not redirect_uri or not code_challenge:
            return JsonResponse(
                {"error": "invalid_request", "error_description": "client_id, redirect_uri, and code_challenge are required."},
                status=400,
            )

        if code_challenge_method != "S256":
            return JsonResponse(
                {"error": "invalid_request", "error_description": "Only S256 code_challenge_method is supported."},
                status=400,
            )

        # Validate client exists
        try:
            app = OAuthApplication.objects.get(client_id=client_id, is_active=True)
        except OAuthApplication.DoesNotExist:
            return JsonResponse(
                {"error": "invalid_client", "error_description": "Unknown client_id."},
                status=400,
            )

        # Validate redirect_uri
        if not app.validate_redirect_uri(redirect_uri):
            return JsonResponse(
                {"error": "invalid_request", "error_description": "Invalid redirect_uri."},
                status=400,
            )

        # If user is not authenticated, redirect to login with return URL
        if not request.user.is_authenticated:
            login_url = settings.LOGIN_URL
            # Preserve the full authorize URL as the next parameter
            authorize_url = request.get_full_path()
            return HttpResponseRedirect(f"{login_url}?next={authorize_url}")

        # User is authenticated - show consent page
        return render(request, "mcp/authorize.html", {
            "app": app,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "state": state,
            "scope": scope,
        })

    def post(self, request):
        """Handle consent form submission."""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "login_required"}, status=401)

        client_id = request.POST.get("client_id")
        redirect_uri = request.POST.get("redirect_uri")
        code_challenge = request.POST.get("code_challenge")
        code_challenge_method = request.POST.get("code_challenge_method", "S256")
        state = request.POST.get("state", "")
        scope = request.POST.get("scope", "")
        action = request.POST.get("action")

        if action == "deny":
            params = urlencode({"error": "access_denied", "state": state})
            return HttpResponseRedirect(f"{redirect_uri}?{params}")

        # Validate client
        try:
            app = OAuthApplication.objects.get(client_id=client_id, is_active=True)
        except OAuthApplication.DoesNotExist:
            return JsonResponse({"error": "invalid_client"}, status=400)

        if not app.validate_redirect_uri(redirect_uri):
            return JsonResponse({"error": "invalid_redirect_uri"}, status=400)

        # Reassign the application to the authorizing user (for dynamic clients)
        if app.is_public_client and app.user.email == "system@mcp.internal":
            app.user = request.user
            app.save(update_fields=["user"])

        # Generate authorization code
        _, raw_code = OAuthAuthorizationCode.create_code(
            client_id=client_id,
            user=request.user,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope,
        )

        # Redirect back to client with the authorization code
        params = {"code": raw_code}
        if state:
            params["state"] = state
        return HttpResponseRedirect(f"{redirect_uri}?{urlencode(params)}")


class OAuthAppCreateView(LoginRequiredMixin, View):
    """Create a new OAuth application (AJAX)."""

    def post(self, request):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.create"):
            return JsonResponse({"error": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON."}, status=400)

        name = (body.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "Name is required."}, status=400)

        raw_secret = _generate_client_secret()
        app = OAuthApplication(name=name, user=request.user)
        app.set_secret(raw_secret)
        app.save()

        return JsonResponse({
            "status": "ok",
            "client_id": app.client_id,
            "client_secret": raw_secret,
        })


class OAuthAppDeleteView(LoginRequiredMixin, View):
    """Delete an OAuth application (AJAX)."""

    def post(self, request, pk):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.delete"):
            return JsonResponse({"error": "Permission denied."}, status=403)

        try:
            app = OAuthApplication.objects.get(pk=pk, user=request.user)
        except OAuthApplication.DoesNotExist:
            return JsonResponse({"error": "Not found."}, status=404)

        app.delete()
        return JsonResponse({"status": "ok"})


class OAuthAppListView(LoginRequiredMixin, View):
    """Return rendered HTML for the OAuth app list (AJAX partial refresh)."""

    def get(self, request):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.read"):
            return JsonResponse({"html": ""})

        oauth_apps = request.user.oauth_applications.order_by("-created_at")
        html = render_to_string(
            "mcp/partials/oauth_app_list.html",
            {"oauth_apps": oauth_apps},
            request=request,
        )
        return JsonResponse({"html": html})
