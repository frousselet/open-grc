from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import (
    MeasurementFrequency,
    ObjectiveCategory,
    ObjectiveStatus,
    ObjectiveType,
)
from .base import ScopedModel


class Objective(ScopedModel):
    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    category = models.CharField(
        _("Category"), max_length=20, choices=ObjectiveCategory.choices
    )
    type = models.CharField(_("Type"), max_length=20, choices=ObjectiveType.choices)
    target_value = models.CharField(_("Target value"), max_length=255, blank=True, default="")
    current_value = models.CharField(
        _("Current value"), max_length=255, blank=True, default=""
    )
    unit = models.CharField(_("Unit of measure"), max_length=50, blank=True, default="")
    measurement_method = models.TextField(
        _("Measurement method"), blank=True, default=""
    )
    measurement_frequency = models.CharField(
        _("Measurement frequency"),
        max_length=20,
        choices=MeasurementFrequency.choices,
        blank=True,
        default="",
    )
    target_date = models.DateField(_("Target date"), null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_objectives",
        verbose_name=_("Owner"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ObjectiveStatus.choices,
        default=ObjectiveStatus.DRAFT,
    )
    progress_percentage = models.IntegerField(
        _("Progress (%)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    related_issues = models.ManyToManyField(
        "context.Issue",
        blank=True,
        related_name="related_objectives",
        verbose_name=_("Addressed issues"),
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_objectives",
        verbose_name=_("Stakeholders"),
    )
    parent_objective = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent objective"),
    )
    # M2M to Measure omitted — module not yet implemented
    # linked_measures = models.ManyToManyField("measures.Measure", ...)
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Objective")
        verbose_name_plural = _("Objectives")

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        # RS-02: achieved -> 100%
        if self.status == ObjectiveStatus.ACHIEVED and self.progress_percentage != 100:
            raise ValidationError(
                {
                    "progress_percentage": _(
                        "An achieved objective must have 100% progress."
                    )
                }
            )
        # RS-03: same scope as parent
        if self.parent_objective_id and self.parent_objective.scope_id != self.scope_id:
            raise ValidationError(
                {
                    "parent_objective": _(
                        "The child objective must belong to the same scope as its parent."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
