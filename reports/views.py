from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, FormView, ListView

from .constants import ReportStatus, ReportType
from .forms import SoaReportForm
from .generators import generate_soa_pdf
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
            )
            report.frameworks.set(frameworks)
            report.file.save(filename, ContentFile(pdf_bytes), save=True)
        except Exception:
            Report.objects.create(
                report_type=ReportType.SOA,
                name=report_name,
                status=ReportStatus.FAILED,
                created_by=self.request.user,
            )

        return redirect("reports:report-list")


class ReportDeleteView(LoginRequiredMixin, DeleteView):
    model = Report
    success_url = reverse_lazy("reports:report-list")
    template_name = "reports/report_confirm_delete.html"
