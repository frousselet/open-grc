from django.urls import path, reverse_lazy

from . import views
from .constants import IndicatorType
from .models import Activity, Indicator, Issue, Objective, Role, Scope, Stakeholder, SwotAnalysis

app_name = "context"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/indicator-toggle/", views.dashboard_indicator_toggle, name="dashboard-indicator-toggle"),
    path("dashboard/indicator-chart-toggle/", views.dashboard_indicator_chart_toggle, name="dashboard-indicator-chart-toggle"),
    # Scopes
    path("scopes/", views.ScopeListView.as_view(), name="scope-list"),
    path("scopes/create/", views.ScopeCreateView.as_view(), name="scope-create"),
    path("scopes/<uuid:pk>/", views.ScopeDetailView.as_view(), name="scope-detail"),
    path("scopes/<uuid:pk>/edit/", views.ScopeUpdateView.as_view(), name="scope-update"),
    path("scopes/<uuid:pk>/delete/", views.ScopeDeleteView.as_view(), name="scope-delete"),
    path("scopes/<uuid:pk>/approve/", views.ApproveView.as_view(model=Scope, success_url=reverse_lazy("context:scope-list")), name="scope-approve"),
    path("scopes/table-body/", views.ScopeTableBodyView.as_view(), name="scope-table-body"),
    # Issues
    path("issues/", views.IssueListView.as_view(), name="issue-list"),
    path("issues/create/", views.IssueCreateView.as_view(), name="issue-create"),
    path("issues/<uuid:pk>/", views.IssueDetailView.as_view(), name="issue-detail"),
    path("issues/<uuid:pk>/edit/", views.IssueUpdateView.as_view(), name="issue-update"),
    path("issues/<uuid:pk>/delete/", views.IssueDeleteView.as_view(), name="issue-delete"),
    path("issues/<uuid:pk>/approve/", views.ApproveView.as_view(model=Issue, success_url=reverse_lazy("context:issue-list")), name="issue-approve"),
    path("issues/table-body/", views.IssueTableBodyView.as_view(), name="issue-table-body"),
    # Stakeholders
    path("stakeholders/", views.StakeholderListView.as_view(), name="stakeholder-list"),
    path("stakeholders/create/", views.StakeholderCreateView.as_view(), name="stakeholder-create"),
    path("stakeholders/<uuid:pk>/", views.StakeholderDetailView.as_view(), name="stakeholder-detail"),
    path("stakeholders/<uuid:pk>/edit/", views.StakeholderUpdateView.as_view(), name="stakeholder-update"),
    path("stakeholders/<uuid:pk>/delete/", views.StakeholderDeleteView.as_view(), name="stakeholder-delete"),
    path("stakeholders/<uuid:pk>/approve/", views.ApproveView.as_view(model=Stakeholder, success_url=reverse_lazy("context:stakeholder-list")), name="stakeholder-approve"),
    path("stakeholders/table-body/", views.StakeholderTableBodyView.as_view(), name="stakeholder-table-body"),
    # Objectives
    path("objectives/", views.ObjectiveListView.as_view(), name="objective-list"),
    path("objectives/create/", views.ObjectiveCreateView.as_view(), name="objective-create"),
    path("objectives/<uuid:pk>/", views.ObjectiveDetailView.as_view(), name="objective-detail"),
    path("objectives/<uuid:pk>/edit/", views.ObjectiveUpdateView.as_view(), name="objective-update"),
    path("objectives/<uuid:pk>/delete/", views.ObjectiveDeleteView.as_view(), name="objective-delete"),
    path("objectives/<uuid:pk>/approve/", views.ApproveView.as_view(model=Objective, success_url=reverse_lazy("context:objective-list")), name="objective-approve"),
    path("objectives/table-body/", views.ObjectiveTableBodyView.as_view(), name="objective-table-body"),
    # SWOT
    path("swot/", views.SwotListView.as_view(), name="swot-list"),
    path("swot/create/", views.SwotCreateView.as_view(), name="swot-create"),
    path("swot/<uuid:pk>/", views.SwotDetailView.as_view(), name="swot-detail"),
    path("swot/<uuid:pk>/edit/", views.SwotUpdateView.as_view(), name="swot-update"),
    path("swot/<uuid:pk>/delete/", views.SwotDeleteView.as_view(), name="swot-delete"),
    path("swot/<uuid:pk>/approve/", views.ApproveView.as_view(model=SwotAnalysis, permission_feature="swot", success_url=reverse_lazy("context:swot-list")), name="swot-approve"),
    path("swot/table-body/", views.SwotTableBodyView.as_view(), name="swot-table-body"),
    # Roles
    path("roles/", views.RoleListView.as_view(), name="role-list"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role-create"),
    path("roles/<uuid:pk>/", views.RoleDetailView.as_view(), name="role-detail"),
    path("roles/<uuid:pk>/edit/", views.RoleUpdateView.as_view(), name="role-update"),
    path("roles/<uuid:pk>/delete/", views.RoleDeleteView.as_view(), name="role-delete"),
    path("roles/<uuid:pk>/approve/", views.ApproveView.as_view(model=Role, success_url=reverse_lazy("context:role-list")), name="role-approve"),
    path("roles/table-body/", views.RoleTableBodyView.as_view(), name="role-table-body"),
    # Activities
    path("activities/", views.ActivityListView.as_view(), name="activity-list"),
    path("activities/create/", views.ActivityCreateView.as_view(), name="activity-create"),
    path("activities/<uuid:pk>/", views.ActivityDetailView.as_view(), name="activity-detail"),
    path("activities/<uuid:pk>/edit/", views.ActivityUpdateView.as_view(), name="activity-update"),
    path("activities/<uuid:pk>/delete/", views.ActivityDeleteView.as_view(), name="activity-delete"),
    path("activities/<uuid:pk>/approve/", views.ApproveView.as_view(model=Activity, success_url=reverse_lazy("context:activity-list")), name="activity-approve"),
    path("activities/table-body/", views.ActivityTableBodyView.as_view(), name="activity-table-body"),
    # Tags
    path("tags/", views.TagListView.as_view(), name="tag-list"),
    path("tags/<uuid:pk>/edit/", views.TagUpdateView.as_view(), name="tag-update"),
    path("tags/<uuid:pk>/delete/", views.TagDeleteView.as_view(), name="tag-delete"),
    # Inline tag creation (AJAX)
    path("tags/create-inline/", views.tag_create_inline, name="tag-create-inline"),
    # Indicators — Organizational
    path("indicators/organizational/", views.IndicatorListView.as_view(indicator_type=IndicatorType.ORGANIZATIONAL), name="indicator-organizational-list"),
    path("indicators/organizational/create/", views.IndicatorCreateView.as_view(indicator_type=IndicatorType.ORGANIZATIONAL), name="indicator-organizational-create"),
    # Indicators — Technical
    path("indicators/technical/", views.IndicatorListView.as_view(indicator_type=IndicatorType.TECHNICAL), name="indicator-technical-list"),
    path("indicators/technical/create/", views.IndicatorCreateView.as_view(indicator_type=IndicatorType.TECHNICAL), name="indicator-technical-create"),
    # Indicators — Predefined
    path("indicators/predefined/create/", views.PredefinedIndicatorCreateView.as_view(), name="indicator-predefined-create"),
    # Indicators — shared CRUD
    path("indicators/<uuid:pk>/", views.IndicatorDetailView.as_view(), name="indicator-detail"),
    path("indicators/<uuid:pk>/edit/", views.IndicatorUpdateView.as_view(), name="indicator-update"),
    path("indicators/<uuid:pk>/delete/", views.IndicatorDeleteView.as_view(), name="indicator-delete"),
    path("indicators/<uuid:pk>/approve/", views.ApproveView.as_view(model=Indicator, success_url=reverse_lazy("context:indicator-organizational-list")), name="indicator-approve"),
    path("indicators/<uuid:pk>/record/", views.IndicatorRecordMeasurementView.as_view(), name="indicator-record"),
    path("indicators/<uuid:pk>/refresh/", views.IndicatorRefreshView.as_view(), name="indicator-refresh"),
]
