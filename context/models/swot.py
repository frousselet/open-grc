import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import ImpactLevel, SwotQuadrant, SwotStatus
from .base import ScopedModel


class SwotAnalysis(ScopedModel):
    REFERENCE_PREFIX = "SWOT"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    analysis_date = models.DateField(_("Analysis date"))
    status = models.CharField(
        _("Status"), max_length=20, choices=SwotStatus.choices, default=SwotStatus.DRAFT
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_swot_analyses",
        verbose_name=_("Validated by"),
    )
    validated_at = models.DateTimeField(_("Validation date"), null=True, blank=True)
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("SWOT analysis")
        verbose_name_plural = _("SWOT analyses")

    def __str__(self):
        return f"{self.reference} — {self.name}"


class SwotItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    swot_analysis = models.ForeignKey(
        SwotAnalysis,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("SWOT analysis"),
    )
    quadrant = models.CharField(
        _("Quadrant"), max_length=20, choices=SwotQuadrant.choices
    )
    description = models.TextField(_("Description"))
    impact_level = models.CharField(
        _("Impact level"),
        max_length=20,
        choices=[
            (ImpactLevel.LOW, ImpactLevel.LOW.label),
            (ImpactLevel.MEDIUM, ImpactLevel.MEDIUM.label),
            (ImpactLevel.HIGH, ImpactLevel.HIGH.label),
        ],
    )
    related_issues = models.ManyToManyField(
        "context.Issue",
        blank=True,
        related_name="swot_items",
        verbose_name=_("Related issues"),
    )
    related_objectives = models.ManyToManyField(
        "context.Objective",
        blank=True,
        related_name="swot_items",
        verbose_name=_("Related objectives"),
    )
    order = models.IntegerField(_("Order"), default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("SWOT item")
        verbose_name_plural = _("SWOT items")
        ordering = ["quadrant", "order"]

    def __str__(self):
        return f"{self.get_quadrant_display()} — {self.description[:50]}"
