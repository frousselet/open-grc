import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import (
    ExpectationType,
    InfluenceLevel,
    IssueType,
    Priority,
    StakeholderCategory,
    StakeholderStatus,
)
from .base import ScopedModel


class Stakeholder(ScopedModel):
    REFERENCE_PREFIX = "STKH"

    name = models.CharField(_("Name"), max_length=255)
    type = models.CharField(
        _("Type"), max_length=20, choices=IssueType.choices
    )
    category = models.CharField(
        _("Category"), max_length=30, choices=StakeholderCategory.choices
    )
    description = models.TextField(_("Description"), blank=True, default="")
    contact_name = models.CharField(
        _("Contact name"), max_length=255, blank=True, default=""
    )
    contact_email = models.EmailField(_("Contact email"), blank=True, default="")
    contact_phone = models.CharField(
        _("Contact phone"), max_length=50, blank=True, default=""
    )
    influence_level = models.CharField(
        _("Influence level"), max_length=20, choices=InfluenceLevel.choices
    )
    interest_level = models.CharField(
        _("Interest level"), max_length=20, choices=InfluenceLevel.choices
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=StakeholderStatus.choices,
        default=StakeholderStatus.ACTIVE,
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Stakeholder")
        verbose_name_plural = _("Stakeholders")

    def __str__(self):
        return f"{self.reference} : {self.name}"


class StakeholderExpectation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stakeholder = models.ForeignKey(
        Stakeholder,
        on_delete=models.CASCADE,
        related_name="expectations",
        verbose_name=_("Stakeholder"),
    )
    description = models.TextField(_("Description"))
    type = models.CharField(_("Type"), max_length=20, choices=ExpectationType.choices)
    priority = models.CharField(_("Priority"), max_length=20, choices=Priority.choices)
    is_applicable = models.BooleanField(_("Applicable"), default=True)
    # M2M to Requirement omitted — module not yet implemented
    # linked_requirements = models.ManyToManyField("compliance.Requirement", ...)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Expectation")
        verbose_name_plural = _("Expectations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.stakeholder.name} — {self.get_type_display()}"
