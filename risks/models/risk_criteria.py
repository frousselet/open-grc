import math
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import ScopedModel
from risks.constants import CriteriaStatus, ScaleType


class RiskCriteria(ScopedModel):
    REFERENCE_PREFIX = "RC"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    risk_matrix = models.JSONField(_("Risk matrix"), default=dict)
    acceptance_threshold = models.PositiveIntegerField(
        _("Acceptance threshold"), default=0
    )
    is_default = models.BooleanField(_("Default"), default=False)
    status = models.CharField(
        _("Status"), max_length=20, choices=CriteriaStatus.choices, default=CriteriaStatus.DRAFT
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]
        verbose_name = _("Risk criteria")
        verbose_name_plural = _("Risk criteria")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def rebuild_risk_matrix(self):
        """Recompute risk_matrix JSON from current scales and risk levels.

        Uses a symmetric formula: score = L + I - 1, mapped linearly to the
        available risk levels so that cell (L, I) always equals cell (I, L)
        when scales are identical.
        """
        l_levels = list(
            self.scale_levels.filter(scale_type="likelihood")
            .order_by("level")
            .values_list("level", flat=True)
        )
        i_levels = list(
            self.scale_levels.filter(scale_type="impact")
            .order_by("level")
            .values_list("level", flat=True)
        )
        r_levels = list(
            self.risk_levels.order_by("level")
            .values_list("level", flat=True)
        )
        if not l_levels or not i_levels or not r_levels:
            self.risk_matrix = {}
            self.save(update_fields=["risk_matrix"])
            return

        max_score = max(l_levels) + max(i_levels) - 1
        num_r = len(r_levels)
        matrix = {}
        for l_val in l_levels:
            for i_val in i_levels:
                score = l_val + i_val - 1
                idx = math.ceil(score * num_r / max_score) - 1
                idx = max(0, min(idx, num_r - 1))
                matrix[f"{l_val},{i_val}"] = r_levels[idx]

        self.risk_matrix = matrix
        self.save(update_fields=["risk_matrix"])


class ScaleLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criteria = models.ForeignKey(
        RiskCriteria,
        on_delete=models.CASCADE,
        related_name="scale_levels",
        verbose_name=_("Criteria"),
    )
    scale_type = models.CharField(
        _("Scale type"), max_length=20, choices=ScaleType.choices
    )
    level = models.PositiveIntegerField(_("Level"))
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    color = models.CharField(_("Color"), max_length=7, blank=True)

    class Meta:
        ordering = ["scale_type", "level"]
        unique_together = [("criteria", "scale_type", "level")]
        verbose_name = _("Scale level")
        verbose_name_plural = _("Scale levels")

    def __str__(self):
        return f"{self.get_scale_type_display()} — {self.level}. {self.name}"


class RiskLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criteria = models.ForeignKey(
        RiskCriteria,
        on_delete=models.CASCADE,
        related_name="risk_levels",
        verbose_name=_("Criteria"),
    )
    level = models.PositiveIntegerField(_("Level"))
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    color = models.CharField(_("Color"), max_length=7, blank=True)
    requires_treatment = models.BooleanField(_("Requires treatment"), default=False)

    class Meta:
        ordering = ["level"]
        unique_together = [("criteria", "level")]
        verbose_name = _("Risk level")
        verbose_name_plural = _("Risk levels")

    def __str__(self):
        return f"{self.level}. {self.name}"
