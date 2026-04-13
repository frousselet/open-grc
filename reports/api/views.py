import logging

from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.api.permissions import ModulePermission
from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment, Framework
from reports.constants import ReportStatus, ReportType
from reports.generators import generate_audit_report_pdf, generate_soa_pdf
from reports.management_review import (
    generate_management_review_docx,
    generate_management_review_pptx,
)
from reports.models import Report
from .serializers import (
    AuditReportCreateSerializer,
    ManagementReviewCreateSerializer,
    ReportSerializer,
    SoaReportCreateSerializer,
)


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"
    permission_feature = "report"
    custom_action_map = {
        "generate_soa": "create",
        "generate_audit_report": "create",
        "generate_management_review": "create",
    }

    @action(detail=False, methods=["post"], url_path="generate-soa")
    def generate_soa(self, request):
        ser = SoaReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        frameworks = Framework.objects.filter(id__in=ser.validated_data["framework_ids"])
        if not frameworks.exists():
            return Response(
                {"detail": _("No frameworks found for given IDs.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fw_names = ", ".join(fw.short_name or fw.name for fw in frameworks)
        report_name = _("Statement of Applicability") + f" — {fw_names}"

        try:
            filename, pdf_bytes = generate_soa_pdf(frameworks, request.user)
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=request.user,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(frameworks)
        except Exception:
            logging.getLogger(__name__).exception("SoA PDF generation failed")
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=request.user,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-audit-report")
    def generate_audit_report(self, request):
        ser = AuditReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            assessment = ComplianceAssessment.objects.get(
                id=ser.validated_data["assessment_id"],
            )
        except ComplianceAssessment.DoesNotExist:
            return Response(
                {"detail": _("Assessment not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if assessment.status not in (AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED):
            return Response(
                {"detail": _("The assessment must be completed or closed to generate a report.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report_name = _("Audit report") + f" — {assessment.reference} : {assessment.name}"

        try:
            filename, pdf_bytes = generate_audit_report_pdf(assessment, request.user)
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=request.user,
                assessment=assessment,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(assessment.frameworks.all())
        except Exception:
            logging.getLogger(__name__).exception("Audit report PDF generation failed")
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=request.user,
                assessment=assessment,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-management-review")
    def generate_management_review(self, request):
        ser = ManagementReviewCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        fmt = ser.validated_data["format"]
        scope_ids = ser.validated_data.get("scope_ids") or None
        period_start = ser.validated_data.get("period_start")
        period_end = ser.validated_data.get("period_end")

        if fmt == "pptx":
            report_type = ReportType.MANAGEMENT_REVIEW_PPTX
            generator = generate_management_review_pptx
            label = _("Presentation")
        else:
            report_type = ReportType.MANAGEMENT_REVIEW_DOCX
            generator = generate_management_review_docx
            label = _("Minutes")

        report_name = _("Management review") + f" - {label}"

        try:
            filename, file_bytes = generator(
                request.user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            report = Report.objects.create(
                report_type=report_type,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=request.user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Management review %s generation failed", fmt.upper()
            )
            report = Report.objects.create(
                report_type=report_type,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=request.user,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
