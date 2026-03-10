from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from compliance.tests.factories import FrameworkFactory, RequirementFactory
from reports.models import Report
from .factories import ReportFactory

pytestmark = pytest.mark.django_db


class TestReportListView:
    def test_login_required(self):
        client = Client()
        resp = client.get(reverse("reports:report-list"))
        assert resp.status_code == 302

    def test_list_reports(self):
        user = UserFactory()
        ReportFactory(created_by=user)
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("reports:report-list"))
        assert resp.status_code == 200
        assert b"Report" in resp.content


class TestSoaReportCreateView:
    def test_get_form(self):
        user = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("reports:soa-create"))
        assert resp.status_code == 200

    @patch("reports.views.generate_soa_pdf")
    def test_create_soa_report(self, mock_generate):
        mock_generate.return_value = ("SoA_test.pdf", b"%PDF-1.4 fake content")

        user = UserFactory()
        fw = FrameworkFactory()
        RequirementFactory(framework=fw, is_applicable=True)
        RequirementFactory(framework=fw, is_applicable=False, applicability_justification="Not relevant")

        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse("reports:soa-create"),
            {"frameworks": [str(fw.pk)]},
        )
        assert resp.status_code == 302
        assert Report.objects.count() == 1
        report = Report.objects.first()
        assert report.file_content
        assert report.file_name == "SoA_test.pdf"
        assert fw in report.frameworks.all()
        mock_generate.assert_called_once()

    @patch("reports.views.generate_soa_pdf", side_effect=Exception("PDF error"))
    def test_create_soa_report_failure(self, mock_generate):
        user = UserFactory()
        fw = FrameworkFactory()

        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse("reports:soa-create"),
            {"frameworks": [str(fw.pk)]},
        )
        assert resp.status_code == 302
        assert Report.objects.count() == 1
        report = Report.objects.first()
        assert report.status == "failed"


class TestReportDownloadView:
    def test_login_required(self):
        report = ReportFactory(file_content=b"%PDF-1.4 fake", file_name="test.pdf")
        client = Client()
        resp = client.get(reverse("reports:report-download", args=[report.pk]))
        assert resp.status_code == 302

    def test_download_pdf(self):
        user = UserFactory()
        report = ReportFactory(
            created_by=user,
            file_content=b"%PDF-1.4 fake content",
            file_name="SoA_test.pdf",
        )
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("reports:report-download", args=[report.pk]))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert 'filename="SoA_test.pdf"' in resp["Content-Disposition"]
        assert resp.content == b"%PDF-1.4 fake content"

    def test_download_no_file_returns_404(self):
        user = UserFactory()
        report = ReportFactory(created_by=user, file_content=None)
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("reports:report-download", args=[report.pk]))
        assert resp.status_code == 404


class TestReportDeleteView:
    def test_delete_report(self):
        user = UserFactory()
        report = ReportFactory(created_by=user)
        client = Client()
        client.force_login(user)
        resp = client.post(reverse("reports:report-delete", args=[report.pk]))
        assert resp.status_code == 302
        assert Report.objects.count() == 0
