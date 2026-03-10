from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportType(models.TextChoices):
    SOA = "soa", _("Statement of Applicability")


class ReportStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    GENERATING = "generating", _("Generating")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
