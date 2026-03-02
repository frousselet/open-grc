from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from mcp.models import OAuthAccessToken


class OAuthTokenAuthentication(BaseAuthentication):
    """Authenticate MCP requests using OAuth 2.0 Bearer tokens."""

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None

        raw_token = auth_header[len(self.keyword) + 1:]
        if not raw_token:
            return None

        token_hash = OAuthAccessToken.hash_token(raw_token)
        try:
            token = OAuthAccessToken.objects.select_related(
                "application__user"
            ).get(token_hash=token_hash)
        except OAuthAccessToken.DoesNotExist:
            raise AuthenticationFailed("Invalid or expired token.")

        if token.is_expired:
            token.delete()
            raise AuthenticationFailed("Token has expired.")

        app = token.application
        if not app.is_active:
            raise AuthenticationFailed("OAuth application is disabled.")

        user = app.user
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        # Update last_used_at on the application
        OAuthApplication = type(app)
        OAuthApplication.objects.filter(pk=app.pk).update(last_used_at=timezone.now())

        return (user, token)

    def authenticate_header(self, request):
        return self.keyword
