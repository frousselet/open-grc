from rest_framework import serializers

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


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]


class ScopeSerializer(serializers.ModelSerializer):
    parent_scope_name = serializers.CharField(
        source="parent_scope.name", read_only=True, default=None
    )

    class Meta:
        model = Scope
        fields = [
            "id", "name", "description", "parent_scope", "parent_scope_name",
            "version", "status",
            "boundaries", "justification_exclusions",
            "geographic_scope", "organizational_scope", "technical_scope",
            "included_sites", "excluded_sites",
            "is_approved", "approved_by", "approved_at",
            "effective_date", "review_date", "tags",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class SiteSerializer(serializers.ModelSerializer):
    parent_site_name = serializers.CharField(
        source="parent_site.name", read_only=True, default=None
    )

    class Meta:
        model = Site
        fields = [
            "id", "name", "type", "address", "description",
            "parent_site", "parent_site_name", "status", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = [
            "id", "scope", "name", "description", "type", "category",
            "impact_level", "trend", "source", "related_stakeholders",
            "review_date", "status", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class StakeholderExpectationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StakeholderExpectation
        fields = [
            "id", "stakeholder", "description", "type", "priority",
            "is_applicable", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StakeholderSerializer(serializers.ModelSerializer):
    expectations = StakeholderExpectationSerializer(many=True, read_only=True)

    class Meta:
        model = Stakeholder
        fields = [
            "id", "scope", "name", "type", "category", "description",
            "contact_name", "contact_email", "contact_phone",
            "influence_level", "interest_level", "expectations",
            "status", "review_date", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class StakeholderListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views (no nested expectations)."""

    class Meta:
        model = Stakeholder
        fields = [
            "id", "scope", "name", "type", "category",
            "influence_level", "interest_level", "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = [
            "id", "scope", "reference", "name", "description",
            "category", "type", "target_value", "current_value", "unit",
            "measurement_method", "measurement_frequency", "target_date",
            "owner", "status", "progress_percentage",
            "related_issues", "related_stakeholders", "parent_objective",
            "review_date", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class SwotItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwotItem
        fields = [
            "id", "swot_analysis", "quadrant", "description", "impact_level",
            "related_issues", "related_objectives", "order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SwotAnalysisSerializer(serializers.ModelSerializer):
    items = SwotItemSerializer(many=True, read_only=True)

    class Meta:
        model = SwotAnalysis
        fields = [
            "id", "scope", "name", "description", "analysis_date",
            "status", "validated_by", "validated_at", "items",
            "review_date", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class SwotAnalysisListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    class Meta:
        model = SwotAnalysis
        fields = [
            "id", "scope", "name", "analysis_date", "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ResponsibilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsibility
        fields = [
            "id", "role", "description", "raci_type", "related_activity",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RoleSerializer(serializers.ModelSerializer):
    responsibilities = ResponsibilitySerializer(many=True, read_only=True)
    compliance_alert = serializers.CharField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id", "scope", "name", "description", "type",
            "assigned_users", "is_mandatory", "source_standard",
            "status", "responsibilities", "compliance_alert",
            "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class RoleListSerializer(serializers.ModelSerializer):
    assigned_users_count = serializers.IntegerField(
        source="assigned_users.count", read_only=True
    )

    class Meta:
        model = Role
        fields = [
            "id", "scope", "name", "type", "status",
            "is_mandatory", "assigned_users_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "id", "scope", "reference", "name", "description",
            "type", "criticality", "owner", "parent_activity",
            "related_stakeholders", "related_objectives",
            "status", "version", "tags",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]
