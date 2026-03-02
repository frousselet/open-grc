import base64
import hashlib
import json

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from mcp.models import OAuthAccessToken, OAuthApplication, OAuthAuthorizationCode
from mcp.models.oauth import _generate_client_id, _generate_client_secret


class OAuthTokenView(APIView):
    """OAuth 2.0 token endpoint supporting client_credentials and authorization_code grants."""

    permission_classes = [AllowAny]
    authentication_classes = []
    renderer_classes = [JSONRenderer]  # Bypass StandardJSONRenderer wrapping

    def post(self, request):
        grant_type = request.data.get("grant_type")

        if grant_type == "authorization_code":
            return self._handle_authorization_code(request)
        elif grant_type == "client_credentials":
            return self._handle_client_credentials(request)
        else:
            return Response(
                {"error": "unsupported_grant_type", "error_description": "Supported: authorization_code, client_credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def _handle_authorization_code(self, request):
        code = request.data.get("code")
        client_id = request.data.get("client_id")
        redirect_uri = request.data.get("redirect_uri")
        code_verifier = request.data.get("code_verifier")

        if not code or not client_id or not redirect_uri or not code_verifier:
            return Response(
                {"error": "invalid_request", "error_description": "code, client_id, redirect_uri, and code_verifier are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the authorization code
        code_hash = OAuthAuthorizationCode.hash_code(code)
        try:
            auth_code = OAuthAuthorizationCode.objects.select_related("user").get(
                code_hash=code_hash,
            )
        except OAuthAuthorizationCode.DoesNotExist:
            return Response(
                {"error": "invalid_grant", "error_description": "Invalid authorization code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the code
        if auth_code.used:
            return Response(
                {"error": "invalid_grant", "error_description": "Authorization code already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if auth_code.is_expired:
            return Response(
                {"error": "invalid_grant", "error_description": "Authorization code expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if auth_code.client_id != client_id:
            return Response(
                {"error": "invalid_grant", "error_description": "Client ID mismatch."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if auth_code.redirect_uri != redirect_uri:
            return Response(
                {"error": "invalid_grant", "error_description": "Redirect URI mismatch."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify PKCE code_verifier against code_challenge
        if auth_code.code_challenge_method == "S256":
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
            if computed_challenge != auth_code.code_challenge:
                return Response(
                    {"error": "invalid_grant", "error_description": "PKCE verification failed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": "invalid_request", "error_description": "Unsupported code_challenge_method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark the code as used
        auth_code.used = True
        auth_code.save(update_fields=["used"])

        # Find or create the application for token tracking
        try:
            app = OAuthApplication.objects.get(client_id=client_id, is_active=True)
        except OAuthApplication.DoesNotExist:
            return Response(
                {"error": "invalid_client", "error_description": "Invalid client."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Issue access token
        token_obj, raw_token = OAuthAccessToken.create_token(app, lifetime_seconds=3600)

        return Response({
            "access_token": raw_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        })

    def _handle_client_credentials(self, request):
        client_id = request.data.get("client_id")
        client_secret = request.data.get("client_secret")

        if not client_id or not client_secret:
            return Response(
                {"error": "invalid_request", "error_description": "client_id and client_secret are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app = OAuthApplication.objects.select_related("user").get(
                client_id=client_id, is_active=True,
            )
        except OAuthApplication.DoesNotExist:
            return Response(
                {"error": "invalid_client", "error_description": "Invalid client credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not app.verify_secret(client_secret):
            return Response(
                {"error": "invalid_client", "error_description": "Invalid client credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not app.user.is_active:
            return Response(
                {"error": "invalid_client", "error_description": "User account is disabled."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check that user has MCP access permission
        if not app.user.is_superuser and not app.user.has_perm("system.mcp.access"):
            return Response(
                {"error": "access_denied", "error_description": "User does not have MCP access."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Issue access token (1 hour lifetime)
        token_obj, raw_token = OAuthAccessToken.create_token(app, lifetime_seconds=3600)

        return Response({
            "access_token": raw_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        })


class OAuthRegisterView(APIView):
    """OAuth 2.0 Dynamic Client Registration (RFC 7591)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    renderer_classes = [JSONRenderer]

    def post(self, request):
        client_name = request.data.get("client_name", "MCP Client")
        redirect_uris = request.data.get("redirect_uris", [])
        grant_types = request.data.get("grant_types", ["authorization_code"])
        token_endpoint_auth_method = request.data.get("token_endpoint_auth_method", "none")

        if not isinstance(redirect_uris, list):
            return Response(
                {"error": "invalid_client_metadata", "error_description": "redirect_uris must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a public client (no secret needed for PKCE flow)
        app = OAuthApplication(
            name=client_name,
            # Assign to a default system user - will be overridden at authorization time
            user_id=self._get_default_user_id(),
            client_secret_hash="",
            redirect_uris=json.dumps(redirect_uris),
            token_endpoint_auth_method=token_endpoint_auth_method,
        )
        app.save()

        response_data = {
            "client_id": app.client_id,
            "client_name": app.name,
            "redirect_uris": redirect_uris,
            "grant_types": grant_types,
            "token_endpoint_auth_method": token_endpoint_auth_method,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    def _get_default_user_id(self):
        """Get or create a default system user for dynamically registered clients."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            email="system@mcp.internal",
            defaults={"first_name": "MCP", "last_name": "System", "is_active": True},
        )
        return user.pk


class OAuthApplicationListCreateView(APIView):
    """List and create OAuth applications for the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # For list: check read permission
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.read"):
            return Response(
                {"status": "error", "error": {"message": "Permission denied."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        apps = OAuthApplication.objects.filter(user=request.user).order_by("-created_at")
        data = [
            {
                "id": str(app.id),
                "name": app.name,
                "client_id": app.client_id,
                "is_active": app.is_active,
                "last_used_at": app.last_used_at.isoformat() if app.last_used_at else None,
                "created_at": app.created_at.isoformat(),
            }
            for app in apps
        ]
        return Response({"status": "success", "data": data})

    def post(self, request):
        # For create: check create permission
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.create"):
            return Response(
                {"status": "error", "error": {"message": "Permission denied."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"status": "error", "error": {"message": "Application name is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_secret = _generate_client_secret()
        app = OAuthApplication(name=name, user=request.user)
        app.set_secret(raw_secret)
        app.save()

        # Return the secret only once at creation time
        return Response(
            {
                "status": "success",
                "data": {
                    "id": str(app.id),
                    "name": app.name,
                    "client_id": app.client_id,
                    "client_secret": raw_secret,
                    "created_at": app.created_at.isoformat(),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class OAuthApplicationDetailView(APIView):
    """Retrieve or delete a specific OAuth application."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.read"):
            return Response(
                {"status": "error", "error": {"message": "Permission denied."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            app = OAuthApplication.objects.get(pk=pk, user=request.user)
        except OAuthApplication.DoesNotExist:
            return Response(
                {"status": "error", "error": {"message": "Not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "status": "success",
            "data": {
                "id": str(app.id),
                "name": app.name,
                "client_id": app.client_id,
                "is_active": app.is_active,
                "last_used_at": app.last_used_at.isoformat() if app.last_used_at else None,
                "created_at": app.created_at.isoformat(),
            },
        })

    def delete(self, request, pk):
        if not request.user.is_superuser and not request.user.has_perm("system.oauth.delete"):
            return Response(
                {"status": "error", "error": {"message": "Permission denied."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            app = OAuthApplication.objects.get(pk=pk, user=request.user)
        except OAuthApplication.DoesNotExist:
            return Response(
                {"status": "error", "error": {"message": "Not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        app.delete()
        return Response({"status": "success"}, status=status.HTTP_204_NO_CONTENT)
