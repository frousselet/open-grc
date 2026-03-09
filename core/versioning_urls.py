from django.urls import path

from .versioning_views import (
    VersioningConfigCreateView,
    VersioningConfigDeleteView,
    VersioningConfigListView,
    VersioningConfigUpdateView,
    VersioningFieldChoicesView,
)

app_name = "core"

urlpatterns = [
    path(
        "versioning/",
        VersioningConfigListView.as_view(),
        name="versioning-config-list",
    ),
    path(
        "versioning/create/",
        VersioningConfigCreateView.as_view(),
        name="versioning-config-create",
    ),
    path(
        "versioning/<int:pk>/edit/",
        VersioningConfigUpdateView.as_view(),
        name="versioning-config-update",
    ),
    path(
        "versioning/<int:pk>/delete/",
        VersioningConfigDeleteView.as_view(),
        name="versioning-config-delete",
    ),
    path(
        "versioning/field-choices/",
        VersioningFieldChoicesView.as_view(),
        name="versioning-field-choices",
    ),
]
