from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import AcceptanceStatus


class RiskAcceptance(BaseModel):
    risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.CASCADE,
        related_name="acceptances",
        verbose_name=_("Risk"),
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_acceptances",
        verbose_name=_("Accepted by"),
    )
    accepted_at = models.DateTimeField(_("Acceptance date"), null=True, blank=True)
    risk_level_at_acceptance = models.PositiveIntegerField(
        _("Risk level at acceptance"), null=True, blank=True
    )
    justification = models.TextField(_("Justification"))
    conditions = models.TextField(_("Conditions"), blank=True)
    valid_until = models.DateField(_("Valid until"), null=True, blank=True)
    review_date = models.DateField(_("Review date"), null=True, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=AcceptanceStatus.choices,
        default=AcceptanceStatus.ACTIVE,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Risk acceptance")
        verbose_name_plural = _("Risk acceptances")

    def __str__(self):
        return f"Acceptance — {self.risk}"
