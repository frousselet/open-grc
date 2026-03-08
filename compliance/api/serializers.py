from rest_framework import serializers

from compliance.models import (
    Auditor,
    ComplianceActionPlan,
    ComplianceAssessment,
    ComplianceAudit,
    ComplianceControl,
    AssessmentResult,
    ControlBody,
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
            "status", "review_date", "version", "tags",
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
            "compliance_level", "status", "owner", "created_at",
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
            "compliance_evidence", "compliance_gaps",
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
            "evidence", "gaps", "observations",
            "assessed_by", "assessed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComplianceAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAssessment
        fields = [
            "id", "scopes", "framework", "name", "description",
            "assessment_date", "assessor", "methodology",
            "overall_compliance_level",
            "total_requirements", "compliant_count",
            "partially_compliant_count", "non_compliant_count",
            "not_assessed_count",
            "status", "validated_by", "validated_at",
            "review_date", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
            "overall_compliance_level", "total_requirements",
            "compliant_count", "partially_compliant_count",
            "non_compliant_count", "not_assessed_count",
            "validated_by", "validated_at",
        ]


class ComplianceAssessmentListSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source="framework.name", read_only=True)

    class Meta:
        model = ComplianceAssessment
        fields = [
            "id", "scopes", "framework", "framework_name",
            "name", "assessment_date", "assessor",
            "overall_compliance_level", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


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
    requirement_reference = serializers.CharField(
        source="requirement.reference", read_only=True, default=""
    )
    framework_name = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceActionPlan
        fields = [
            "id", "scopes", "reference", "name", "description",
            "assessment", "requirement", "requirement_reference",
            "framework_name",
            "gap_description", "remediation_plan",
            "priority", "owner",
            "start_date", "target_date", "completion_date",
            "progress_percentage", "cost_estimate",
            "status", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]

    def get_framework_name(self, obj):
        if obj.requirement and obj.requirement.framework:
            return obj.requirement.framework.name
        return ""


class ComplianceActionPlanListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceActionPlan
        fields = [
            "id", "scopes", "reference", "name",
            "priority", "owner", "target_date",
            "progress_percentage", "status", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# ── Control ───────────────────────────────────────────────

class ComplianceControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceControl
        fields = [
            "id", "scopes", "reference", "name", "description", "objective",
            "frequency", "status", "result",
            "planned_date", "completion_date",
            "owner", "support_asset", "site", "supplier",
            "evidence", "findings",
            "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ComplianceControlListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceControl
        fields = [
            "id", "scopes", "reference", "name",
            "frequency", "status", "result",
            "planned_date", "owner", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# ── Audit ─────────────────────────────────────────────────

class ComplianceAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAudit
        fields = [
            "id", "scopes", "reference", "name", "description",
            "audit_type", "status",
            "frameworks", "sections",
            "lead_auditor", "control_body",
            "planned_start_date", "planned_end_date",
            "actual_start_date", "actual_end_date",
            "objectives", "conclusion", "findings_summary",
            "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ComplianceAuditListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAudit
        fields = [
            "id", "scopes", "reference", "name",
            "audit_type", "status",
            "planned_start_date", "lead_auditor", "control_body",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# ── Control Body ──────────────────────────────────────────

class ControlBodySerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlBody
        fields = [
            "id", "reference", "name", "description",
            "is_accredited", "accreditation_details",
            "contact_name", "contact_email", "contact_phone",
            "website", "address", "country",
            "frameworks",
            "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ControlBodyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlBody
        fields = [
            "id", "reference", "name",
            "is_accredited", "country",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# ── Auditor ───────────────────────────────────────────────

class AuditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auditor
        fields = [
            "id", "reference", "first_name", "last_name",
            "email", "phone",
            "control_body",
            "certifications", "cv", "specializations",
            "version", "tags",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "version",
        ]


class AuditorListSerializer(serializers.ModelSerializer):
    control_body_name = serializers.CharField(
        source="control_body.name", read_only=True
    )

    class Meta:
        model = Auditor
        fields = [
            "id", "reference", "first_name", "last_name",
            "email", "control_body", "control_body_name",
            "certifications", "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]


# ── Finding ──────────────────────────────────────────────

class FindingSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_resolved = serializers.BooleanField(read_only=True)

    class Meta:
        model = Finding
        fields = [
            "id", "scopes", "reference", "name", "description",
            "finding_type",
            "audit", "control",
            "action_plans", "activities", "requirements", "related_findings",
            "evidence",
            "status", "is_resolved",
            "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
            "status", "is_resolved",
        ]


class FindingListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_resolved = serializers.BooleanField(read_only=True)
    audit_reference = serializers.CharField(
        source="audit.reference", read_only=True, default=""
    )
    control_reference = serializers.CharField(
        source="control.reference", read_only=True, default=""
    )

    class Meta:
        model = Finding
        fields = [
            "id", "scopes", "reference", "name",
            "finding_type",
            "audit", "audit_reference",
            "control", "control_reference",
            "status", "is_resolved",
            "created_at",
        ]
        read_only_fields = ["id", "reference", "created_at"]
