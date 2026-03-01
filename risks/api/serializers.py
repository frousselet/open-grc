from rest_framework import serializers

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


class ScaleLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScaleLevel
        fields = [
            "id", "criteria", "scale_type", "level", "name", "description", "color",
        ]
        read_only_fields = ["id"]


class RiskLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskLevel
        fields = [
            "id", "criteria", "level", "name", "description", "color", "requires_treatment",
        ]
        read_only_fields = ["id"]


class RiskCriteriaSerializer(serializers.ModelSerializer):
    scale_levels = ScaleLevelSerializer(many=True, read_only=True)
    risk_levels = RiskLevelSerializer(many=True, read_only=True)

    class Meta:
        model = RiskCriteria
        fields = [
            "id", "scope", "name", "description", "risk_matrix",
            "acceptance_threshold", "is_default", "status",
            "scale_levels", "risk_levels", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class RiskCriteriaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCriteria
        fields = [
            "id", "scope", "name", "is_default", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RiskAssessmentSerializer(serializers.ModelSerializer):
    assessor_name = serializers.CharField(source="assessor.get_full_name", read_only=True, default="")

    class Meta:
        model = RiskAssessment
        fields = [
            "id", "scope", "reference", "name", "description", "methodology",
            "assessment_date", "assessor", "assessor_name", "risk_criteria",
            "status", "validated_by", "validated_at", "next_review_date", "summary", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class RiskAssessmentListSerializer(serializers.ModelSerializer):
    assessor_name = serializers.CharField(source="assessor.get_full_name", read_only=True, default="")

    class Meta:
        model = RiskAssessment
        fields = [
            "id", "scope", "reference", "name", "methodology",
            "assessment_date", "assessor", "assessor_name",
            "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RiskSerializer(serializers.ModelSerializer):
    risk_owner_name = serializers.CharField(source="risk_owner.get_full_name", read_only=True, default="")

    class Meta:
        model = Risk
        fields = [
            "id", "assessment", "reference", "name", "description",
            "risk_source", "source_entity_id", "source_entity_type",
            "affected_essential_assets", "affected_support_assets",
            "impact_confidentiality", "impact_integrity", "impact_availability",
            "initial_likelihood", "initial_impact", "initial_risk_level",
            "current_likelihood", "current_impact", "current_risk_level",
            "residual_likelihood", "residual_impact", "residual_risk_level",
            "treatment_decision", "treatment_justification",
            "risk_owner", "risk_owner_name", "priority", "status", "review_date", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "initial_risk_level", "current_risk_level", "residual_risk_level",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class RiskListSerializer(serializers.ModelSerializer):
    risk_owner_name = serializers.CharField(source="risk_owner.get_full_name", read_only=True, default="")

    class Meta:
        model = Risk
        fields = [
            "id", "assessment", "reference", "name", "risk_source",
            "current_risk_level", "priority", "status",
            "risk_owner", "risk_owner_name", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TreatmentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentAction
        fields = [
            "id", "treatment_plan", "description", "owner",
            "target_date", "completion_date", "status", "order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RiskTreatmentPlanSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True, default="")
    actions = TreatmentActionSerializer(many=True, read_only=True)

    class Meta:
        model = RiskTreatmentPlan
        fields = [
            "id", "risk", "reference", "name", "description", "treatment_type",
            "expected_residual_likelihood", "expected_residual_impact",
            "cost_estimate", "owner", "owner_name",
            "start_date", "target_date", "completion_date",
            "progress_percentage", "status", "actions", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class RiskTreatmentPlanListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True, default="")

    class Meta:
        model = RiskTreatmentPlan
        fields = [
            "id", "risk", "reference", "name", "treatment_type",
            "owner", "owner_name", "target_date",
            "progress_percentage", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RiskAcceptanceSerializer(serializers.ModelSerializer):
    accepted_by_name = serializers.CharField(source="accepted_by.get_full_name", read_only=True, default="")

    class Meta:
        model = RiskAcceptance
        fields = [
            "id", "risk", "accepted_by", "accepted_by_name", "accepted_at",
            "risk_level_at_acceptance", "justification", "conditions",
            "valid_until", "review_date", "status", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ThreatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Threat
        fields = [
            "id", "scope", "reference", "name", "description",
            "type", "origin", "category", "typical_likelihood",
            "is_from_catalog", "status", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ThreatListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Threat
        fields = [
            "id", "scope", "reference", "name", "type", "origin",
            "category", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VulnerabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vulnerability
        fields = [
            "id", "scope", "reference", "name", "description",
            "category", "severity", "affected_asset_types",
            "affected_assets", "cve_references", "remediation_guidance",
            "is_from_catalog", "status", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class VulnerabilityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vulnerability
        fields = [
            "id", "scope", "reference", "name", "category",
            "severity", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ISO27005RiskSerializer(serializers.ModelSerializer):
    threat_name = serializers.CharField(source="threat.name", read_only=True)
    vulnerability_name = serializers.CharField(source="vulnerability.name", read_only=True)

    class Meta:
        model = ISO27005Risk
        fields = [
            "id", "assessment", "threat", "threat_name",
            "vulnerability", "vulnerability_name",
            "affected_essential_assets", "affected_support_assets",
            "threat_likelihood", "vulnerability_exposure", "combined_likelihood",
            "impact_confidentiality", "impact_integrity", "impact_availability",
            "max_impact", "risk_level", "existing_controls",
            "risk", "description", "tags",
            "version", "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "combined_likelihood", "max_impact", "risk_level",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class ISO27005RiskListSerializer(serializers.ModelSerializer):
    threat_name = serializers.CharField(source="threat.name", read_only=True)
    vulnerability_name = serializers.CharField(source="vulnerability.name", read_only=True)

    class Meta:
        model = ISO27005Risk
        fields = [
            "id", "assessment", "threat", "threat_name",
            "vulnerability", "vulnerability_name",
            "combined_likelihood", "max_impact", "risk_level",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
