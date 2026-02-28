from django.urls import path, reverse_lazy

from . import views
from .models import Activity, Issue, Objective, Role, Scope, Site, Stakeholder, SwotAnalysis

app_name = "context"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Scopes
    path("scopes/", views.ScopeListView.as_view(), name="scope-list"),
    path("scopes/create/", views.ScopeCreateView.as_view(), name="scope-create"),
    path("scopes/<uuid:pk>/", views.ScopeDetailView.as_view(), name="scope-detail"),
    path("scopes/<uuid:pk>/edit/", views.ScopeUpdateView.as_view(), name="scope-update"),
    path("scopes/<uuid:pk>/delete/", views.ScopeDeleteView.as_view(), name="scope-delete"),
    path("scopes/<uuid:pk>/approve/", views.ApproveView.as_view(model=Scope, success_url=reverse_lazy("context:scope-list")), name="scope-approve"),
    # Sites
    path("sites/", views.SiteListView.as_view(), name="site-list"),
    path("sites/create/", views.SiteCreateView.as_view(), name="site-create"),
    path("sites/<uuid:pk>/", views.SiteDetailView.as_view(), name="site-detail"),
    path("sites/<uuid:pk>/edit/", views.SiteUpdateView.as_view(), name="site-update"),
    path("sites/<uuid:pk>/delete/", views.SiteDeleteView.as_view(), name="site-delete"),
    path("sites/<uuid:pk>/approve/", views.ApproveView.as_view(model=Site, success_url=reverse_lazy("context:site-list")), name="site-approve"),
    # Issues
    path("issues/", views.IssueListView.as_view(), name="issue-list"),
    path("issues/create/", views.IssueCreateView.as_view(), name="issue-create"),
    path("issues/<uuid:pk>/", views.IssueDetailView.as_view(), name="issue-detail"),
    path("issues/<uuid:pk>/edit/", views.IssueUpdateView.as_view(), name="issue-update"),
    path("issues/<uuid:pk>/delete/", views.IssueDeleteView.as_view(), name="issue-delete"),
    path("issues/<uuid:pk>/approve/", views.ApproveView.as_view(model=Issue, success_url=reverse_lazy("context:issue-list")), name="issue-approve"),
    # Stakeholders
    path("stakeholders/", views.StakeholderListView.as_view(), name="stakeholder-list"),
    path("stakeholders/create/", views.StakeholderCreateView.as_view(), name="stakeholder-create"),
    path("stakeholders/<uuid:pk>/", views.StakeholderDetailView.as_view(), name="stakeholder-detail"),
    path("stakeholders/<uuid:pk>/edit/", views.StakeholderUpdateView.as_view(), name="stakeholder-update"),
    path("stakeholders/<uuid:pk>/delete/", views.StakeholderDeleteView.as_view(), name="stakeholder-delete"),
    path("stakeholders/<uuid:pk>/approve/", views.ApproveView.as_view(model=Stakeholder, success_url=reverse_lazy("context:stakeholder-list")), name="stakeholder-approve"),
    # Objectives
    path("objectives/", views.ObjectiveListView.as_view(), name="objective-list"),
    path("objectives/create/", views.ObjectiveCreateView.as_view(), name="objective-create"),
    path("objectives/<uuid:pk>/", views.ObjectiveDetailView.as_view(), name="objective-detail"),
    path("objectives/<uuid:pk>/edit/", views.ObjectiveUpdateView.as_view(), name="objective-update"),
    path("objectives/<uuid:pk>/delete/", views.ObjectiveDeleteView.as_view(), name="objective-delete"),
    path("objectives/<uuid:pk>/approve/", views.ApproveView.as_view(model=Objective, success_url=reverse_lazy("context:objective-list")), name="objective-approve"),
    # SWOT
    path("swot/", views.SwotListView.as_view(), name="swot-list"),
    path("swot/create/", views.SwotCreateView.as_view(), name="swot-create"),
    path("swot/<uuid:pk>/", views.SwotDetailView.as_view(), name="swot-detail"),
    path("swot/<uuid:pk>/edit/", views.SwotUpdateView.as_view(), name="swot-update"),
    path("swot/<uuid:pk>/delete/", views.SwotDeleteView.as_view(), name="swot-delete"),
    path("swot/<uuid:pk>/approve/", views.ApproveView.as_view(model=SwotAnalysis, permission_feature="swot", success_url=reverse_lazy("context:swot-list")), name="swot-approve"),
    # Roles
    path("roles/", views.RoleListView.as_view(), name="role-list"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role-create"),
    path("roles/<uuid:pk>/", views.RoleDetailView.as_view(), name="role-detail"),
    path("roles/<uuid:pk>/edit/", views.RoleUpdateView.as_view(), name="role-update"),
    path("roles/<uuid:pk>/delete/", views.RoleDeleteView.as_view(), name="role-delete"),
    path("roles/<uuid:pk>/approve/", views.ApproveView.as_view(model=Role, success_url=reverse_lazy("context:role-list")), name="role-approve"),
    # Activities
    path("activities/", views.ActivityListView.as_view(), name="activity-list"),
    path("activities/create/", views.ActivityCreateView.as_view(), name="activity-create"),
    path("activities/<uuid:pk>/", views.ActivityDetailView.as_view(), name="activity-detail"),
    path("activities/<uuid:pk>/edit/", views.ActivityUpdateView.as_view(), name="activity-update"),
    path("activities/<uuid:pk>/delete/", views.ActivityDeleteView.as_view(), name="activity-delete"),
    path("activities/<uuid:pk>/approve/", views.ApproveView.as_view(model=Activity, success_url=reverse_lazy("context:activity-list")), name="activity-approve"),
]
