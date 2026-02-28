from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel


class ISO27005Risk(BaseModel):
    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="iso27005_risks",
        verbose_name=_("Assessment"),
    )
    threat = models.ForeignKey(
        "risks.Threat",
        on_delete=models.CASCADE,
        related_name="iso27005_risks",
        verbose_name=_("Threat"),
    )
    vulnerability = models.ForeignKey(
        "risks.Vulnerability",
        on_delete=models.CASCADE,
        related_name="iso27005_risks",
        verbose_name=_("Vulnerability"),
    )
    affected_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="iso27005_risks",
        verbose_name=_("Affected essential assets"),
    )
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="iso27005_risks",
        verbose_name=_("Affected support assets"),
    )
    threat_likelihood = models.PositiveIntegerField(
        _("Threat likelihood"), null=True, blank=True
    )
    vulnerability_exposure = models.PositiveIntegerField(
        _("Vulnerability exposure"), null=True, blank=True
    )
    combined_likelihood = models.PositiveIntegerField(
        _("Combined likelihood"), null=True, blank=True
    )
    impact_confidentiality = models.PositiveIntegerField(
        _("Confidentiality impact"), null=True, blank=True
    )
    impact_integrity = models.PositiveIntegerField(
        _("Integrity impact"), null=True, blank=True
    )
    impact_availability = models.PositiveIntegerField(
        _("Availability impact"), null=True, blank=True
    )
    max_impact = models.PositiveIntegerField(
        _("Maximum impact"), null=True, blank=True
    )
    risk_level = models.PositiveIntegerField(
        _("Risk level"), null=True, blank=True
    )
    existing_controls = models.TextField(
        _("Existing controls"), blank=True
    )
    risk = models.ForeignKey(
        "risks.Risk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="iso27005_sources",
        verbose_name=_("Consolidated risk"),
    )
    description = models.TextField(_("Description"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("ISO 27005 analysis")
        verbose_name_plural = _("ISO 27005 analyses")

    def __str__(self):
        return f"{self.threat} × {self.vulnerability}"

    def save(self, *args, **kwargs):
        # Calculate combined_likelihood = max(threat_likelihood, vulnerability_exposure)
        values = [
            v for v in [self.threat_likelihood, self.vulnerability_exposure]
            if v is not None
        ]
        self.combined_likelihood = max(values) if values else None

        # Calculate max_impact = max of non-null impact values
        impacts = [
            v for v in [
                self.impact_confidentiality,
                self.impact_integrity,
                self.impact_availability,
            ]
            if v is not None
        ]
        self.max_impact = max(impacts) if impacts else None

        # Calculate risk_level via the assessment's criteria matrix
        if self.combined_likelihood is not None and self.max_impact is not None:
            criteria = getattr(self.assessment, "risk_criteria", None)
            if criteria and criteria.risk_matrix:
                key = f"{self.combined_likelihood},{self.max_impact}"
                level = criteria.risk_matrix.get(key)
                if level is not None:
                    self.risk_level = int(level)

        super().save(*args, **kwargs)
