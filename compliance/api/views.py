from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.mixins import ApprovableAPIMixin, HistoryAPIMixin, ScopeFilterAPIMixin
from compliance.constants import ActionPlanStatus
from compliance.models import (
    ActionPlanComment,
    ComplianceActionPlan,
    ComplianceAssessment,
    AssessmentResult,
    Finding,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)
from .filters import (
    ComplianceActionPlanFilter,
    ComplianceAssessmentFilter,
    FrameworkFilter,
    RequirementFilter,
    RequirementMappingFilter,
    SectionFilter,
)
from .permissions import CompliancePermission
from .serializers import (
    ActionPlanCommentCreateSerializer,
    ActionPlanCommentSerializer,
    ActionPlanTransitionHistorySerializer,
    ActionPlanTransitionSerializer,
    AssessmentResultSerializer,
    ComplianceActionPlanListSerializer,
    ComplianceActionPlanSerializer,
    ComplianceAssessmentListSerializer,
    ComplianceAssessmentSerializer,
    FindingListSerializer,
    FindingSerializer,
    FrameworkListSerializer,
    FrameworkSerializer,
    RequirementListSerializer,
    RequirementMappingSerializer,
    RequirementSerializer,
    SectionSerializer,
)


class CreatedByMixin:
    """Automatically set created_by on creation."""

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FrameworkViewSet(
    ScopeFilterAPIMixin,
    ApprovableAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    viewsets.ModelViewSet,
):
    queryset = Framework.objects.prefetch_related("scopes").select_related("owner").all()
    filterset_class = FrameworkFilter
    permission_classes = [CompliancePermission]
    search_fields = ["reference", "name", "short_name", "description"]
    ordering_fields = [
        "reference", "name", "type", "category", "compliance_level",
        "status", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return FrameworkListSerializer
        return FrameworkSerializer

    @action(detail=True, methods=["get"])
    def compliance_summary(self, request, pk=None):
        """Compliance summary by section and status."""
        framework = self.get_object()
        sections = framework.sections.filter(parent_section__isnull=True)
        section_data = []
        for s in sections:
            section_data.append({
                "id": str(s.id),
                "reference": s.reference,
                "name": s.name,
                "compliance_level": float(s.compliance_level),
            })
        reqs = framework.requirements.filter(is_applicable=True)
        by_status = {}
        for req in reqs.values("compliance_status"):
            st = req["compliance_status"]
            by_status[st] = by_status.get(st, 0) + 1
        return Response({
            "compliance_level": float(framework.compliance_level),
            "sections": section_data,
            "by_status": by_status,
            "total_requirements": reqs.count(),
        })


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.select_related("framework", "parent_section").all()
    serializer_class = SectionSerializer
    filterset_class = SectionFilter
    permission_classes = [CompliancePermission]
    permission_feature = "section"
    search_fields = ["reference", "name"]
    ordering_fields = ["reference", "order", "name"]

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        section = self.get_object()
        children = section.children.all()
        serializer = SectionSerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Full section tree for a framework."""
        framework_id = request.query_params.get("framework_id")
        if not framework_id:
            return Response(
                {"detail": "framework_id query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        roots = Section.objects.filter(
            framework_id=framework_id, parent_section__isnull=True
        ).order_by("order")
        serializer = SectionSerializer(roots, many=True)
        return Response(serializer.data)


class RequirementViewSet(
    ApprovableAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    viewsets.ModelViewSet,
):
    queryset = Requirement.objects.select_related(
        "framework", "section", "owner"
    ).all()
    filterset_class = RequirementFilter
    permission_classes = [CompliancePermission]
    search_fields = ["reference", "name", "description"]
    ordering_fields = [
        "reference", "name", "type", "compliance_status",
        "compliance_level", "priority", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return RequirementListSerializer
        return RequirementSerializer

    @action(detail=True, methods=["patch"])
    def assess(self, request, pk=None):
        """Quick compliance assessment for a single requirement."""
        requirement = self.get_object()
        serializer = RequirementSerializer(
            requirement, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        allowed_fields = {
            "compliance_status", "compliance_level",
            "compliance_evidence", "compliance_finding",
        }
        update_data = {
            k: v for k, v in serializer.validated_data.items()
            if k in allowed_fields
        }
        update_data["last_assessment_date"] = timezone.now().date()
        update_data["last_assessed_by"] = request.user
        for attr, value in update_data.items():
            setattr(requirement, attr, value)
        requirement.save()
        # Trigger recalculation up the chain
        if requirement.section:
            requirement.section.recalculate_compliance()
        requirement.framework.recalculate_compliance()
        return Response(RequirementSerializer(requirement).data)


class ComplianceAssessmentViewSet(
    ScopeFilterAPIMixin,
    ApprovableAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    viewsets.ModelViewSet,
):
    queryset = ComplianceAssessment.objects.select_related(
        "assessor",
    ).prefetch_related("scopes", "frameworks").all()
    filterset_class = ComplianceAssessmentFilter
    permission_classes = [CompliancePermission]
    permission_feature = "assessment"
    search_fields = ["name", "description"]
    ordering_fields = ["name", "assessment_start_date", "overall_compliance_level", "status", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ComplianceAssessmentListSerializer
        return ComplianceAssessmentSerializer

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        """Advance the assessment to the next status in the workflow."""
        assessment = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"detail": "status field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            assessment.transition_to(new_status)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # When closing, propagate results to requirements and frameworks
        if new_status == "closed":
            for result in assessment.results.all():
                req = result.requirement
                req.compliance_status = result.compliance_status
                req.compliance_level = result.compliance_level
                req.compliance_evidence = result.evidence
                req.compliance_finding = result.finding
                req.last_assessment_date = result.assessed_at.date()
                req.last_assessed_by = result.assessed_by
                req.save()
            for fw in assessment.frameworks.all():
                fw.recalculate_compliance()
                if assessment.assessment_end_date:
                    Framework.objects.filter(pk=fw.pk).update(
                        last_assessment_date=assessment.assessment_end_date,
                    )
        return Response(ComplianceAssessmentSerializer(assessment).data)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Assessment summary with KPIs."""
        assessment = self.get_object()
        return Response({
            "overall_compliance_level": float(assessment.overall_compliance_level),
            "total_requirements": assessment.total_requirements,
            "compliant_count": assessment.compliant_count,
            "major_non_conformity_count": assessment.major_non_conformity_count,
            "minor_non_conformity_count": assessment.minor_non_conformity_count,
            "observation_count": assessment.observation_count,
            "improvement_opportunity_count": assessment.improvement_opportunity_count,
            "strength_count": assessment.strength_count,
            "not_assessed_count": assessment.not_assessed_count,
        })


class AssessmentResultViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentResultSerializer
    permission_classes = [CompliancePermission]
    permission_feature = "assessment"

    def get_queryset(self):
        return AssessmentResult.objects.filter(
            assessment_id=self.kwargs["assessment_pk"]
        ).select_related("requirement")

    def perform_create(self, serializer):
        serializer.save(
            assessment_id=self.kwargs["assessment_pk"],
            assessed_by=self.request.user,
            assessed_at=timezone.now(),
        )
        # Recalculate assessment counts
        assessment = ComplianceAssessment.objects.get(
            pk=self.kwargs["assessment_pk"]
        )
        assessment.recalculate_counts()

    def perform_update(self, serializer):
        serializer.save()
        assessment = ComplianceAssessment.objects.get(
            pk=self.kwargs["assessment_pk"]
        )
        assessment.recalculate_counts()


class FindingViewSet(viewsets.ModelViewSet):
    serializer_class = FindingSerializer
    permission_classes = [CompliancePermission]
    permission_feature = "assessment"

    def get_queryset(self):
        return Finding.objects.filter(
            assessment_id=self.kwargs["assessment_pk"]
        ).select_related("assessor").prefetch_related("requirements")

    def get_serializer_class(self):
        if self.action == "list":
            return FindingListSerializer
        return FindingSerializer

    def perform_create(self, serializer):
        serializer.save(
            assessment_id=self.kwargs["assessment_pk"],
            assessor=self.request.user,
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save()


class RequirementMappingViewSet(viewsets.ModelViewSet):
    queryset = RequirementMapping.objects.select_related(
        "source_requirement__framework",
        "target_requirement__framework",
    ).all()
    serializer_class = RequirementMappingSerializer
    filterset_class = RequirementMappingFilter
    permission_classes = [CompliancePermission]
    permission_feature = "mapping"
    search_fields = ["description", "justification"]
    ordering_fields = ["mapping_type", "created_at"]

    def perform_create(self, serializer):
        mapping = serializer.save(created_by=self.request.user)
        # RM-02 / RM-03: auto-create inverse mapping
        inverse_type = None
        if mapping.mapping_type == "equivalent":
            inverse_type = "equivalent"
        elif mapping.mapping_type == "includes":
            inverse_type = "included_by"
        elif mapping.mapping_type == "included_by":
            inverse_type = "includes"

        if inverse_type:
            RequirementMapping.objects.get_or_create(
                source_requirement=mapping.target_requirement,
                target_requirement=mapping.source_requirement,
                defaults={
                    "mapping_type": inverse_type,
                    "coverage_level": mapping.coverage_level,
                    "description": mapping.description,
                    "justification": mapping.justification,
                    "created_by": self.request.user,
                },
            )


class ComplianceActionPlanViewSet(
    ScopeFilterAPIMixin,
    ApprovableAPIMixin,
    HistoryAPIMixin,
    CreatedByMixin,
    viewsets.ModelViewSet,
):
    queryset = ComplianceActionPlan.objects.select_related(
        "owner",
    ).prefetch_related("scopes", "risks", "findings", "assignees").all()
    filterset_class = ComplianceActionPlanFilter
    permission_classes = [CompliancePermission]
    permission_feature = "action_plan"
    search_fields = ["reference", "name", "description"]
    ordering_fields = [
        "reference", "name", "priority", "target_date",
        "progress_percentage", "status", "created_at",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ComplianceActionPlanListSerializer
        return ComplianceActionPlanSerializer

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        """Perform a status transition on an action plan."""
        action_plan = self.get_object()
        serializer = ActionPlanTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            action_plan.transition_to(
                serializer.validated_data["status"],
                request.user,
                serializer.validated_data.get("comment", ""),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplianceActionPlanSerializer(action_plan).data)

    @action(detail=True, methods=["get"], url_path="transitions")
    def transitions(self, request, pk=None):
        """Get transition history for an action plan."""
        action_plan = self.get_object()
        qs = action_plan.transitions.all()
        serializer = ActionPlanTransitionHistorySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def kanban(self, request):
        """Get action plans grouped by status for kanban view."""
        qs = self.filter_queryset(self.get_queryset())
        result = {}
        for status_choice in ActionPlanStatus:
            plans = qs.filter(status=status_choice.value)
            result[status_choice.value] = ComplianceActionPlanListSerializer(plans, many=True).data
        return Response(result)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Action plans dashboard KPIs."""
        qs = self.filter_queryset(self.get_queryset())
        total = qs.count()
        by_status = {}
        for item in qs.values("status"):
            st = item["status"]
            by_status[st] = by_status.get(st, 0) + 1
        by_priority = {}
        for item in qs.values("priority"):
            p = item["priority"]
            by_priority[p] = by_priority.get(p, 0) + 1
        overdue = qs.filter(
            target_date__lt=timezone.now().date()
        ).exclude(status__in=[ActionPlanStatus.CLOSED, ActionPlanStatus.CANCELLED]).count()
        return Response({
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue": overdue,
        })

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        """List or create comments on an action plan."""
        action_plan = self.get_object()

        if request.method == "GET":
            qs = (
                action_plan.comments.filter(parent__isnull=True)
                .select_related("author")
                .prefetch_related(
                    Prefetch(
                        "replies",
                        queryset=ActionPlanComment.objects.select_related("author"),
                    )
                )
            )
            serializer = ActionPlanCommentSerializer(qs, many=True)
            return Response(serializer.data)

        # POST
        serializer = ActionPlanCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parent = None
        parent_id = serializer.validated_data.get("parent")
        if parent_id:
            try:
                parent = ActionPlanComment.objects.get(
                    pk=parent_id, action_plan=action_plan
                )
            except ActionPlanComment.DoesNotExist:
                return Response(
                    {"detail": "Parent comment not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if parent.parent_id is not None:
                parent = parent.parent

        comment = ActionPlanComment.objects.create(
            action_plan=action_plan,
            author=request.user,
            content=serializer.validated_data["content"],
            parent=parent,
        )
        return Response(
            ActionPlanCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )
