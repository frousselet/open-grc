from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"scopes", views.ScopeViewSet)
router.register(r"sites", views.SiteViewSet)
router.register(r"issues", views.IssueViewSet)
router.register(r"stakeholders", views.StakeholderViewSet)
router.register(r"objectives", views.ObjectiveViewSet)
router.register(r"swot-analyses", views.SwotAnalysisViewSet)
router.register(r"roles", views.RoleViewSet)
router.register(r"activities", views.ActivityViewSet)
router.register(r"tags", views.TagViewSet)

# Nested routes for sub-entities
stakeholder_expectations = views.StakeholderExpectationViewSet.as_view({
    "get": "list",
    "post": "create",
})
stakeholder_expectation_detail = views.StakeholderExpectationViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

swot_items = views.SwotItemViewSet.as_view({
    "get": "list",
    "post": "create",
})
swot_item_detail = views.SwotItemViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
swot_items_reorder = views.SwotItemViewSet.as_view({
    "patch": "reorder",
})

role_responsibilities = views.ResponsibilityViewSet.as_view({
    "get": "list",
    "post": "create",
})
role_responsibility_detail = views.ResponsibilityViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

app_name = "context-api"

urlpatterns = [
    path("", include(router.urls)),
    # Stakeholder expectations
    path(
        "stakeholders/<uuid:stakeholder_pk>/expectations/",
        stakeholder_expectations,
        name="stakeholder-expectations-list",
    ),
    path(
        "stakeholders/<uuid:stakeholder_pk>/expectations/<uuid:pk>/",
        stakeholder_expectation_detail,
        name="stakeholder-expectations-detail",
    ),
    # SWOT items
    path(
        "swot-analyses/<uuid:analysis_pk>/items/",
        swot_items,
        name="swot-items-list",
    ),
    path(
        "swot-analyses/<uuid:analysis_pk>/items/reorder/",
        swot_items_reorder,
        name="swot-items-reorder",
    ),
    path(
        "swot-analyses/<uuid:analysis_pk>/items/<uuid:pk>/",
        swot_item_detail,
        name="swot-items-detail",
    ),
    # Role responsibilities
    path(
        "roles/<uuid:role_pk>/responsibilities/",
        role_responsibilities,
        name="role-responsibilities-list",
    ),
    path(
        "roles/<uuid:role_pk>/responsibilities/<uuid:pk>/",
        role_responsibility_detail,
        name="role-responsibilities-detail",
    ),
]
