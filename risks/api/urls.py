from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"assessments", views.RiskAssessmentViewSet)
router.register(r"criteria", views.RiskCriteriaViewSet)
router.register(r"risks", views.RiskViewSet)
router.register(r"treatment-plans", views.RiskTreatmentPlanViewSet)
router.register(r"acceptances", views.RiskAcceptanceViewSet)
router.register(r"threats", views.ThreatViewSet)
router.register(r"vulnerabilities", views.VulnerabilityViewSet)
router.register(r"iso27005-risks", views.ISO27005RiskViewSet)

app_name = "risks-api"

urlpatterns = [
    path("", include(router.urls)),
]
