from django.urls import path, reverse_lazy

from . import views
from .models import AssetDependency, AssetGroup, EssentialAsset, Supplier, SupportAsset

app_name = "assets"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Essential Assets
    path("essential/", views.EssentialAssetListView.as_view(), name="essential-asset-list"),
    path("essential/create/", views.EssentialAssetCreateView.as_view(), name="essential-asset-create"),
    path("essential/<uuid:pk>/", views.EssentialAssetDetailView.as_view(), name="essential-asset-detail"),
    path("essential/<uuid:pk>/edit/", views.EssentialAssetUpdateView.as_view(), name="essential-asset-update"),
    path("essential/<uuid:pk>/delete/", views.EssentialAssetDeleteView.as_view(), name="essential-asset-delete"),
    path("essential/<uuid:pk>/approve/", views.ApproveView.as_view(model=EssentialAsset, permission_feature="essential_asset", success_url=reverse_lazy("assets:essential-asset-list")), name="essential-asset-approve"),
    # Support Assets
    path("support/", views.SupportAssetListView.as_view(), name="support-asset-list"),
    path("support/create/", views.SupportAssetCreateView.as_view(), name="support-asset-create"),
    path("support/<uuid:pk>/", views.SupportAssetDetailView.as_view(), name="support-asset-detail"),
    path("support/<uuid:pk>/edit/", views.SupportAssetUpdateView.as_view(), name="support-asset-update"),
    path("support/<uuid:pk>/delete/", views.SupportAssetDeleteView.as_view(), name="support-asset-delete"),
    path("support/<uuid:pk>/approve/", views.ApproveView.as_view(model=SupportAsset, permission_feature="support_asset", success_url=reverse_lazy("assets:support-asset-list")), name="support-asset-approve"),
    # Dependencies
    path("dependencies/", views.DependencyListView.as_view(), name="dependency-list"),
    path("dependencies/create/", views.DependencyCreateView.as_view(), name="dependency-create"),
    path("dependencies/<uuid:pk>/edit/", views.DependencyUpdateView.as_view(), name="dependency-update"),
    path("dependencies/<uuid:pk>/delete/", views.DependencyDeleteView.as_view(), name="dependency-delete"),
    path("dependencies/<uuid:pk>/approve/", views.ApproveView.as_view(model=AssetDependency, permission_feature="dependency", success_url=reverse_lazy("assets:dependency-list")), name="dependency-approve"),
    # Groups
    path("groups/", views.GroupListView.as_view(), name="group-list"),
    path("groups/create/", views.GroupCreateView.as_view(), name="group-create"),
    path("groups/<uuid:pk>/", views.GroupDetailView.as_view(), name="group-detail"),
    path("groups/<uuid:pk>/edit/", views.GroupUpdateView.as_view(), name="group-update"),
    path("groups/<uuid:pk>/delete/", views.GroupDeleteView.as_view(), name="group-delete"),
    path("groups/<uuid:pk>/approve/", views.ApproveView.as_view(model=AssetGroup, permission_feature="group", success_url=reverse_lazy("assets:group-list")), name="group-approve"),
    # Suppliers
    path("suppliers/", views.SupplierListView.as_view(), name="supplier-list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier-create"),
    path("suppliers/<uuid:pk>/", views.SupplierDetailView.as_view(), name="supplier-detail"),
    path("suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier-update"),
    path("suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier-delete"),
    path("suppliers/<uuid:pk>/archive/", views.SupplierArchiveView.as_view(), name="supplier-archive"),
    path("suppliers/<uuid:pk>/approve/", views.ApproveView.as_view(model=Supplier, permission_feature="supplier", success_url=reverse_lazy("assets:supplier-list")), name="supplier-approve"),
    # Supplier Requirements
    path("suppliers/<uuid:supplier_pk>/requirements/create/", views.SupplierRequirementCreateView.as_view(), name="supplier-requirement-create"),
    path("supplier-requirements/<int:pk>/edit/", views.SupplierRequirementUpdateView.as_view(), name="supplier-requirement-update"),
    path("supplier-requirements/<int:pk>/delete/", views.SupplierRequirementDeleteView.as_view(), name="supplier-requirement-delete"),
]
