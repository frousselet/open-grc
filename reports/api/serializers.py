from rest_framework import serializers

from reports.models import Report


class ReportSerializer(serializers.ModelSerializer):
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id", "report_type", "name", "status", "frameworks",
            "file_name", "has_file", "created_at", "created_by",
        ]
        read_only_fields = [
            "id", "file_name", "has_file", "created_at", "created_by",
            "status", "name",
        ]

    def get_has_file(self, obj):
        return bool(obj.file_content)


class SoaReportCreateSerializer(serializers.Serializer):
    framework_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of framework UUIDs to include in the SoA.",
    )


class AuditReportCreateSerializer(serializers.Serializer):
    assessment_id = serializers.UUIDField(
        help_text="UUID of a completed or closed compliance assessment.",
    )


class ManagementReviewCreateSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=["pptx", "docx"],
        help_text="Output format: 'pptx' for PowerPoint presentation, 'docx' for Word meeting minutes.",
    )
    scope_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="Optional list of scope UUIDs to filter data.",
    )
    period_start = serializers.DateField(
        required=False,
        default=None,
        help_text="Start of the review period (YYYY-MM-DD). Omit to include all past data.",
    )
    period_end = serializers.DateField(
        required=False,
        default=None,
        help_text="End of the review period (YYYY-MM-DD). Defaults to today.",
    )
