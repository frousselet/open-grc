import pytest

from reports.constants import ReportStatus, ReportType
from reports.models import Report
from .factories import ReportFactory

pytestmark = pytest.mark.django_db


class TestReportModel:
    def test_create_report(self):
        report = ReportFactory()
        assert report.pk is not None
        assert report.report_type == ReportType.SOA
        assert report.status == ReportStatus.COMPLETED

    def test_str(self):
        report = ReportFactory(name="Test SoA Report")
        assert str(report) == "Test SoA Report"

    def test_ordering(self):
        r1 = ReportFactory(name="First")
        r2 = ReportFactory(name="Second")
        reports = list(Report.objects.all())
        assert reports[0].name == "Second"
        assert reports[1].name == "First"
