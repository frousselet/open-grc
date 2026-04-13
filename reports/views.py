import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, FormView, ListView

from accounts.views import PermissionRequiredMixin

from .constants import ReportStatus, ReportType
from .forms import AuditReportForm, ManagementReviewForm, SoaReportForm
from .generators import generate_audit_report_pdf, generate_soa_pdf
from .management_review import (
    generate_management_review_docx,
    generate_management_review_pptx,
)
from .models import Report


class ReportListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "reports.report.read"
    model = Report
    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 25


class SoaReportCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "reports.report.create"
    form_class = SoaReportForm
    template_name = "reports/soa_form.html"

    def form_valid(self, form):
        frameworks = form.cleaned_data["frameworks"]
        fw_names = ", ".join(fw.short_name or fw.name for fw in frameworks)
        report_name = _("Statement of Applicability") + f" — {fw_names}"

        try:
            filename, pdf_bytes = generate_soa_pdf(frameworks, self.request.user)
            report = Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=self.request.user,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(frameworks)
        except Exception:
            logging.getLogger(__name__).exception("SoA PDF generation failed")
            Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=self.request.user,
            )

        return redirect("reports:report-list")


class AuditReportCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "reports.report.create"
    form_class = AuditReportForm
    template_name = "reports/audit_report_form.html"

    def form_valid(self, form):
        assessment = form.cleaned_data["assessment"]
        report_name = _("Audit report") + f" — {assessment.reference} : {assessment.name}"

        try:
            filename, pdf_bytes = generate_audit_report_pdf(
                assessment, self.request.user
            )
            report = Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=self.request.user,
                assessment=assessment,
                file_content=pdf_bytes,
                file_name=filename,
            )
            report.frameworks.set(assessment.frameworks.all())
        except Exception:
            logging.getLogger(__name__).exception("Audit report PDF generation failed")
            Report.objects.create(
                report_type=ReportType.AUDIT_REPORT,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=self.request.user,
                assessment=assessment,
            )

        return redirect("reports:report-list")


class ManagementReviewCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "reports.report.create"
    form_class = ManagementReviewForm
    template_name = "reports/management_review_form.html"

    def form_valid(self, form):
        fmt = form.cleaned_data["format"]
        scopes = form.cleaned_data.get("scopes")
        scope_ids = list(scopes.values_list("id", flat=True)) if scopes else None
        period_start = form.cleaned_data.get("period_start")
        period_end = form.cleaned_data.get("period_end")

        if fmt == "pptx":
            report_type = ReportType.MANAGEMENT_REVIEW_PPTX
            generator = generate_management_review_pptx
        else:
            report_type = ReportType.MANAGEMENT_REVIEW_DOCX
            generator = generate_management_review_docx

        report_name = _("Management review") + f" - {_('Presentation') if fmt == 'pptx' else _('Minutes')}"

        try:
            filename, file_bytes = generator(
                self.request.user, scope_ids,
                period_start=period_start, period_end=period_end,
            )
            Report.objects.create(
                report_type=report_type,
                name=report_name,
                status=ReportStatus.COMPLETED,
                created_by=self.request.user,
                file_content=file_bytes,
                file_name=filename,
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "Management review %s generation failed", fmt.upper()
            )
            Report.objects.create(
                report_type=report_type,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=self.request.user,
            )

        return redirect("reports:report-list")


class ReportDownloadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "reports.report.read"
    """Serve report file content stored in the database."""

    CONTENT_TYPES = {
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        if not report.file_content:
            raise Http404
        import os
        ext = os.path.splitext(report.file_name)[1].lower()
        content_type = self.CONTENT_TYPES.get(ext, "application/octet-stream")
        response = HttpResponse(
            bytes(report.file_content),
            content_type=content_type,
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{report.file_name}"'
        )
        return response


class ReportDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "reports.report.delete"
    model = Report
    success_url = reverse_lazy("reports:report-list")
    template_name = "reports/report_confirm_delete.html"
