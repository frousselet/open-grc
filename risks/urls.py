from django.urls import path, reverse_lazy

from . import views, views_ebios
from .models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskTreatmentPlan,
    Threat,
    Vulnerability,
)

app_name = "risks"

urlpatterns = [
    path("", views.RiskDashboardView.as_view(), name="dashboard"),
    # Assessments
    path("assessments/", views.RiskAssessmentListView.as_view(), name="assessment-list"),
    path("assessments/create/", views.RiskAssessmentCreateView.as_view(), name="assessment-create"),
    path("assessments/<uuid:pk>/", views.RiskAssessmentDetailView.as_view(), name="assessment-detail"),
    path("assessments/<uuid:pk>/edit/", views.RiskAssessmentUpdateView.as_view(), name="assessment-update"),
    path("assessments/<uuid:pk>/delete/", views.RiskAssessmentDeleteView.as_view(), name="assessment-delete"),
    path("assessments/<uuid:pk>/approve/", views.ApproveView.as_view(model=RiskAssessment, permission_feature="assessment", success_url=reverse_lazy("risks:assessment-list")), name="assessment-approve"),
    path("assessments/<uuid:pk>/export/docx/", views.ISO27005ReportExportView.as_view(), name="assessment-export-docx"),
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
    path("register/export/xlsx/", views.RiskRegisterExportView.as_view(), name="risk-register-export-xlsx"),
    path("register/bulk/", views.RiskBulkActionView.as_view(), name="risk-bulk-action"),
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
    # Treatment actions (inline editing under a plan)
    path("treatments/<uuid:plan_pk>/actions/create/", views.TreatmentActionCreateView.as_view(), name="treatment-action-create"),
    path("treatment-actions/<uuid:pk>/edit/", views.TreatmentActionUpdateView.as_view(), name="treatment-action-update"),
    path("treatment-actions/<uuid:pk>/delete/", views.TreatmentActionDeleteView.as_view(), name="treatment-action-delete"),
    # Acceptances
    path("acceptances/", views.RiskAcceptanceListView.as_view(), name="acceptance-list"),
    path("acceptances/create/", views.RiskAcceptanceCreateView.as_view(), name="acceptance-create"),
    path("acceptances/<uuid:pk>/", views.RiskAcceptanceDetailView.as_view(), name="acceptance-detail"),
    path("acceptances/<uuid:pk>/edit/", views.RiskAcceptanceUpdateView.as_view(), name="acceptance-update"),
    path("acceptances/<uuid:pk>/delete/", views.RiskAcceptanceDeleteView.as_view(), name="acceptance-delete"),
    path("acceptances/<uuid:pk>/approve/", views.ApproveView.as_view(model=RiskAcceptance, permission_feature="acceptance", success_url=reverse_lazy("risks:acceptance-list")), name="acceptance-approve"),
    # Threats
    path("threats/", views.ThreatListView.as_view(), name="threat-list"),
    path("threats/create/", views.ThreatCreateView.as_view(), name="threat-create"),
    path("threats/<uuid:pk>/", views.ThreatDetailView.as_view(), name="threat-detail"),
    path("threats/<uuid:pk>/edit/", views.ThreatUpdateView.as_view(), name="threat-update"),
    path("threats/<uuid:pk>/delete/", views.ThreatDeleteView.as_view(), name="threat-delete"),
    path("threats/<uuid:pk>/approve/", views.ApproveView.as_view(model=Threat, permission_feature="threat", success_url=reverse_lazy("risks:threat-list")), name="threat-approve"),
    # Vulnerabilities
    path("vulnerabilities/", views.VulnerabilityListView.as_view(), name="vulnerability-list"),
    path("vulnerabilities/create/", views.VulnerabilityCreateView.as_view(), name="vulnerability-create"),
    path("vulnerabilities/<uuid:pk>/", views.VulnerabilityDetailView.as_view(), name="vulnerability-detail"),
    path("vulnerabilities/<uuid:pk>/edit/", views.VulnerabilityUpdateView.as_view(), name="vulnerability-update"),
    path("vulnerabilities/<uuid:pk>/delete/", views.VulnerabilityDeleteView.as_view(), name="vulnerability-delete"),
    path("vulnerabilities/<uuid:pk>/approve/", views.ApproveView.as_view(model=Vulnerability, permission_feature="vulnerability", success_url=reverse_lazy("risks:vulnerability-list")), name="vulnerability-approve"),
    # ISO 27005 analyses
    path("iso27005/", views.ISO27005RiskListView.as_view(), name="iso27005-list"),
    path("iso27005/create/", views.ISO27005RiskCreateView.as_view(), name="iso27005-create"),
    path("iso27005/<uuid:pk>/", views.ISO27005RiskDetailView.as_view(), name="iso27005-detail"),
    path("iso27005/<uuid:pk>/edit/", views.ISO27005RiskUpdateView.as_view(), name="iso27005-update"),
    path("iso27005/<uuid:pk>/delete/", views.ISO27005RiskDeleteView.as_view(), name="iso27005-delete"),
    path("iso27005/<uuid:pk>/approve/", views.ApproveView.as_view(model=ISO27005Risk, permission_feature="iso27005", success_url=reverse_lazy("risks:iso27005-list")), name="iso27005-approve"),
    path("iso27005/<uuid:pk>/consolidate/", views.ISO27005ConsolidateView.as_view(), name="iso27005-consolidate"),

    # EBIOS RM workshop transitions and detail pages
    path(
        "assessments/<uuid:assessment_pk>/ebios/workshops/<uuid:workshop_pk>/",
        views_ebios.WorkshopDetailView.as_view(),
        name="ebios-workshop-detail",
    ),
    path(
        "assessments/<uuid:assessment_pk>/ebios/workshops/<uuid:workshop_pk>/start/",
        views_ebios.WorkshopStartView.as_view(),
        name="ebios-workshop-start",
    ),
    path(
        "assessments/<uuid:assessment_pk>/ebios/workshops/<uuid:workshop_pk>/submit/",
        views_ebios.WorkshopSubmitView.as_view(),
        name="ebios-workshop-submit",
    ),
    path(
        "assessments/<uuid:assessment_pk>/ebios/workshops/<uuid:workshop_pk>/validate/",
        views_ebios.WorkshopValidateView.as_view(),
        name="ebios-workshop-validate",
    ),
    path(
        "assessments/<uuid:assessment_pk>/ebios/workshops/<uuid:workshop_pk>/reject/",
        views_ebios.WorkshopRejectView.as_view(),
        name="ebios-workshop-reject",
    ),

    # EBIOS RM Workshop 0 (Study framework)
    path(
        "ebios/study-frameworks/<uuid:pk>/edit/",
        views_ebios.StudyFrameworkUpdateView.as_view(),
        name="ebios-study-framework-update",
    ),

    # EBIOS RM Workshop 1 (Security baseline + feared events + gaps)
    path(
        "ebios/baselines/<uuid:pk>/edit/",
        views_ebios.SecurityBaselineUpdateView.as_view(),
        name="ebios-baseline-update",
    ),
    path(
        "ebios/baselines/<uuid:baseline_pk>/feared-events/create/",
        views_ebios.FearedEventCreateView.as_view(),
        name="ebios-feared-event-create",
    ),
    path(
        "ebios/feared-events/<uuid:pk>/edit/",
        views_ebios.FearedEventUpdateView.as_view(),
        name="ebios-feared-event-update",
    ),
    path(
        "ebios/feared-events/<uuid:pk>/delete/",
        views_ebios.FearedEventDeleteView.as_view(),
        name="ebios-feared-event-delete",
    ),
    path(
        "ebios/baselines/<uuid:baseline_pk>/gaps/create/",
        views_ebios.BaselineGapCreateView.as_view(),
        name="ebios-baseline-gap-create",
    ),
    path(
        "ebios/gaps/<uuid:pk>/edit/",
        views_ebios.BaselineGapUpdateView.as_view(),
        name="ebios-baseline-gap-update",
    ),
    path(
        "ebios/gaps/<uuid:pk>/delete/",
        views_ebios.BaselineGapDeleteView.as_view(),
        name="ebios-baseline-gap-delete",
    ),

    # EBIOS RM Workshop 2 (risk sources, targeted objectives, SR/OV pairs)
    path(
        "assessments/<uuid:assessment_pk>/ebios/risk-sources/create/",
        views_ebios.RiskSourceCreateView.as_view(),
        name="ebios-risk-source-create",
    ),
    path(
        "ebios/risk-sources/<uuid:pk>/edit/",
        views_ebios.RiskSourceUpdateView.as_view(),
        name="ebios-risk-source-update",
    ),
    path(
        "ebios/risk-sources/<uuid:pk>/delete/",
        views_ebios.RiskSourceDeleteView.as_view(),
        name="ebios-risk-source-delete",
    ),
    path(
        "ebios/risk-sources/<uuid:risk_source_pk>/objectives/create/",
        views_ebios.TargetedObjectiveCreateView.as_view(),
        name="ebios-targeted-objective-create",
    ),
    path(
        "ebios/targeted-objectives/<uuid:pk>/edit/",
        views_ebios.TargetedObjectiveUpdateView.as_view(),
        name="ebios-targeted-objective-update",
    ),
    path(
        "ebios/targeted-objectives/<uuid:pk>/delete/",
        views_ebios.TargetedObjectiveDeleteView.as_view(),
        name="ebios-targeted-objective-delete",
    ),
    path(
        "assessments/<uuid:assessment_pk>/ebios/sr-ov-pairs/create/",
        views_ebios.SrOvPairCreateView.as_view(),
        name="ebios-sr-ov-pair-create",
    ),
    path(
        "ebios/sr-ov-pairs/<uuid:pk>/edit/",
        views_ebios.SrOvPairUpdateView.as_view(),
        name="ebios-sr-ov-pair-update",
    ),
    path(
        "ebios/sr-ov-pairs/<uuid:pk>/delete/",
        views_ebios.SrOvPairDeleteView.as_view(),
        name="ebios-sr-ov-pair-delete",
    ),

    # EBIOS RM Workshop 3 (ecosystem stakeholders, strategic scenarios, attack path steps)
    path(
        "assessments/<uuid:assessment_pk>/ebios/ecosystem/create/",
        views_ebios.EcosystemStakeholderCreateView.as_view(),
        name="ebios-ecosystem-create",
    ),
    path(
        "ebios/ecosystem/<uuid:pk>/edit/",
        views_ebios.EcosystemStakeholderUpdateView.as_view(),
        name="ebios-ecosystem-update",
    ),
    path(
        "ebios/ecosystem/<uuid:pk>/delete/",
        views_ebios.EcosystemStakeholderDeleteView.as_view(),
        name="ebios-ecosystem-delete",
    ),
    path(
        "assessments/<uuid:assessment_pk>/ebios/strategic-scenarios/create/",
        views_ebios.StrategicScenarioCreateView.as_view(),
        name="ebios-strategic-scenario-create",
    ),
    path(
        "ebios/strategic-scenarios/<uuid:pk>/edit/",
        views_ebios.StrategicScenarioUpdateView.as_view(),
        name="ebios-strategic-scenario-update",
    ),
    path(
        "ebios/strategic-scenarios/<uuid:pk>/delete/",
        views_ebios.StrategicScenarioDeleteView.as_view(),
        name="ebios-strategic-scenario-delete",
    ),
    path(
        "ebios/strategic-scenarios/<uuid:scenario_pk>/attack-steps/create/",
        views_ebios.AttackPathStepCreateView.as_view(),
        name="ebios-attack-path-step-create",
    ),
    path(
        "ebios/attack-steps/<uuid:pk>/edit/",
        views_ebios.AttackPathStepUpdateView.as_view(),
        name="ebios-attack-path-step-update",
    ),
    path(
        "ebios/attack-steps/<uuid:pk>/delete/",
        views_ebios.AttackPathStepDeleteView.as_view(),
        name="ebios-attack-path-step-delete",
    ),

    # EBIOS RM Workshop 4 (operational scenarios, attack techniques, consolidation)
    path(
        "assessments/<uuid:assessment_pk>/ebios/operational-scenarios/create/",
        views_ebios.OperationalScenarioCreateView.as_view(),
        name="ebios-operational-scenario-create",
    ),
    path(
        "ebios/operational-scenarios/<uuid:pk>/edit/",
        views_ebios.OperationalScenarioUpdateView.as_view(),
        name="ebios-operational-scenario-update",
    ),
    path(
        "ebios/operational-scenarios/<uuid:pk>/delete/",
        views_ebios.OperationalScenarioDeleteView.as_view(),
        name="ebios-operational-scenario-delete",
    ),
    path(
        "ebios/operational-scenarios/<uuid:pk>/consolidate/",
        views_ebios.OperationalScenarioConsolidateView.as_view(),
        name="ebios-operational-scenario-consolidate",
    ),
    path(
        "ebios/operational-scenarios/<uuid:scenario_pk>/techniques/create/",
        views_ebios.AttackTechniqueCreateView.as_view(),
        name="ebios-attack-technique-create",
    ),
    path(
        "ebios/attack-techniques/<uuid:pk>/edit/",
        views_ebios.AttackTechniqueUpdateView.as_view(),
        name="ebios-attack-technique-update",
    ),
    path(
        "ebios/attack-techniques/<uuid:pk>/delete/",
        views_ebios.AttackTechniqueDeleteView.as_view(),
        name="ebios-attack-technique-delete",
    ),

    # EBIOS RM Workshop 5 (summary edit, capture mappings, PACS measures)
    path(
        "ebios/summaries/<uuid:pk>/edit/",
        views_ebios.EbiosSummaryUpdateView.as_view(),
        name="ebios-summary-update",
    ),
    path(
        "ebios/summaries/<uuid:pk>/capture-mappings/",
        views_ebios.EbiosSummaryCaptureMappingsView.as_view(),
        name="ebios-summary-capture-mappings",
    ),
    path(
        "ebios/summaries/<uuid:summary_pk>/pacs-measures/create/",
        views_ebios.PACSMeasureCreateView.as_view(),
        name="ebios-pacs-measure-create",
    ),
    path(
        "ebios/pacs-measures/<uuid:pk>/edit/",
        views_ebios.PACSMeasureUpdateView.as_view(),
        name="ebios-pacs-measure-update",
    ),
    path(
        "ebios/pacs-measures/<uuid:pk>/delete/",
        views_ebios.PACSMeasureDeleteView.as_view(),
        name="ebios-pacs-measure-delete",
    ),
]
