from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from mcp.models import OAuthAccessToken, OAuthApplication
from mcp.models.oauth import _generate_client_secret


class OAuthTokenView(APIView):
    """OAuth 2.0 token endpoint implementing client_credentials grant."""

    permission_classes = [AllowAny]
    authentication_classes = []
    renderer_classes = [JSONRenderer]  # Bypass StandardJSONRenderer wrapping

    def post(self, request):
        grant_type = request.data.get("grant_type")
        if grant_type != "client_credentials":
            return Response(
                {"error": "unsupported_grant_type", "error_description": "Only client_credentials is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
