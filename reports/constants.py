from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportType(models.TextChoices):
    SOA = "soa", _("Statement of Applicability")
    AUDIT_REPORT = "audit_report", _("Audit report")
    MANAGEMENT_REVIEW_PPTX = "management_review_pptx", _("Management review - Presentation")
    MANAGEMENT_REVIEW_DOCX = "management_review_docx", _("Management review - Minutes")


class ReportStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    GENERATING = "generating", _("Generating")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
