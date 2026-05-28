from rest_framework import viewsets

from accounts.api.mixins import ApprovableAPIMixin, BatchCreateMixin, HistoryAPIMixin, ScopeFilterAPIMixin
from context.api.permissions import ContextPermission
from risks.models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskLevel,
    RiskTreatmentPlan,
    ScaleLevel,
    Threat,
    TreatmentAction,
    Vulnerability,
)
from .filters import (
    ISO27005RiskFilter,
    RiskAcceptanceFilter,
    RiskAssessmentFilter,
    RiskCriteriaFilter,
    RiskFilter,
    RiskLevelFilter,
    RiskTreatmentPlanFilter,
    ScaleLevelFilter,
    ThreatFilter,
    TreatmentActionFilter,
    VulnerabilityFilter,
)
from .serializers import (
    ISO27005RiskListSerializer,
    ISO27005RiskSerializer,
    RiskAcceptanceSerializer,
    RiskAssessmentListSerializer,
    RiskAssessmentSerializer,
    RiskCriteriaListSerializer,
    RiskCriteriaSerializer,
    RiskLevelSerializer,
    RiskListSerializer,
    RiskSerializer,
    RiskTreatmentPlanListSerializer,
    RiskTreatmentPlanSerializer,
    ScaleLevelSerializer,
    ThreatListSerializer,
    ThreatSerializer,
    TreatmentActionSerializer,
    VulnerabilityListSerializer,
    VulnerabilitySerializer,
)


class CreatedByMixin:
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class RiskCriteriaViewSet(ScopeFilterAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = RiskCriteria.objects.prefetch_related("scopes", "scale_levels", "risk_levels").all()
    filterset_class = RiskCriteriaFilter
    permission_classes = [ContextPermission]
    permission_feature = "criteria"
    search_fields = ["name", "description"]
    ordering_fields = ["name", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RiskCriteriaListSerializer
        return RiskCriteriaSerializer


class RiskAssessmentViewSet(ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = RiskAssessment.objects.select_related("assessor", "risk_criteria").prefetch_related("scopes").all()
    filterset_class = RiskAssessmentFilter
    permission_classes = [ContextPermission]
    permission_feature = "assessment"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "status", "assessment_date", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RiskAssessmentListSerializer
        return RiskAssessmentSerializer


class RiskViewSet(BatchCreateMixin, ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    scope_parent_lookup = "assessment__scopes"
    queryset = Risk.objects.select_related("assessment", "risk_owner").all()
    filterset_class = RiskFilter
    permission_classes = [ContextPermission]
    permission_feature = "risk"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "priority", "status", "current_risk_level", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RiskListSerializer
        return RiskSerializer


class RiskTreatmentPlanViewSet(BatchCreateMixin, ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    scope_parent_lookup = "risk__assessment__scopes"
    queryset = RiskTreatmentPlan.objects.select_related("risk", "owner").prefetch_related("actions").all()
    filterset_class = RiskTreatmentPlanFilter
    permission_classes = [ContextPermission]
    permission_feature = "treatment"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "status", "target_date", "progress_percentage", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RiskTreatmentPlanListSerializer
        return RiskTreatmentPlanSerializer


class RiskAcceptanceViewSet(BatchCreateMixin, ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    scope_parent_lookup = "risk__assessment__scopes"
    queryset = RiskAcceptance.objects.select_related("risk", "accepted_by").all()
    filterset_class = RiskAcceptanceFilter
    permission_classes = [ContextPermission]
    permission_feature = "acceptance"
    search_fields = ["justification", "conditions"]
    ordering_fields = ["status", "valid_until", "created_at"]

    def get_serializer_class(self):
        return RiskAcceptanceSerializer


class ThreatViewSet(BatchCreateMixin, ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Threat.objects.prefetch_related("scopes").all()
    filterset_class = ThreatFilter
    permission_classes = [ContextPermission]
    permission_feature = "threat"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "type", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ThreatListSerializer
        return ThreatSerializer


class VulnerabilityViewSet(BatchCreateMixin, ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Vulnerability.objects.prefetch_related("scopes").all()
    filterset_class = VulnerabilityFilter
    permission_classes = [ContextPermission]
    permission_feature = "vulnerability"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "category", "severity", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return VulnerabilityListSerializer
        return VulnerabilitySerializer


class ISO27005RiskViewSet(BatchCreateMixin, ScopeFilterAPIMixin, ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    scope_parent_lookup = "assessment__scopes"
    queryset = ISO27005Risk.objects.select_related("assessment", "threat", "vulnerability").all()
    filterset_class = ISO27005RiskFilter
    permission_classes = [ContextPermission]
    permission_feature = "iso27005"
    search_fields = ["threat__name", "vulnerability__name", "description"]
    ordering_fields = ["risk_level", "combined_likelihood", "max_impact", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ISO27005RiskListSerializer
        return ISO27005RiskSerializer


class TreatmentActionViewSet(viewsets.ModelViewSet):
    """CRUD for individual TreatmentAction rows under a RiskTreatmentPlan."""

    queryset = TreatmentAction.objects.select_related("treatment_plan", "owner").all()
    serializer_class = TreatmentActionSerializer
    filterset_class = TreatmentActionFilter
    permission_classes = [ContextPermission]
    permission_module = "risks"
    permission_feature = "treatment"
    search_fields = ["description"]
    ordering_fields = ["order", "status", "target_date", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated or user.is_superuser:
            return qs
        scope_ids = user.get_allowed_scope_ids()
        if scope_ids is None:
            return qs
        return qs.filter(
            treatment_plan__risk__assessment__scopes__id__in=scope_ids
        ).distinct()


class ScaleLevelViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to scale levels of a risk criteria."""

    queryset = ScaleLevel.objects.select_related("criteria").all()
    serializer_class = ScaleLevelSerializer
    filterset_class = ScaleLevelFilter
    permission_classes = [ContextPermission]
    permission_module = "risks"
    permission_feature = "criteria"
    ordering_fields = ["scale_type", "level"]


class RiskLevelViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to risk levels (outcomes) of a risk criteria."""

    queryset = RiskLevel.objects.select_related("criteria").all()
    serializer_class = RiskLevelSerializer
    filterset_class = RiskLevelFilter
    permission_classes = [ContextPermission]
    permission_module = "risks"
    permission_feature = "criteria"
    ordering_fields = ["level"]
