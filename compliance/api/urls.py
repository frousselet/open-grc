from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"frameworks", views.FrameworkViewSet)
router.register(r"sections", views.SectionViewSet)
router.register(r"requirements", views.RequirementViewSet)
router.register(r"assessments", views.ComplianceAssessmentViewSet)
router.register(r"mappings", views.RequirementMappingViewSet)
router.register(r"action-plans", views.ComplianceActionPlanViewSet)

# Nested routes for assessment results
assessment_results = views.AssessmentResultViewSet.as_view({
    "get": "list",
    "post": "create",
})
assessment_result_detail = views.AssessmentResultViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

app_name = "compliance-api"

urlpatterns = [
    path("", include(router.urls)),
    # Assessment results
    path(
        "assessments/<uuid:assessment_pk>/results/",
        assessment_results,
        name="assessment-results-list",
    ),
    path(
        "assessments/<uuid:assessment_pk>/results/<uuid:pk>/",
        assessment_result_detail,
        name="assessment-results-detail",
    ),
]
