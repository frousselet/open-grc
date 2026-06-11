from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    EbiosIterationType,
    EbiosWorkshopNumber,
    EbiosWorkshopStatus,
)


class EbiosWorkshopProgress(BaseModel):
    """Tracks the progression of an EBIOS RM workshop for an assessment.

    Six instances are created automatically when an assessment with
    methodology=ebios_rm is created (W0..W5, iteration_type=strategic,
    iteration_number=1). New iterations are created via the `iterate` action.
    """

    WORKFLOW_NAME = "ebios_workshop"

    REFERENCE_PREFIX = "EWSP"

    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_workshops",
        verbose_name=_("Assessment"),
    )
    workshop_number = models.IntegerField(
        _("Workshop number"),
        choices=EbiosWorkshopNumber.choices,
    )
    iteration_type = models.CharField(
        _("Iteration type"),
        max_length=20,
        choices=EbiosIterationType.choices,
        default=EbiosIterationType.STRATEGIC,
    )
    iteration_number = models.PositiveIntegerField(
        _("Iteration number"),
        default=1,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=EbiosWorkshopStatus.choices,
        default=EbiosWorkshopStatus.NOT_STARTED,
    )
    started_at = models.DateTimeField(_("Started at"), null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_workshops_validated",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validated at"), null=True, blank=True)
    rejection_reason = models.TextField(_("Rejection reason"), blank=True)
    deliverables_summary = models.TextField(_("Deliverables summary"), blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["assessment", "iteration_number", "workshop_number"]
        verbose_name = _("EBIOS RM workshop progress")
        verbose_name_plural = _("EBIOS RM workshop progress")
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "workshop_number", "iteration_type", "iteration_number"],
                name="unique_ebios_workshop_iteration",
            ),
        ]

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_assessment"

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, EbiosWorkshopStatus.NOT_STARTED)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} : W{self.workshop_number} ({self.get_status_display()})"
