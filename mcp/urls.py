from django.urls import path

from mcp.api.views_mcp import McpEndpointView, mcp_metadata_view
from mcp.api.views_oauth import (
    OAuthApplicationDetailView,
    OAuthApplicationListCreateView,
    OAuthRegisterView,
    OAuthTokenView,
)

app_name = "mcp"

urlpatterns = [
    # OAuth 2.0 endpoints
    path("oauth/token/", OAuthTokenView.as_view(), name="oauth-token"),
    path("oauth/register/", OAuthRegisterView.as_view(), name="oauth-register"),
    path("oauth/applications/", OAuthApplicationListCreateView.as_view(), name="oauth-applications"),
    path("oauth/applications/<uuid:pk>/", OAuthApplicationDetailView.as_view(), name="oauth-application-detail"),

    # MCP Streamable HTTP endpoint
    path("mcp", McpEndpointView.as_view(), name="mcp-endpoint"),

    # OAuth Protected Resource Metadata
    path("mcp/.well-known/oauth-protected-resource", mcp_metadata_view, name="mcp-metadata"),
]
