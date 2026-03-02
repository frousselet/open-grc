from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.mixins import ApprovableAPIMixin, HistoryAPIMixin, ScopeFilterAPIMixin
from context.models import (
    Activity,
    Issue,
    Objective,
    Responsibility,
    Role,
    Scope,
    Site,
    Stakeholder,
    StakeholderExpectation,
    SwotAnalysis,
    SwotItem,
    Tag,
)
from .filters import (
    ActivityFilter,
    IssueFilter,
    ObjectiveFilter,
    RoleFilter,
    ScopeFilter,
    SiteFilter,
    StakeholderFilter,
    SwotAnalysisFilter,
)
from .permissions import ContextPermission
from .serializers import (
    ActivitySerializer,
    IssueSerializer,
    ObjectiveSerializer,
    ResponsibilitySerializer,
    RoleListSerializer,
    RoleSerializer,
    ScopeSerializer,
    SiteSerializer,
    StakeholderExpectationSerializer,
    StakeholderListSerializer,
    StakeholderSerializer,
    SwotAnalysisListSerializer,
    SwotAnalysisSerializer,
    SwotItemSerializer,
    TagSerializer,
)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [ContextPermission]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class CreatedByMixin:
    """Automatically set created_by on creation."""

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ScopeViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Scope.objects.select_related("parent_scope").all()
    serializer_class = ScopeSerializer
    filterset_class = ScopeFilter
    permission_classes = [ContextPermission]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "version", "status", "created_at", "effective_date"]

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        scope = self.get_object()
        scope.status = "archived"
        scope.save()
        return Response(ScopeSerializer(scope).data)


class SiteViewSet(ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Site.objects.select_related("parent_site").all()
    serializer_class = SiteSerializer
    filterset_class = SiteFilter
    permission_classes = [ContextPermission]
    search_fields = ["name", "description", "address"]
    ordering_fields = ["name", "type", "status", "created_at"]


class IssueViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Issue.objects.prefetch_related("scopes").all()
    serializer_class = IssueSerializer
    filterset_class = IssueFilter
    permission_classes = [ContextPermission]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "type", "impact_level", "status", "created_at"]


class StakeholderViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Stakeholder.objects.prefetch_related("scopes", "expectations").all()
    filterset_class = StakeholderFilter
    permission_classes = [ContextPermission]
    search_fields = ["name", "description", "contact_name"]
    ordering_fields = ["name", "type", "influence_level", "interest_level", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return StakeholderListSerializer
        return StakeholderSerializer

    @action(detail=False, methods=["get"])
    def matrix(self, request):
        """Matrice influence/intérêt."""
        qs = self.filter_queryset(self.get_queryset())
        data = qs.values("id", "name", "influence_level", "interest_level")
        return Response(list(data))


class StakeholderExpectationViewSet(CreatedByMixin, viewsets.ModelViewSet):
    serializer_class = StakeholderExpectationSerializer
    permission_classes = [ContextPermission]

    def get_queryset(self):
        return StakeholderExpectation.objects.filter(
            stakeholder_id=self.kwargs["stakeholder_pk"]
        )

    def perform_create(self, serializer):
        serializer.save(stakeholder_id=self.kwargs["stakeholder_pk"])


class ObjectiveViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Objective.objects.select_related("owner", "parent_objective").prefetch_related("scopes").all()
    serializer_class = ObjectiveSerializer
    filterset_class = ObjectiveFilter
    permission_classes = [ContextPermission]
    search_fields = ["reference", "name", "description"]
    ordering_fields = [
        "reference", "name", "category", "status", "progress_percentage",
        "target_date", "created_at",
    ]

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        obj = self.get_object()
        children = obj.children.all()
        serializer = ObjectiveSerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Arborescence complète (racines uniquement)."""
        roots = self.filter_queryset(self.get_queryset()).filter(parent_objective__isnull=True)
        serializer = ObjectiveSerializer(roots, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total = qs.count()
        by_status = {}
        for obj in qs.values("status").order_by("status"):
            by_status[obj["status"]] = by_status.get(obj["status"], 0) + 1
        avg_progress = qs.exclude(progress_percentage__isnull=True).values_list(
            "progress_percentage", flat=True
        )
        avg = sum(avg_progress) / len(avg_progress) if avg_progress else 0
        return Response({
            "total": total,
            "by_status": by_status,
            "average_progress": round(avg, 1),
        })


class SwotAnalysisViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = SwotAnalysis.objects.select_related("validated_by").prefetch_related("scopes", "items").all()
    filterset_class = SwotAnalysisFilter
    permission_classes = [ContextPermission]
    permission_feature = "swot"
    search_fields = ["name", "description"]
    ordering_fields = ["name", "analysis_date", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return SwotAnalysisListSerializer
        return SwotAnalysisSerializer

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        analysis = self.get_object()
        analysis.validated_by = request.user
        analysis.validated_at = timezone.now()
        analysis.status = "validated"
        analysis.save()
        return Response(SwotAnalysisSerializer(analysis).data)


class SwotItemViewSet(viewsets.ModelViewSet):
    serializer_class = SwotItemSerializer
    permission_classes = [ContextPermission]

    def get_queryset(self):
        return SwotItem.objects.filter(
            swot_analysis_id=self.kwargs["analysis_pk"]
        )

    def perform_create(self, serializer):
        serializer.save(swot_analysis_id=self.kwargs["analysis_pk"])

    @action(detail=False, methods=["patch"])
    def reorder(self, request, analysis_pk=None):
        """Réordonner les éléments: body = {"items": [{"id": "...", "order": 1}, ...]}"""
        items_data = request.data.get("items", [])
        for item_data in items_data:
            SwotItem.objects.filter(
                id=item_data["id"], swot_analysis_id=analysis_pk
            ).update(order=item_data["order"])
        return Response({"status": "success"})


class RoleViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related(
        "scopes", "assigned_users", "responsibilities"
    ).all()
    filterset_class = RoleFilter
    permission_classes = [ContextPermission]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "type", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RoleListSerializer
        return RoleSerializer

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        role = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"detail": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role.assigned_users.add(user_id)
        return Response(RoleSerializer(role).data)

    @action(detail=True, methods=["delete"], url_path="assign/(?P<user_id>[^/.]+)")
    def unassign(self, request, pk=None, user_id=None):
        role = self.get_object()
        role.assigned_users.remove(user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="compliance-check")
    def compliance_check(self, request):
        """RS-06: rôles obligatoires non pourvus."""
        qs = self.filter_queryset(self.get_queryset()).filter(is_mandatory=True)
        alerts = []
        for role in qs:
            if not role.assigned_users.exists():
                alerts.append({
                    "role_id": str(role.id),
                    "role_name": role.name,
                    "alert": "Rôle obligatoire sans utilisateur affecté",
                })
        return Response(alerts)


class ResponsibilityViewSet(viewsets.ModelViewSet):
    serializer_class = ResponsibilitySerializer
    permission_classes = [ContextPermission]

    def get_queryset(self):
        return Responsibility.objects.filter(role_id=self.kwargs["role_pk"])

    def perform_create(self, serializer):
        serializer.save(role_id=self.kwargs["role_pk"])


class ActivityViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Activity.objects.select_related("owner", "parent_activity").prefetch_related("scopes").all()
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter
    permission_classes = [ContextPermission]
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "type", "criticality", "status", "created_at"]

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        activity = self.get_object()
        children = activity.children.all()
        serializer = ActivitySerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        roots = self.filter_queryset(self.get_queryset()).filter(parent_activity__isnull=True)
        serializer = ActivitySerializer(roots, many=True)
        return Response(serializer.data)
