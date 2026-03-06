"""URL configuration for open-grc project."""

from django.contrib import admin
from django.urls import include, path

from mcp.views import OAuthAuthorizeView, oauth_authorization_server_metadata

from .views import CalendarEventsView, CalendarView, DashboardIndicatorsPartialView, GeneralDashboardView, GlobalSearchView

urlpatterns = [
    # OAuth 2.0 Authorization Server Metadata (RFC 8414) - must be at root
    path(".well-known/oauth-authorization-server", oauth_authorization_server_metadata, name="oauth-as-metadata"),

    # OAuth 2.0 Authorization Endpoint - must be at root
    path("authorize", OAuthAuthorizeView.as_view(), name="oauth-authorize"),

    path("i18n/", include("django.conf.urls.i18n")),
    path("", GeneralDashboardView.as_view(), name="home"),
    path("dashboard/indicators-partial/", DashboardIndicatorsPartialView.as_view(), name="dashboard-indicators-partial"),
    path("calendar/", CalendarView.as_view(), name="calendar"),
    path("api/calendar-events/", CalendarEventsView.as_view(), name="calendar-events"),
    path("api/search/", GlobalSearchView.as_view(), name="global-search"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("helpers/", include("helpers.urls")),
    path("context/", include("context.urls")),
    path("assets/", include("assets.urls")),
    path("compliance/", include("compliance.urls")),
    path("risks/", include("risks.urls")),
    path("api/v1/", include("accounts.api.urls")),
    path("api/v1/context/", include("context.api.urls")),
    path("api/v1/assets/", include("assets.api.urls")),
    path("api/v1/compliance/", include("compliance.api.urls")),
    path("api/v1/risks/", include("risks.api.urls")),
    path("api/v1/", include("mcp.urls")),
]
