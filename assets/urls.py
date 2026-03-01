from django.urls import path, reverse_lazy

from context.models import Site
from . import views
from .models import AssetDependency, AssetGroup, EssentialAsset, SiteAssetDependency, SiteSupplierDependency, Supplier, SupplierDependency, SupportAsset

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
    # Supplier Types
    path("supplier-types/", views.SupplierTypeListView.as_view(), name="supplier-type-list"),
    path("supplier-types/create/", views.SupplierTypeCreateView.as_view(), name="supplier-type-create"),
    path("supplier-types/<int:pk>/", views.SupplierTypeDetailView.as_view(), name="supplier-type-detail"),
    path("supplier-types/<int:pk>/edit/", views.SupplierTypeUpdateView.as_view(), name="supplier-type-update"),
    path("supplier-types/<int:pk>/delete/", views.SupplierTypeDeleteView.as_view(), name="supplier-type-delete"),
    # Supplier Type Requirements
    path("supplier-types/<int:type_pk>/requirements/create/", views.SupplierTypeRequirementCreateView.as_view(), name="supplier-type-requirement-create"),
    path("supplier-type-requirements/<int:pk>/edit/", views.SupplierTypeRequirementUpdateView.as_view(), name="supplier-type-requirement-update"),
    path("supplier-type-requirements/<int:pk>/delete/", views.SupplierTypeRequirementDeleteView.as_view(), name="supplier-type-requirement-delete"),
    # Suppliers
    path("suppliers/", views.SupplierListView.as_view(), name="supplier-list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier-create"),
    path("suppliers/<uuid:pk>/", views.SupplierDetailView.as_view(), name="supplier-detail"),
    path("suppliers/<uuid:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier-update"),
    path("suppliers/<uuid:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier-delete"),
    path("suppliers/<uuid:pk>/archive/", views.SupplierArchiveView.as_view(), name="supplier-archive"),
    path("suppliers/<uuid:pk>/approve/", views.ApproveView.as_view(model=Supplier, permission_feature="supplier", success_url=reverse_lazy("assets:supplier-list")), name="supplier-approve"),
    # Supplier Requirements
    path("suppliers/<uuid:supplier_pk>/type-requirements/<int:type_req_pk>/review/", views.InstantiateTypeRequirementReviewView.as_view(), name="instantiate-type-requirement-review"),
    path("suppliers/<uuid:supplier_pk>/requirements/create/", views.SupplierRequirementCreateView.as_view(), name="supplier-requirement-create"),
    path("supplier-requirements/<int:pk>/", views.SupplierRequirementDetailView.as_view(), name="supplier-requirement-detail"),
    path("supplier-requirements/<int:pk>/edit/", views.SupplierRequirementUpdateView.as_view(), name="supplier-requirement-update"),
    path("supplier-requirements/<int:pk>/delete/", views.SupplierRequirementDeleteView.as_view(), name="supplier-requirement-delete"),
    # Supplier Requirement Reviews
    path("supplier-requirements/<int:requirement_pk>/reviews/create/", views.SupplierRequirementReviewCreateView.as_view(), name="supplier-requirement-review-create"),
    path("supplier-requirement-reviews/<int:pk>/delete/", views.SupplierRequirementReviewDeleteView.as_view(), name="supplier-requirement-review-delete"),
    # Supplier Dependencies
    path("supplier-dependencies/", views.SupplierDependencyListView.as_view(), name="supplier-dependency-list"),
    path("supplier-dependencies/create/", views.SupplierDependencyCreateView.as_view(), name="supplier-dependency-create"),
    path("supplier-dependencies/<uuid:pk>/edit/", views.SupplierDependencyUpdateView.as_view(), name="supplier-dependency-update"),
    path("supplier-dependencies/<uuid:pk>/delete/", views.SupplierDependencyDeleteView.as_view(), name="supplier-dependency-delete"),
    path("supplier-dependencies/<uuid:pk>/approve/", views.ApproveView.as_view(model=SupplierDependency, permission_feature="supplier_dependency", success_url=reverse_lazy("assets:supplier-dependency-list")), name="supplier-dependency-approve"),
    # Sites
    path("sites/", views.SiteListView.as_view(), name="site-list"),
    path("sites/create/", views.SiteCreateView.as_view(), name="site-create"),
    path("sites/<uuid:pk>/", views.SiteDetailView.as_view(), name="site-detail"),
    path("sites/<uuid:pk>/edit/", views.SiteUpdateView.as_view(), name="site-update"),
    path("sites/<uuid:pk>/delete/", views.SiteDeleteView.as_view(), name="site-delete"),
    path("sites/<uuid:pk>/approve/", views.ApproveView.as_view(model=Site, permission_feature="site", success_url=reverse_lazy("assets:site-list")), name="site-approve"),
    # Site–Asset Dependencies
    path("site-asset-dependencies/", views.SiteAssetDependencyListView.as_view(), name="site-asset-dependency-list"),
    path("site-asset-dependencies/create/", views.SiteAssetDependencyCreateView.as_view(), name="site-asset-dependency-create"),
    path("site-asset-dependencies/<uuid:pk>/edit/", views.SiteAssetDependencyUpdateView.as_view(), name="site-asset-dependency-update"),
    path("site-asset-dependencies/<uuid:pk>/delete/", views.SiteAssetDependencyDeleteView.as_view(), name="site-asset-dependency-delete"),
    path("site-asset-dependencies/<uuid:pk>/approve/", views.ApproveView.as_view(model=SiteAssetDependency, permission_feature="site_asset_dependency", success_url=reverse_lazy("assets:site-asset-dependency-list")), name="site-asset-dependency-approve"),
    # Site–Supplier Dependencies
    path("site-supplier-dependencies/", views.SiteSupplierDependencyListView.as_view(), name="site-supplier-dependency-list"),
    path("site-supplier-dependencies/create/", views.SiteSupplierDependencyCreateView.as_view(), name="site-supplier-dependency-create"),
    path("site-supplier-dependencies/<uuid:pk>/edit/", views.SiteSupplierDependencyUpdateView.as_view(), name="site-supplier-dependency-update"),
    path("site-supplier-dependencies/<uuid:pk>/delete/", views.SiteSupplierDependencyDeleteView.as_view(), name="site-supplier-dependency-delete"),
    path("site-supplier-dependencies/<uuid:pk>/approve/", views.ApproveView.as_view(model=SiteSupplierDependency, permission_feature="site_supplier_dependency", success_url=reverse_lazy("assets:site-supplier-dependency-list")), name="site-supplier-dependency-approve"),
    # Dependency Graph
    path("dependency-graph/", views.DependencyGraphView.as_view(), name="dependency-graph"),
]
