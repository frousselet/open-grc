from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from risks.constants import ThreatCategory, ThreatOrigin, ThreatStatus, ThreatType


class Threat(ScopedModel):
    REFERENCE_PREFIX = "THRT"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    type = models.CharField(
        _("Type"), max_length=20, choices=ThreatType.choices
    )
    origin = models.CharField(
        _("Origin"), max_length=20, choices=ThreatOrigin.choices, blank=True
    )
    category = models.CharField(
        _("Category"), max_length=30, choices=ThreatCategory.choices, blank=True
    )
    typical_likelihood = models.PositiveIntegerField(
        _("Typical likelihood"), null=True, blank=True
    )
    is_from_catalog = models.BooleanField(_("From catalog"), default=False)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ThreatStatus.choices,
        default=ThreatStatus.ACTIVE,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = _("Threat")
        verbose_name_plural = _("Threats")

    def __str__(self):
        return f"{self.reference} : {self.name}"
