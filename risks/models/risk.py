from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import (
    DEFAULT_IMPACT_SCALES,
    DEFAULT_LIKELIHOOD_SCALES,
    RiskPriority,
    RiskSourceType,
    RiskStatus,
    TreatmentDecision,
)


class Risk(BaseModel):
    assessment = models.ForeignKey(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="risks",
        verbose_name="Appréciation",
    )
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    description = models.TextField("Description", blank=True)
    risk_source = models.CharField(
        "Source du risque",
        max_length=30,
        choices=RiskSourceType.choices,
        default=RiskSourceType.MANUAL,
    )
    source_entity_id = models.UUIDField(
        "ID entité source", null=True, blank=True
    )
    source_entity_type = models.CharField(
        "Type entité source", max_length=100, blank=True
    )
    affected_essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="risks",
        verbose_name="Biens essentiels affectés",
    )
    affected_support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="risks",
        verbose_name="Biens supports affectés",
    )
    impact_confidentiality = models.BooleanField(
        "Impact confidentialité", default=False
    )
    impact_integrity = models.BooleanField("Impact intégrité", default=False)
    impact_availability = models.BooleanField(
        "Impact disponibilité", default=False
    )
    # Initial risk levels
    initial_likelihood = models.PositiveIntegerField(
        "Vraisemblance initiale", null=True, blank=True
    )
    initial_impact = models.PositiveIntegerField(
        "Impact initial", null=True, blank=True
    )
    initial_risk_level = models.PositiveIntegerField(
        "Niveau de risque initial", null=True, blank=True
    )
    # Current risk levels
    current_likelihood = models.PositiveIntegerField(
        "Vraisemblance actuelle", null=True, blank=True
    )
    current_impact = models.PositiveIntegerField(
        "Impact actuel", null=True, blank=True
    )
    current_risk_level = models.PositiveIntegerField(
        "Niveau de risque réel", null=True, blank=True
    )
    # Residual risk levels
    residual_likelihood = models.PositiveIntegerField(
        "Vraisemblance résiduelle", null=True, blank=True
    )
    residual_impact = models.PositiveIntegerField(
        "Impact résiduel", null=True, blank=True
    )
    residual_risk_level = models.PositiveIntegerField(
        "Niveau de risque résiduel", null=True, blank=True
    )
    treatment_decision = models.CharField(
        "Décision de traitement",
        max_length=20,
        choices=TreatmentDecision.choices,
        default=TreatmentDecision.NOT_DECIDED,
    )
    treatment_justification = models.TextField(
        "Justification du traitement", blank=True
    )
    risk_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_risks",
        verbose_name="Propriétaire du risque",
    )
    priority = models.CharField(
        "Priorité",
        max_length=20,
        choices=RiskPriority.choices,
        default=RiskPriority.LOW,
    )
    status = models.CharField(
        "Statut",
        max_length=30,
        choices=RiskStatus.choices,
        default=RiskStatus.IDENTIFIED,
    )
    review_date = models.DateField("Date de revue", null=True, blank=True)
    # FK vers modules non implémentés
    # linked_measures = ...
    # linked_requirements = ...
    # linked_incidents = ...
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Risque"
        verbose_name_plural = "Risques"

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def _get_valid_levels(self):
        """Return (likelihood_levels, impact_levels) sets from criteria or defaults."""
        from risks.models.risk_criteria import RiskCriteria

        criteria = None
        if self.assessment_id:
            criteria = getattr(self.assessment, "risk_criteria", None)
        if not criteria:
            criteria = (
                RiskCriteria.objects.filter(is_default=True).first()
                or RiskCriteria.objects.filter(status="active").first()
            )
        if criteria:
            l_levels = set(
                criteria.scale_levels.filter(scale_type="likelihood")
                .values_list("level", flat=True)
            )
            i_levels = set(
                criteria.scale_levels.filter(scale_type="impact")
                .values_list("level", flat=True)
            )
            if l_levels and i_levels:
                return l_levels, i_levels
        return (
            {level for level, _ in DEFAULT_LIKELIHOOD_SCALES},
            {level for level, _ in DEFAULT_IMPACT_SCALES},
        )

    def clean(self):
        super().clean()
        l_levels, i_levels = self._get_valid_levels()
        errors = {}
        for fname in ("initial_likelihood", "current_likelihood", "residual_likelihood"):
            val = getattr(self, fname)
            if val is not None and val not in l_levels:
                errors[fname] = (
                    f"La valeur doit être parmi {sorted(l_levels)}."
                )
        for fname in ("initial_impact", "current_impact", "residual_impact"):
            val = getattr(self, fname)
            if val is not None and val not in i_levels:
                errors[fname] = (
                    f"La valeur doit être parmi {sorted(i_levels)}."
                )
        if errors:
            raise ValidationError(errors)

    def calculate_risk_level(self, likelihood, impact):
        """Calculate risk level using the assessment's criteria matrix."""
        if likelihood is None or impact is None:
            return None
        criteria = getattr(self.assessment, "risk_criteria", None)
        if criteria and criteria.risk_matrix:
            matrix = criteria.risk_matrix
            key = f"{likelihood},{impact}"
            level = matrix.get(key)
            if level is not None:
                return int(level)
        return None

    def save(self, *args, **kwargs):
        if self.initial_likelihood is not None and self.initial_impact is not None:
            calculated = self.calculate_risk_level(
                self.initial_likelihood, self.initial_impact
            )
            if calculated is not None:
                self.initial_risk_level = calculated
        if self.current_likelihood is not None and self.current_impact is not None:
            calculated = self.calculate_risk_level(
                self.current_likelihood, self.current_impact
            )
            if calculated is not None:
                self.current_risk_level = calculated
        if self.residual_likelihood is not None and self.residual_impact is not None:
            calculated = self.calculate_risk_level(
                self.residual_likelihood, self.residual_impact
            )
            if calculated is not None:
                self.residual_risk_level = calculated
        super().save(*args, **kwargs)
