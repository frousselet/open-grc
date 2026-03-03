from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
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
    REFERENCE_PREFIX = "REQT"

    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.CASCADE,
        related_name="requirements",
        verbose_name=_("Framework"),
    )
    section = models.ForeignKey(
        "compliance.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requirements",
        verbose_name=_("Section"),
    )
    requirement_number = models.CharField(
        _("Requirement number"), max_length=100, blank=True, default=""
    )
    name = models.CharField(_("Title"), max_length=500)
    description = models.TextField(_("Description"))
    guidance = models.TextField(
        _("Implementation guidance"), blank=True, default=""
    )
    type = models.CharField(
        _("Type"), max_length=20, choices=RequirementType.choices
    )
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=RequirementCategory.choices,
        blank=True,
        default="",
    )
    is_applicable = models.BooleanField(_("Applicable"), default=True)
    applicability_justification = models.TextField(
        _("Applicability justification"), blank=True, default=""
    )
    compliance_status = models.CharField(
        _("Compliance status"),
        max_length=25,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_ASSESSED,
    )
    compliance_level = models.PositiveIntegerField(
        _("Compliance level (%)"), default=0
    )
    compliance_evidence = models.TextField(_("Compliance evidence"), blank=True, default="")
    compliance_gaps = models.TextField(_("Identified gaps"), blank=True, default="")
    last_assessment_date = models.DateField(
        _("Last assessment"), null=True, blank=True
    )
    last_assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessed_requirements",
        verbose_name=_("Last assessor"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_requirements",
        verbose_name=_("Owner"),
    )
    priority = models.CharField(
        _("Priority"),
        max_length=20,
        choices=Priority.choices,
        blank=True,
        default="",
    )
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    # M2M relations (some to modules not yet implemented — commented out)
    # linked_measures = models.ManyToManyField("measures.Measure", blank=True)
    linked_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="linked_requirements",
        verbose_name=_("Linked essential assets"),
    )
    # linked_risks = models.ManyToManyField("risks.Risk", blank=True)
    linked_stakeholder_expectations = models.ManyToManyField(
        "context.StakeholderExpectation",
        blank=True,
        related_name="linked_requirements",
        verbose_name=_("Linked stakeholder expectations"),
    )
    order = models.PositiveIntegerField(_("Order"), default=0)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=RequirementStatus.choices,
        default=RequirementStatus.ACTIVE,
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Requirement")
        verbose_name_plural = _("Requirements")
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "requirement_number"],
                name="unique_requirement_number_per_framework",
                condition=~models.Q(requirement_number=""),
            )
        ]

    def __str__(self):
        if self.requirement_number:
            return f"{self.requirement_number} : {self.name}"
        return f"{self.reference} : {self.name}"
