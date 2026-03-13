import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, FormView, ListView

from .constants import ReportStatus, ReportType
from .forms import AuditReportForm, SoaReportForm
from .generators import generate_audit_report_pdf, generate_soa_pdf
from .models import Report


class ReportListView(LoginRequiredMixin, ListView):
    model = Report
    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 25


class SoaReportCreateView(LoginRequiredMixin, FormView):
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


class AuditReportCreateView(LoginRequiredMixin, FormView):
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


class ReportDownloadView(LoginRequiredMixin, View):
    """Serve report file content stored in the database."""

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        if not report.file_content:
            raise Http404
        response = HttpResponse(
            bytes(report.file_content),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{report.file_name}"'
        )
        return response


class ReportDeleteView(LoginRequiredMixin, DeleteView):
    model = Report
    success_url = reverse_lazy("reports:report-list")
    template_name = "reports/report_confirm_delete.html"
