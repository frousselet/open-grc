"""
OAuth 2.0 Authorization endpoint for the Authorization Code + PKCE flow.

This is used by MCP clients like Claude.ai that need interactive user consent.
The flow:
  1. Client redirects user to /authorize with PKCE params
  2. User logs in (if needed) and approves
  3. Server redirects back to client with an authorization code
  4. Client exchanges code + code_verifier for an access token at /oauth/token/
"""

import base64
import hashlib
import logging
from urllib.parse import urlencode, urlparse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views import View

from mcp.models import OAuthAuthorizationCode

logger = logging.getLogger(__name__)


def _validate_authorize_params(params):
    """Validate OAuth authorize request parameters. Returns (errors, cleaned) tuple."""
    errors = []

    response_type = params.get("response_type")
    if response_type != "code":
        errors.append("response_type must be 'code'.")

    client_id = params.get("client_id", "").strip()
    if not client_id:
        errors.append("client_id is required.")

    redirect_uri = params.get("redirect_uri", "").strip()
    if not redirect_uri:
        errors.append("redirect_uri is required.")
    elif not redirect_uri.startswith("https://"):
        # Allow http://localhost for development
        parsed = urlparse(redirect_uri)
        if parsed.hostname not in ("localhost", "127.0.0.1"):
            errors.append("redirect_uri must use HTTPS.")

    code_challenge = params.get("code_challenge", "").strip()
    if not code_challenge:
        errors.append("code_challenge is required (PKCE).")

    code_challenge_method = params.get("code_challenge_method", "S256").strip()
    if code_challenge_method != "S256":
        errors.append("code_challenge_method must be S256.")

    state = params.get("state", "").strip()
    scope = params.get("scope", "").strip()

    return errors, {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state,
        "scope": scope,
    }


def verify_code_challenge(code_verifier, code_challenge, method="S256"):
    """Verify PKCE code_verifier against stored code_challenge."""
    if method != "S256":
        return False
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return computed == code_challenge


class OAuthAuthorizeView(LoginRequiredMixin, View):
    """OAuth 2.0 Authorization endpoint with PKCE support."""

    login_url = "/accounts/login/"

    def get(self, request):
        errors, params = _validate_authorize_params(request.GET)
        if errors:
            return HttpResponseBadRequest(
                f"Invalid OAuth request: {'; '.join(errors)}"
            )

        # Check MCP access permission
        user = request.user
        if not user.is_superuser and not user.has_perm("system.mcp.access"):
            return render(request, "mcp/authorize.html", {
                "error": _("You do not have permission to access the MCP server."),
                "params": params,
            })

        return render(request, "mcp/authorize.html", {
            "params": params,
            "client_id": params["client_id"],
            "scope": params["scope"],
            "redirect_uri": params["redirect_uri"],
        })

    def post(self, request):
        errors, params = _validate_authorize_params(request.POST)
        if errors:
            return HttpResponseBadRequest(
                f"Invalid OAuth request: {'; '.join(errors)}"
            )

        action = request.POST.get("action")

        if action == "deny":
            # Redirect back with error
            qs = urlencode({
                "error": "access_denied",
                "error_description": "User denied the request.",
                "state": params["state"],
            })
            return HttpResponseRedirect(f"{params['redirect_uri']}?{qs}")

        # action == "approve" (or default)
        user = request.user
        if not user.is_superuser and not user.has_perm("system.mcp.access"):
            qs = urlencode({
                "error": "access_denied",
                "error_description": "User does not have MCP access permission.",
                "state": params["state"],
            })
            return HttpResponseRedirect(f"{params['redirect_uri']}?{qs}")

        # Create authorization code
        auth_code, raw_code = OAuthAuthorizationCode.create_code(
            user=user,
            client_id=params["client_id"],
            redirect_uri=params["redirect_uri"],
            code_challenge=params["code_challenge"],
            code_challenge_method=params["code_challenge_method"],
            scope=params["scope"],
            state=params["state"],
        )

        # Redirect back to client with the code
        redirect_params = {"code": raw_code}
        if params["state"]:
            redirect_params["state"] = params["state"]
        qs = urlencode(redirect_params)
        return HttpResponseRedirect(f"{params['redirect_uri']}?{qs}")
