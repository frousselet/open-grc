from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from compliance.constants import (
    ComplianceStatus,
    Priority,
    RequirementCategory,
    RequirementStatus,
    RequirementType,
)
from context.models.base import BaseModel


class Requirement(BaseModel):
    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.CASCADE,
        related_name="requirements",
        verbose_name="Référentiel",
    )
    section = models.ForeignKey(
        "compliance.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requirements",
        verbose_name="Section",
    )
    reference = models.CharField("Référence", max_length=100)
    name = models.CharField("Intitulé", max_length=500)
    description = models.TextField("Description")
    guidance = models.TextField(
        "Recommandations de mise en œuvre", blank=True, default=""
    )
    type = models.CharField(
        "Type", max_length=20, choices=RequirementType.choices
    )
    category = models.CharField(
        "Catégorie",
        max_length=20,
        choices=RequirementCategory.choices,
        blank=True,
        default="",
    )
    is_applicable = models.BooleanField("Applicable", default=True)
    applicability_justification = models.TextField(
        "Justification d'applicabilité", blank=True, default=""
    )
    compliance_status = models.CharField(
        "Statut de conformité",
        max_length=25,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_ASSESSED,
    )
    compliance_level = models.PositiveIntegerField(
        "Niveau de conformité (%)", default=0
    )
    compliance_evidence = models.TextField("Preuves de conformité", blank=True, default="")
    compliance_gaps = models.TextField("Écarts constatés", blank=True, default="")
    last_assessment_date = models.DateField(
        "Dernière évaluation", null=True, blank=True
    )
    last_assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessed_requirements",
        verbose_name="Dernier évaluateur",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_requirements",
        verbose_name="Responsable",
    )
    priority = models.CharField(
        "Priorité",
        max_length=20,
        choices=Priority.choices,
        blank=True,
        default="",
    )
    target_date = models.DateField("Date cible", null=True, blank=True)
    # M2M relations (some to modules not yet implemented — commented out)
    # linked_measures = models.ManyToManyField("measures.Measure", blank=True)
    linked_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="linked_requirements",
        verbose_name="Biens essentiels liés",
    )
    # linked_risks = models.ManyToManyField("risks.Risk", blank=True)
    linked_stakeholder_expectations = models.ManyToManyField(
        "context.StakeholderExpectation",
        blank=True,
        related_name="linked_requirements",
        verbose_name="Attentes de PI liées",
    )
    order = models.PositiveIntegerField("Ordre", default=0)
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=RequirementStatus.choices,
        default=RequirementStatus.ACTIVE,
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = "Exigence"
        verbose_name_plural = "Exigences"
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "reference"],
                name="unique_requirement_reference_per_framework",
            )
        ]

    def __str__(self):
        return f"{self.reference} — {self.name}"
