from django.urls import path, reverse_lazy

from . import views
from .models import (
    Auditor,
    ComplianceActionPlan,
    ComplianceAssessment,
    ComplianceAudit,
    ComplianceControl,
    ControlBody,
    Finding,
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
    # Controls
    path("controls/", views.ControlListView.as_view(), name="control-list"),
    path("controls/create/", views.ControlCreateView.as_view(), name="control-create"),
    path("controls/<uuid:pk>/", views.ControlDetailView.as_view(), name="control-detail"),
    path("controls/<uuid:pk>/edit/", views.ControlUpdateView.as_view(), name="control-update"),
    path("controls/<uuid:pk>/delete/", views.ControlDeleteView.as_view(), name="control-delete"),
    path("controls/<uuid:pk>/approve/", views.ApproveView.as_view(model=ComplianceControl, permission_feature="control", success_url=reverse_lazy("compliance:control-list")), name="control-approve"),
    # Audits
    path("audits/", views.AuditListView.as_view(), name="audit-list"),
    path("audits/create/", views.AuditCreateView.as_view(), name="audit-create"),
    path("audits/<uuid:pk>/", views.AuditDetailView.as_view(), name="audit-detail"),
    path("audits/<uuid:pk>/edit/", views.AuditUpdateView.as_view(), name="audit-update"),
    path("audits/<uuid:pk>/delete/", views.AuditDeleteView.as_view(), name="audit-delete"),
    path("audits/<uuid:pk>/approve/", views.ApproveView.as_view(model=ComplianceAudit, permission_feature="audit", success_url=reverse_lazy("compliance:audit-list")), name="audit-approve"),
    # Control Bodies & Authorities
    path("control-bodies/", views.ControlBodyListView.as_view(), name="control-body-list"),
    path("control-bodies/create/", views.ControlBodyCreateView.as_view(), name="control-body-create"),
    path("control-bodies/<uuid:pk>/", views.ControlBodyDetailView.as_view(), name="control-body-detail"),
    path("control-bodies/<uuid:pk>/edit/", views.ControlBodyUpdateView.as_view(), name="control-body-update"),
    path("control-bodies/<uuid:pk>/delete/", views.ControlBodyDeleteView.as_view(), name="control-body-delete"),
    path("control-bodies/<uuid:pk>/approve/", views.ApproveView.as_view(model=ControlBody, permission_feature="control_body", success_url=reverse_lazy("compliance:control-body-list")), name="control-body-approve"),
    # Auditors
    path("auditors/create/", views.AuditorCreateView.as_view(), name="auditor-create"),
    path("auditors/<uuid:pk>/edit/", views.AuditorUpdateView.as_view(), name="auditor-update"),
    path("auditors/<uuid:pk>/delete/", views.AuditorDeleteView.as_view(), name="auditor-delete"),
    # Findings
    path("findings/", views.FindingListView.as_view(), name="finding-list"),
    path("findings/create/", views.FindingCreateView.as_view(), name="finding-create"),
    path("findings/<uuid:pk>/", views.FindingDetailView.as_view(), name="finding-detail"),
    path("findings/<uuid:pk>/edit/", views.FindingUpdateView.as_view(), name="finding-update"),
    path("findings/<uuid:pk>/delete/", views.FindingDeleteView.as_view(), name="finding-delete"),
    path("findings/<uuid:pk>/approve/", views.ApproveView.as_view(model=Finding, permission_feature="finding", success_url=reverse_lazy("compliance:finding-list")), name="finding-approve"),
]
