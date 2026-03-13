import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from reports.constants import ReportStatus, ReportType


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(
        _("Report type"),
        max_length=30,
        choices=ReportType.choices,
    )
    name = models.CharField(_("Name"), max_length=255)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.COMPLETED,
    )
    assessment = models.ForeignKey(
        "compliance.ComplianceAssessment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name=_("Assessment"),
    )
    frameworks = models.ManyToManyField(
        "compliance.Framework",
        related_name="reports",
        verbose_name=_("Frameworks"),
        blank=True,
    )
    file = models.FileField(
        _("File"),
        upload_to="reports/%Y/%m/",
        blank=True,
    )
    file_content = models.BinaryField(
        _("File content"),
        blank=True,
        null=True,
        editable=False,
    )
    file_name = models.CharField(
        _("File name"),
        max_length=255,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_created",
        verbose_name=_("Created by"),
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return self.name
