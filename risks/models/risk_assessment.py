from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from risks.constants import AssessmentStatus, Methodology


class RiskAssessment(ScopedModel):
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True)
    methodology = models.CharField(
        "Méthodologie",
        max_length=20,
        choices=Methodology.choices,
        default=Methodology.ISO27005,
    )
    assessment_date = models.DateField("Date d'appréciation", null=True, blank=True)
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments_assessed",
        verbose_name="Appréciateur",
    )
    risk_criteria = models.ForeignKey(
        "risks.RiskCriteria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        verbose_name="Critères de risque",
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.DRAFT,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments_validated",
        verbose_name="Validé par",
    )
    validated_at = models.DateTimeField("Date de validation", null=True, blank=True)
    next_review_date = models.DateField("Prochaine revue", null=True, blank=True)
    summary = models.TextField("Synthèse", blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Appréciation des risques"
        verbose_name_plural = "Appréciations des risques"

    def __str__(self):
        return f"{self.reference} — {self.name}"
