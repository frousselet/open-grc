from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.mixins import ApprovableAPIMixin, HistoryAPIMixin, ScopeFilterAPIMixin
from context.api.permissions import ContextPermission
from assets.models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    EssentialAsset,
    Supplier,
    SupplierDependency,
    SupplierRequirement,
    SupportAsset,
)
from .filters import (
    AssetDependencyFilter,
    AssetGroupFilter,
    EssentialAssetFilter,
    SupplierDependencyFilter,
    SupplierFilter,
    SupportAssetFilter,
)
from .serializers import (
    AssetDependencySerializer,
    AssetGroupListSerializer,
    AssetGroupSerializer,
    AssetValuationSerializer,
    EssentialAssetListSerializer,
    EssentialAssetSerializer,
    SupplierDependencySerializer,
    SupplierListSerializer,
    SupplierRequirementSerializer,
    SupplierSerializer,
    SupportAssetListSerializer,
    SupportAssetSerializer,
)


class CreatedByMixin:
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EssentialAssetViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = EssentialAsset.objects.select_related("scope", "owner", "custodian").all()
    filterset_class = EssentialAssetFilter
    permission_classes = [ContextPermission]
    permission_feature = "essential_asset"
    search_fields = ["reference", "name", "description"]
    ordering_fields = [
        "reference", "name", "type", "category", "status",
        "confidentiality_level", "integrity_level", "availability_level",
        "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return EssentialAssetListSerializer
        return EssentialAssetSerializer

    @action(detail=True, methods=["get"], url_path="supporting-assets")
    def supporting_assets(self, request, pk=None):
        asset = self.get_object()
        deps = asset.dependencies_as_essential.select_related("support_asset")
        data = AssetDependencySerializer(deps, many=True).data
        return Response(data)

    @action(detail=True, methods=["get"])
    def dependencies(self, request, pk=None):
        asset = self.get_object()
        deps = asset.dependencies_as_essential.all()
        return Response(AssetDependencySerializer(deps, many=True).data)

    @action(detail=True, methods=["get", "post"])
    def valuations(self, request, pk=None):
        asset = self.get_object()
        if request.method == "GET":
            vals = asset.valuations.all()
            return Response(AssetValuationSerializer(vals, many=True).data)
        # POST — create valuation + update asset DIC (RV-06)
        serializer = AssetValuationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valuation = serializer.save(
            essential_asset=asset,
            evaluated_by=request.user,
        )
        # Update asset DIC levels from valuation
        asset.confidentiality_level = valuation.confidentiality_level
        asset.integrity_level = valuation.integrity_level
        asset.availability_level = valuation.availability_level
        asset.save()
        return Response(
            AssetValuationSerializer(valuation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total = qs.count()
        by_type = dict(qs.values_list("type").annotate(c=Count("id")).values_list("type", "c"))
        by_status = dict(qs.values_list("status").annotate(c=Count("id")).values_list("status", "c"))
        unsupported = qs.filter(dependencies_as_essential__isnull=True).count()
        personal_data_count = qs.filter(personal_data=True).count()
        return Response({
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
            "unsupported_count": unsupported,
            "personal_data_count": personal_data_count,
        })


class SupportAssetViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = SupportAsset.objects.select_related("scope", "owner", "custodian", "parent_asset").all()
    filterset_class = SupportAssetFilter
    permission_classes = [ContextPermission]
    permission_feature = "support_asset"
    search_fields = ["reference", "name", "description", "hostname", "ip_address"]
    ordering_fields = [
        "reference", "name", "type", "category", "status",
        "inherited_confidentiality", "inherited_integrity",
        "inherited_availability", "end_of_life_date", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return SupportAssetListSerializer
        return SupportAssetSerializer

    @action(detail=True, methods=["get"], url_path="essential-assets")
    def essential_assets(self, request, pk=None):
        asset = self.get_object()
        deps = asset.dependencies_as_support.select_related("essential_asset")
        return Response(AssetDependencySerializer(deps, many=True).data)

    @action(detail=True, methods=["get"])
    def dependencies(self, request, pk=None):
        asset = self.get_object()
        deps = asset.dependencies_as_support.all()
        return Response(AssetDependencySerializer(deps, many=True).data)

    @action(detail=True, methods=["get"], url_path="inherited-dic")
    def inherited_dic(self, request, pk=None):
        """RV-05: DIC inheritance detail."""
        asset = self.get_object()
        deps = asset.dependencies_as_support.select_related("essential_asset")
        detail = []
        for dep in deps:
            ea = dep.essential_asset
            detail.append({
                "essential_asset_id": str(ea.id),
                "essential_asset_reference": ea.reference,
                "essential_asset_name": ea.name,
                "confidentiality_level": ea.confidentiality_level,
                "integrity_level": ea.integrity_level,
                "availability_level": ea.availability_level,
            })
        return Response({
            "inherited_confidentiality": asset.inherited_confidentiality,
            "inherited_integrity": asset.inherited_integrity,
            "inherited_availability": asset.inherited_availability,
            "sources": detail,
        })

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        asset = self.get_object()
        children = asset.children.all()
        return Response(SupportAssetListSerializer(children, many=True).data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        roots = self.filter_queryset(self.get_queryset()).filter(parent_asset__isnull=True)
        return Response(SupportAssetListSerializer(roots, many=True).data)

    @action(detail=False, methods=["get"], url_path="end-of-life")
    def end_of_life(self, request):
        today = timezone.now().date()
        qs = self.filter_queryset(self.get_queryset()).filter(
            end_of_life_date__isnull=False,
            status__in=["in_stock", "deployed", "active", "under_maintenance"],
        ).order_by("end_of_life_date")
        return Response(SupportAssetListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        qs = self.filter_queryset(self.get_queryset())
        today = timezone.now().date()
        total = qs.count()
        by_type = dict(qs.values_list("type").annotate(c=Count("id")).values_list("type", "c"))
        by_status = dict(qs.values_list("status").annotate(c=Count("id")).values_list("status", "c"))
        orphans = qs.filter(dependencies_as_support__isnull=True).count()
        eol_count = qs.filter(
            end_of_life_date__lte=today,
            status="active",
        ).count()
        return Response({
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
            "orphan_count": orphans,
            "end_of_life_count": eol_count,
        })


class AssetDependencyViewSet(ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = AssetDependency.objects.select_related(
        "essential_asset", "support_asset"
    ).all()
    serializer_class = AssetDependencySerializer
    filterset_class = AssetDependencyFilter
    permission_classes = [ContextPermission]
    permission_feature = "dependency"
    search_fields = [
        "essential_asset__reference", "essential_asset__name",
        "support_asset__reference", "support_asset__name",
    ]
    ordering_fields = ["dependency_type", "criticality", "created_at"]

    @action(detail=False, methods=["get"])
    def spof(self, request):
        """RS-07: list SPOF with no redundancy."""
        qs = self.filter_queryset(self.get_queryset()).filter(
            is_single_point_of_failure=True,
        )
        return Response(AssetDependencySerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def graph(self, request):
        """Dependency graph data for visualization."""
        deps = self.filter_queryset(self.get_queryset()).select_related(
            "essential_asset", "support_asset"
        )
        nodes = {}
        edges = []
        for dep in deps:
            ea = dep.essential_asset
            sa = dep.support_asset
            ea_id = str(ea.id)
            sa_id = str(sa.id)
            if ea_id not in nodes:
                nodes[ea_id] = {
                    "id": ea_id,
                    "label": f"{ea.reference} - {ea.name}",
                    "type": "essential_asset",
                    "subtype": ea.type,
                    "dic": {
                        "c": ea.confidentiality_level,
                        "i": ea.integrity_level,
                        "d": ea.availability_level,
                    },
                }
            if sa_id not in nodes:
                nodes[sa_id] = {
                    "id": sa_id,
                    "label": f"{sa.reference} - {sa.name}",
                    "type": "support_asset",
                    "subtype": sa.type,
                    "inherited_dic": {
                        "c": sa.inherited_confidentiality,
                        "i": sa.inherited_integrity,
                        "d": sa.inherited_availability,
                    },
                }
            edges.append({
                "id": str(dep.id),
                "source": ea_id,
                "target": sa_id,
                "dependency_type": dep.dependency_type,
                "criticality": dep.criticality,
                "is_spof": dep.is_single_point_of_failure,
            })
        return Response({
            "nodes": list(nodes.values()),
            "edges": edges,
        })


class AssetGroupViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = AssetGroup.objects.select_related("scope", "owner").prefetch_related("members").all()
    filterset_class = AssetGroupFilter
    permission_classes = [ContextPermission]
    permission_feature = "group"
    search_fields = ["name", "description"]
    ordering_fields = ["name", "type", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return AssetGroupListSerializer
        return AssetGroupSerializer

    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):
        group = self.get_object()
        if request.method == "GET":
            members = group.members.all()
            return Response(SupportAssetListSerializer(members, many=True).data)
        # POST — add members
        asset_ids = request.data.get("asset_ids", [])
        group.members.add(*asset_ids)
        return Response({"status": "success"})

    @action(
        detail=True,
        methods=["delete"],
        url_path="members/(?P<asset_id>[^/.]+)",
    )
    def remove_member(self, request, pk=None, asset_id=None):
        group = self.get_object()
        group.members.remove(asset_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SupplierViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.select_related("scope", "owner").all()
    filterset_class = SupplierFilter
    permission_classes = [ContextPermission]
    permission_feature = "supplier"
    search_fields = ["reference", "name", "description", "contact_name", "contact_email"]
    ordering_fields = [
        "reference", "name", "type", "criticality", "status",
        "contract_end_date", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return SupplierListSerializer
        return SupplierSerializer

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        supplier = self.get_object()
        supplier.status = "archived"
        supplier.save(update_fields=["status"])
        return Response(SupplierSerializer(supplier).data)

    @action(detail=True, methods=["get", "post"])
    def requirements(self, request, pk=None):
        supplier = self.get_object()
        if request.method == "GET":
            reqs = supplier.requirements.select_related("requirement", "verified_by")
            return Response(SupplierRequirementSerializer(reqs, many=True).data)
        serializer = SupplierRequirementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(supplier=supplier)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total = qs.count()
        by_type = dict(qs.values_list("type").annotate(c=Count("id")).values_list("type", "c"))
        by_status = dict(qs.values_list("status").annotate(c=Count("id")).values_list("status", "c"))
        by_criticality = dict(qs.values_list("criticality").annotate(c=Count("id")).values_list("criticality", "c"))
        return Response({
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
            "by_criticality": by_criticality,
        })


class SupplierDependencyViewSet(ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = SupplierDependency.objects.select_related(
        "support_asset", "supplier"
    ).all()
    serializer_class = SupplierDependencySerializer
    filterset_class = SupplierDependencyFilter
    permission_classes = [ContextPermission]
    permission_feature = "supplier_dependency"
    search_fields = [
        "support_asset__reference", "support_asset__name",
        "supplier__reference", "supplier__name",
    ]
    ordering_fields = ["dependency_type", "criticality", "created_at"]
