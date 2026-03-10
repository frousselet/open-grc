from rest_framework import serializers

from reports.models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id", "report_type", "name", "status", "frameworks",
            "file", "created_at", "created_by",
        ]
        read_only_fields = [
            "id", "file", "created_at", "created_by", "status", "name",
        ]


class SoaReportCreateSerializer(serializers.Serializer):
    framework_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of framework UUIDs to include in the SoA.",
    )
