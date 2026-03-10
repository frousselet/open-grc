import factory

from accounts.tests.factories import UserFactory
from reports.constants import ReportStatus, ReportType
from reports.models import Report


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    report_type = ReportType.SOA
    name = factory.Sequence(lambda n: f"Report {n}")
    status = ReportStatus.COMPLETED
    created_by = factory.SubFactory(UserFactory)
