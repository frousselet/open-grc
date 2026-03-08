from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import ControlFrequency, ControlResult, ControlStatus
from context.models.base import ScopedModel


class ComplianceControl(ScopedModel):
    REFERENCE_PREFIX = "CTRL"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    objective = models.TextField(_("Objective"), blank=True, default="")

    frequency = models.CharField(
        _("Frequency"),
        max_length=20,
        choices=ControlFrequency.choices,
        default=ControlFrequency.ONE_TIME,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ControlStatus.choices,
        default=ControlStatus.PLANNED,
    )
    result = models.CharField(
        _("Result"),
        max_length=25,
        choices=ControlResult.choices,
        default=ControlResult.NOT_ASSESSED,
    )

    planned_date = models.DateField(_("Planned date"), null=True, blank=True)
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_controls_owned",
        verbose_name=_("Owner"),
    )

    # Linked entities
    support_asset = models.ForeignKey(
        "assets.SupportAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_controls",
        verbose_name=_("Support asset"),
    )
    site = models.ForeignKey(
        "context.Site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_controls",
        verbose_name=_("Site"),
    )
    supplier = models.ForeignKey(
        "assets.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_controls",
        verbose_name=_("Supplier"),
    )

    evidence = models.TextField(_("Evidence"), blank=True, default="")
    findings = models.TextField(_("Findings"), blank=True, default="")

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Control")
        verbose_name_plural = _("Controls")

    def __str__(self):
        return f"{self.reference} : {self.name}"
