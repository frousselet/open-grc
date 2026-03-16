from rest_framework import serializers

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


class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = [
            "id", "scopes", "reference", "name", "short_name", "description",
            "type", "category", "framework_version",
            "publication_date", "effective_date", "expiry_date",
            "issuing_body", "jurisdiction", "url",
            "is_mandatory", "is_applicable", "applicability_justification",
            "owner", "related_stakeholders",
            "compliance_level", "last_assessment_date",
            "status", "review_date",
            "logo", "logo_16", "logo_32", "logo_64",
            "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
            "compliance_level", "last_assessment_date",
        ]


class FrameworkListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = [
            "id", "scopes", "reference", "name", "short_name",
            "type", "category", "is_mandatory", "is_applicable",
            "compliance_level", "status", "owner", "logo_32",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = [
            "id", "framework", "parent_section", "reference", "name",
            "description", "order", "compliance_level",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "created_at", "updated_at", "compliance_level"]


class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = [
            "id", "framework", "section",
            "reference", "requirement_number", "name", "description", "guidance",
            "type", "category",
            "is_applicable", "applicability_justification",
            "compliance_status", "compliance_level",
            "compliance_evidence", "compliance_finding",
            "last_assessment_date", "last_assessed_by",
            "owner", "priority", "target_date",
            "linked_assets", "linked_stakeholder_expectations", "linked_risks",
            "status", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
            "last_assessment_date", "last_assessed_by",
        ]


class RequirementListSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source="framework.name", read_only=True)
    section_name = serializers.CharField(
        source="section.name", read_only=True, default=""
    )

    class Meta:
        model = Requirement
        fields = [
            "id", "framework", "framework_name",
            "section", "section_name",
            "reference", "requirement_number", "name", "type", "is_applicable",
            "compliance_status", "compliance_level",
            "priority", "owner", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class AssessmentResultSerializer(serializers.ModelSerializer):
    requirement_reference = serializers.CharField(
        source="requirement.reference", read_only=True
    )
    requirement_name = serializers.CharField(
        source="requirement.name", read_only=True
    )

    class Meta:
        model = AssessmentResult
        fields = [
            "id", "assessment", "requirement",
            "requirement_reference", "requirement_name",
            "compliance_status", "compliance_level",
            "finding", "auditor_recommendations", "evidence",
            "assessed_by", "assessed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FindingSerializer(serializers.ModelSerializer):
    finding_type_display = serializers.CharField(
        source="get_finding_type_display", read_only=True
    )

    class Meta:
        model = Finding
        fields = [
            "id", "assessment", "reference",
            "finding_type", "finding_type_display",
            "description", "recommendation", "evidence",
            "assessor", "requirements",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reference", "created_by", "created_at", "updated_at"]


class FindingListSerializer(serializers.ModelSerializer):
    finding_type_display = serializers.CharField(
        source="get_finding_type_display", read_only=True
    )

    class Meta:
        model = Finding
        fields = [
            "id", "assessment", "reference",
            "finding_type", "finding_type_display",
            "description", "assessor",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class ComplianceAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAssessment
        fields = [
            "id", "scopes", "frameworks", "name", "description", "limitations",
            "assessment_start_date", "assessment_end_date",
            "assessor",
            "overall_compliance_level",
            "total_requirements", "compliant_count",
            "major_non_conformity_count", "minor_non_conformity_count",
            "observation_count", "improvement_opportunity_count",
            "strength_count", "not_assessed_count", "not_applicable_count",
            "status", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
            "overall_compliance_level", "total_requirements",
            "compliant_count", "major_non_conformity_count",
            "minor_non_conformity_count", "observation_count",
            "improvement_opportunity_count", "strength_count",
            "not_assessed_count", "not_applicable_count",
        ]


class ComplianceAssessmentListSerializer(serializers.ModelSerializer):
    framework_names = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceAssessment
        fields = [
            "id", "scopes", "frameworks", "framework_names",
            "name", "assessment_start_date", "assessment_end_date",
            "assessor", "overall_compliance_level", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_framework_names(self, obj):
        return [fw.short_name or fw.name for fw in obj.frameworks.all()]


class RequirementMappingSerializer(serializers.ModelSerializer):
    source_reference = serializers.CharField(
        source="source_requirement.reference", read_only=True
    )
    target_reference = serializers.CharField(
        source="target_requirement.reference", read_only=True
    )
    source_framework_name = serializers.CharField(
        source="source_requirement.framework.name", read_only=True
    )
    target_framework_name = serializers.CharField(
        source="target_requirement.framework.name", read_only=True
    )

    class Meta:
        model = RequirementMapping
        fields = [
            "id", "source_requirement", "source_reference",
            "source_framework_name",
            "target_requirement", "target_reference",
            "target_framework_name",
            "mapping_type", "coverage_level",
            "description", "justification",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ComplianceActionPlanSerializer(serializers.ModelSerializer):
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceActionPlan
        fields = [
            "id", "scopes", "reference", "name", "description",
            "risks", "findings",
            "gap_description", "remediation_plan",
            "priority", "owner", "assignees",
            "start_date", "target_date", "completion_date",
            "progress_percentage", "cost_estimate",
            "status", "allowed_transitions", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
            "status",
        ]

    def get_allowed_transitions(self, obj):
        return obj.get_allowed_transitions()


class ActionPlanTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ActionPlanStatus.choices)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ActionPlanTransitionHistorySerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        from compliance.models import ActionPlanTransition
        model = ActionPlanTransition
        fields = [
            "id", "from_status", "to_status",
            "performed_by", "performed_by_name",
            "comment", "is_refusal", "created_at",
        ]
        read_only_fields = fields

    def get_performed_by_name(self, obj):
        return obj.performed_by.get_full_name() or obj.performed_by.email


class ComplianceActionPlanListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceActionPlan
        fields = [
            "id", "scopes", "reference", "name",
            "priority", "owner", "assignees", "target_date",
            "progress_percentage", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


class ActionPlanCommentReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ActionPlanComment
        fields = [
            "id", "author", "author_name", "content",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        return obj.author.display_name


class ActionPlanCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    replies = ActionPlanCommentReplySerializer(many=True, read_only=True)

    class Meta:
        model = ActionPlanComment
        fields = [
            "id", "author", "author_name", "content",
            "parent", "replies", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "author", "author_name", "replies",
            "created_at", "updated_at",
        ]

    def get_author_name(self, obj):
        return obj.author.display_name


class ActionPlanCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    parent = serializers.UUIDField(required=False, allow_null=True, default=None)
