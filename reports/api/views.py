import logging

from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment, Framework
from reports.constants import ReportStatus, ReportType
from reports.generators import generate_audit_report_pdf, generate_soa_pdf
from reports.models import Report
from .serializers import AuditReportCreateSerializer, ReportSerializer, SoaReportCreateSerializer


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

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
