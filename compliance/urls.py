from django.urls import path, reverse_lazy

from . import views
from .models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    Framework,
    Requirement,
)

app_name = "compliance"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Frameworks
    path("frameworks/", views.FrameworkListView.as_view(), name="framework-list"),
    path("frameworks/import/", views.FrameworkImportView.as_view(), name="framework-import"),
    path("frameworks/import/preview/", views.FrameworkImportPreviewView.as_view(), name="framework-import-preview"),
    path("frameworks/import/sample/", views.FrameworkImportSampleView.as_view(), name="framework-import-sample"),
    path("frameworks/create/", views.FrameworkCreateView.as_view(), name="framework-create"),
    path("frameworks/<uuid:pk>/", views.FrameworkDetailView.as_view(), name="framework-detail"),
    path("frameworks/<uuid:pk>/edit/", views.FrameworkUpdateView.as_view(), name="framework-update"),
    path("frameworks/<uuid:pk>/delete/", views.FrameworkDeleteView.as_view(), name="framework-delete"),
    path("frameworks/<uuid:pk>/approve/", views.ApproveView.as_view(model=Framework, success_url=reverse_lazy("compliance:framework-list")), name="framework-approve"),
    # Requirements
    path("requirements/", views.RequirementListView.as_view(), name="requirement-list"),
    path("requirements/create/", views.RequirementCreateView.as_view(), name="requirement-create"),
    path("requirements/<uuid:pk>/", views.RequirementDetailView.as_view(), name="requirement-detail"),
    path("requirements/<uuid:pk>/edit/", views.RequirementUpdateView.as_view(), name="requirement-update"),
    path("requirements/<uuid:pk>/delete/", views.RequirementDeleteView.as_view(), name="requirement-delete"),
    path("requirements/<uuid:pk>/approve/", views.ApproveView.as_view(model=Requirement, success_url=reverse_lazy("compliance:requirement-list")), name="requirement-approve"),
    # Assessments
    path("assessments/", views.AssessmentListView.as_view(), name="assessment-list"),
    path("assessments/create/", views.AssessmentCreateView.as_view(), name="assessment-create"),
    path("assessments/<uuid:pk>/", views.AssessmentDetailView.as_view(), name="assessment-detail"),
    path("assessments/<uuid:pk>/edit/", views.AssessmentUpdateView.as_view(), name="assessment-update"),
    path("assessments/<uuid:pk>/delete/", views.AssessmentDeleteView.as_view(), name="assessment-delete"),
    path("assessments/<uuid:pk>/approve/", views.ApproveView.as_view(model=ComplianceAssessment, permission_feature="assessment", success_url=reverse_lazy("compliance:assessment-list")), name="assessment-approve"),
    # Mappings
    path("mappings/", views.MappingListView.as_view(), name="mapping-list"),
    path("mappings/create/", views.MappingCreateView.as_view(), name="mapping-create"),
    path("mappings/<uuid:pk>/", views.MappingDetailView.as_view(), name="mapping-detail"),
    path("mappings/<uuid:pk>/edit/", views.MappingUpdateView.as_view(), name="mapping-update"),
    path("mappings/<uuid:pk>/delete/", views.MappingDeleteView.as_view(), name="mapping-delete"),
    # Action Plans
    path("action-plans/", views.ActionPlanListView.as_view(), name="action-plan-list"),
    path("action-plans/create/", views.ActionPlanCreateView.as_view(), name="action-plan-create"),
    path("action-plans/<uuid:pk>/", views.ActionPlanDetailView.as_view(), name="action-plan-detail"),
    path("action-plans/<uuid:pk>/edit/", views.ActionPlanUpdateView.as_view(), name="action-plan-update"),
    path("action-plans/<uuid:pk>/delete/", views.ActionPlanDeleteView.as_view(), name="action-plan-delete"),
    path("action-plans/<uuid:pk>/approve/", views.ApproveView.as_view(model=ComplianceActionPlan, permission_feature="action_plan", success_url=reverse_lazy("compliance:action-plan-list")), name="action-plan-approve"),
]
