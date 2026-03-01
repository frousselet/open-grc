from rest_framework import serializers

from assets.models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    EssentialAsset,
    Supplier,
    SupplierRequirement,
    SupportAsset,
)


class AssetValuationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetValuation
        fields = [
            "id", "essential_asset", "evaluation_date",
            "confidentiality_level", "integrity_level", "availability_level",
            "evaluated_by", "justification", "context", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AssetDependencySerializer(serializers.ModelSerializer):
    essential_asset_name = serializers.CharField(
        source="essential_asset.name", read_only=True
    )
    support_asset_name = serializers.CharField(
        source="support_asset.name", read_only=True
    )

    class Meta:
        model = AssetDependency
        fields = [
            "id", "essential_asset", "essential_asset_name",
            "support_asset", "support_asset_name",
            "dependency_type", "criticality", "description",
            "is_single_point_of_failure", "redundancy_level",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class EssentialAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = EssentialAsset
        fields = [
            "id", "scope", "reference", "name", "description",
            "type", "category", "owner", "custodian",
            "confidentiality_level", "integrity_level", "availability_level",
            "confidentiality_justification", "integrity_justification",
            "availability_justification",
            "max_tolerable_downtime", "recovery_time_objective",
            "recovery_point_objective",
            "data_classification", "personal_data",
            "personal_data_categories", "regulatory_constraints",
            "related_activities", "status", "review_date", "tags",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class EssentialAssetListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    class Meta:
        model = EssentialAsset
        fields = [
            "id", "scope", "reference", "name", "type", "category",
            "owner", "owner_name",
            "confidentiality_level", "integrity_level", "availability_level",
            "data_classification", "personal_data", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SupportAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportAsset
        fields = [
            "id", "scope", "reference", "name", "description",
            "type", "category", "owner", "custodian",
            "location", "manufacturer", "model_name", "serial_number",
            "software_version", "ip_address", "hostname", "operating_system",
            "acquisition_date", "end_of_life_date", "warranty_expiry_date",
            "contract_reference",
            "inherited_confidentiality", "inherited_integrity",
            "inherited_availability",
            "exposure_level", "environment",
            "parent_asset", "status", "review_date", "tags",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "inherited_confidentiality", "inherited_integrity",
            "inherited_availability",
            "is_approved", "approved_by", "approved_at",
            "version",
        ]


class SupportAssetListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    class Meta:
        model = SupportAsset
        fields = [
            "id", "scope", "reference", "name", "type", "category",
            "owner", "owner_name",
            "inherited_confidentiality", "inherited_integrity",
            "inherited_availability",
            "environment", "exposure_level", "status",
            "end_of_life_date", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AssetGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(
        source="members.count", read_only=True
    )

    class Meta:
        model = AssetGroup
        fields = [
            "id", "scope", "name", "description", "type",
            "members", "owner", "status", "member_count", "tags",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "is_approved", "approved_by", "approved_at", "version"]


class AssetGroupListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(
        source="members.count", read_only=True
    )

    class Meta:
        model = AssetGroup
        fields = [
            "id", "scope", "name", "type", "owner",
            "status", "member_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SupplierRequirementSerializer(serializers.ModelSerializer):
    requirement_reference = serializers.CharField(
        source="requirement.reference", read_only=True, default=None
    )

    class Meta:
        model = SupplierRequirement
        fields = [
            "id", "supplier", "requirement", "requirement_reference",
            "title", "description",
            "compliance_status", "evidence", "due_date",
            "verified_at", "verified_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierSerializer(serializers.ModelSerializer):
    requirement_count = serializers.IntegerField(
        source="requirements.count", read_only=True
    )

    class Meta:
        model = Supplier
        fields = [
            "id", "scope", "reference", "name", "description",
            "type", "criticality", "owner",
            "contact_name", "contact_email", "contact_phone",
            "website", "address", "country",
            "contract_reference", "contract_start_date", "contract_end_date",
            "status", "notes", "tags",
            "requirement_count",
            "version",
            "is_approved", "approved_by", "approved_at",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "created_at", "updated_at",
            "is_approved", "approved_by", "approved_at", "version",
        ]


class SupplierListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    requirement_count = serializers.IntegerField(
        source="requirements.count", read_only=True
    )

    class Meta:
        model = Supplier
        fields = [
            "id", "scope", "reference", "name", "type", "criticality",
            "owner", "owner_name",
            "status", "contract_end_date", "requirement_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
