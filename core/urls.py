"""URL configuration for open-grc project."""

from django.contrib import admin
from django.urls import include, path

from .views import GeneralDashboardView

urlpatterns = [
    path("", GeneralDashboardView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("context/", include("context.urls")),
    path("assets/", include("assets.urls")),
    path("compliance/", include("compliance.urls")),
    path("risks/", include("risks.urls")),
    path("api/v1/", include("accounts.api.urls")),
    path("api/v1/context/", include("context.api.urls")),
    path("api/v1/assets/", include("assets.api.urls")),
    path("api/v1/compliance/", include("compliance.api.urls")),
    path("api/v1/risks/", include("risks.api.urls")),
]
