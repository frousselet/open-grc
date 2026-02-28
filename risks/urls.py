from django.urls import path, reverse_lazy

from . import views
from .models import Risk, RiskAssessment, RiskTreatmentPlan

app_name = "risks"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Assessments
    path("assessments/", views.RiskAssessmentListView.as_view(), name="assessment-list"),
    path("assessments/create/", views.RiskAssessmentCreateView.as_view(), name="assessment-create"),
    path("assessments/<uuid:pk>/", views.RiskAssessmentDetailView.as_view(), name="assessment-detail"),
    path("assessments/<uuid:pk>/edit/", views.RiskAssessmentUpdateView.as_view(), name="assessment-update"),
    path("assessments/<uuid:pk>/delete/", views.RiskAssessmentDeleteView.as_view(), name="assessment-delete"),
    path("assessments/<uuid:pk>/approve/", views.ApproveView.as_view(model=RiskAssessment, permission_feature="assessment", success_url=reverse_lazy("risks:assessment-list")), name="assessment-approve"),
    # Criteria
    path("criteria/", views.RiskCriteriaListView.as_view(), name="criteria-list"),
    path("criteria/create/", views.RiskCriteriaCreateView.as_view(), name="criteria-create"),
    path("criteria/<uuid:pk>/", views.RiskCriteriaDetailView.as_view(), name="criteria-detail"),
    path("criteria/<uuid:pk>/edit/", views.RiskCriteriaUpdateView.as_view(), name="criteria-update"),
    path("criteria/<uuid:pk>/delete/", views.RiskCriteriaDeleteView.as_view(), name="criteria-delete"),
    # API (AJAX)
    path("api/scale-choices/", views.scale_choices_api, name="api-scale-choices"),
    # Risk register
    path("register/", views.RiskListView.as_view(), name="risk-list"),
    path("register/create/", views.RiskCreateView.as_view(), name="risk-create"),
    path("register/<uuid:pk>/", views.RiskDetailView.as_view(), name="risk-detail"),
    path("register/<uuid:pk>/edit/", views.RiskUpdateView.as_view(), name="risk-update"),
    path("register/<uuid:pk>/delete/", views.RiskDeleteView.as_view(), name="risk-delete"),
    path("register/<uuid:pk>/approve/", views.ApproveView.as_view(model=Risk, permission_feature="risk", success_url=reverse_lazy("risks:risk-list")), name="risk-approve"),
    # Treatment plans
    path("treatments/", views.TreatmentPlanListView.as_view(), name="treatment-plan-list"),
    path("treatments/create/", views.TreatmentPlanCreateView.as_view(), name="treatment-plan-create"),
    path("treatments/<uuid:pk>/", views.TreatmentPlanDetailView.as_view(), name="treatment-plan-detail"),
    path("treatments/<uuid:pk>/edit/", views.TreatmentPlanUpdateView.as_view(), name="treatment-plan-update"),
    path("treatments/<uuid:pk>/delete/", views.TreatmentPlanDeleteView.as_view(), name="treatment-plan-delete"),
    path("treatments/<uuid:pk>/approve/", views.ApproveView.as_view(model=RiskTreatmentPlan, permission_feature="treatment", success_url=reverse_lazy("risks:treatment-plan-list")), name="treatment-plan-approve"),
    # Acceptances
    path("acceptances/", views.RiskAcceptanceListView.as_view(), name="acceptance-list"),
    path("acceptances/create/", views.RiskAcceptanceCreateView.as_view(), name="acceptance-create"),
    path("acceptances/<uuid:pk>/", views.RiskAcceptanceDetailView.as_view(), name="acceptance-detail"),
    path("acceptances/<uuid:pk>/edit/", views.RiskAcceptanceUpdateView.as_view(), name="acceptance-update"),
    path("acceptances/<uuid:pk>/delete/", views.RiskAcceptanceDeleteView.as_view(), name="acceptance-delete"),
    # Threats
    path("threats/", views.ThreatListView.as_view(), name="threat-list"),
    path("threats/create/", views.ThreatCreateView.as_view(), name="threat-create"),
    path("threats/<uuid:pk>/", views.ThreatDetailView.as_view(), name="threat-detail"),
    path("threats/<uuid:pk>/edit/", views.ThreatUpdateView.as_view(), name="threat-update"),
    path("threats/<uuid:pk>/delete/", views.ThreatDeleteView.as_view(), name="threat-delete"),
    # Vulnerabilities
    path("vulnerabilities/", views.VulnerabilityListView.as_view(), name="vulnerability-list"),
    path("vulnerabilities/create/", views.VulnerabilityCreateView.as_view(), name="vulnerability-create"),
    path("vulnerabilities/<uuid:pk>/", views.VulnerabilityDetailView.as_view(), name="vulnerability-detail"),
    path("vulnerabilities/<uuid:pk>/edit/", views.VulnerabilityUpdateView.as_view(), name="vulnerability-update"),
    path("vulnerabilities/<uuid:pk>/delete/", views.VulnerabilityDeleteView.as_view(), name="vulnerability-delete"),
    # ISO 27005 analyses
    path("iso27005/", views.ISO27005RiskListView.as_view(), name="iso27005-list"),
    path("iso27005/create/", views.ISO27005RiskCreateView.as_view(), name="iso27005-create"),
    path("iso27005/<uuid:pk>/", views.ISO27005RiskDetailView.as_view(), name="iso27005-detail"),
    path("iso27005/<uuid:pk>/edit/", views.ISO27005RiskUpdateView.as_view(), name="iso27005-update"),
    path("iso27005/<uuid:pk>/delete/", views.ISO27005RiskDeleteView.as_view(), name="iso27005-delete"),
]
