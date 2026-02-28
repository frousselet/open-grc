from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import AcceptanceStatus


class RiskAcceptance(BaseModel):
    risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.CASCADE,
        related_name="acceptances",
        verbose_name="Risque",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_acceptances",
        verbose_name="Accepté par",
    )
    accepted_at = models.DateTimeField("Date d'acceptation", null=True, blank=True)
    risk_level_at_acceptance = models.PositiveIntegerField(
        "Niveau de risque à l'acceptation", null=True, blank=True
    )
    justification = models.TextField("Justification")
    conditions = models.TextField("Conditions", blank=True)
    valid_until = models.DateField("Valide jusqu'au", null=True, blank=True)
    review_date = models.DateField("Date de revue", null=True, blank=True)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=AcceptanceStatus.choices,
        default=AcceptanceStatus.ACTIVE,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Acceptation de risque"
        verbose_name_plural = "Acceptations de risque"

    def __str__(self):
        return f"Acceptation — {self.risk}"
