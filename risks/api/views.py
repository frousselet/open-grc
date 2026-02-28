from rest_framework import viewsets

from accounts.api.mixins import ApprovableAPIMixin, HistoryAPIMixin, ScopeFilterAPIMixin
from context.api.permissions import ContextPermission
from risks.models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskTreatmentPlan,
    Threat,
    Vulnerability,
)
from .filters import (
    ISO27005RiskFilter,
    RiskAcceptanceFilter,
    RiskAssessmentFilter,
    RiskCriteriaFilter,
    RiskFilter,
    RiskTreatmentPlanFilter,
    ThreatFilter,
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
    RiskListSerializer,
    RiskSerializer,
    RiskTreatmentPlanListSerializer,
    RiskTreatmentPlanSerializer,
    ThreatListSerializer,
    ThreatSerializer,
    VulnerabilityListSerializer,
    VulnerabilitySerializer,
)


class CreatedByMixin:
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class RiskCriteriaViewSet(ScopeFilterAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = RiskCriteria.objects.select_related("scope").prefetch_related("scale_levels", "risk_levels").all()
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
    queryset = RiskAssessment.objects.select_related("scope", "assessor", "risk_criteria").all()
    filterset_class = RiskAssessmentFilter
    permission_classes = [ContextPermission]
    permission_feature = "assessment"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "status", "assessment_date", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return RiskAssessmentListSerializer
        return RiskAssessmentSerializer


class RiskViewSet(ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
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


class RiskTreatmentPlanViewSet(ApprovableAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
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


class RiskAcceptanceViewSet(HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = RiskAcceptance.objects.select_related("risk", "accepted_by").all()
    filterset_class = RiskAcceptanceFilter
    permission_classes = [ContextPermission]
    permission_feature = "acceptance"
    search_fields = ["justification", "conditions"]
    ordering_fields = ["status", "valid_until", "created_at"]

    def get_serializer_class(self):
        return RiskAcceptanceSerializer


class ThreatViewSet(ScopeFilterAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Threat.objects.select_related("scope").all()
    filterset_class = ThreatFilter
    permission_classes = [ContextPermission]
    permission_feature = "threat"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "type", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ThreatListSerializer
        return ThreatSerializer


class VulnerabilityViewSet(ScopeFilterAPIMixin, HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
    queryset = Vulnerability.objects.select_related("scope").all()
    filterset_class = VulnerabilityFilter
    permission_classes = [ContextPermission]
    permission_feature = "vulnerability"
    search_fields = ["reference", "name", "description"]
    ordering_fields = ["reference", "name", "category", "severity", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return VulnerabilityListSerializer
        return VulnerabilitySerializer


class ISO27005RiskViewSet(HistoryAPIMixin, CreatedByMixin, viewsets.ModelViewSet):
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
