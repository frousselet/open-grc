import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import DICLevel


class AssetValuation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    essential_asset = models.ForeignKey(
        "assets.EssentialAsset",
        on_delete=models.CASCADE,
        related_name="valuations",
        verbose_name=_("Essential asset"),
    )
    evaluation_date = models.DateField(_("Evaluation date"))
    confidentiality_level = models.IntegerField(
        _("Confidentiality"), choices=DICLevel.choices
    )
    integrity_level = models.IntegerField(
        _("Integrity"), choices=DICLevel.choices
    )
    availability_level = models.IntegerField(
        _("Availability"), choices=DICLevel.choices
    )
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asset_valuations",
        verbose_name=_("Evaluator"),
    )
    justification = models.TextField(_("Justification"), blank=True, default="")
    context = models.TextField(_("Context"), blank=True, default="")
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("DIC valuation")
        verbose_name_plural = _("DIC valuations")
        ordering = ["-evaluation_date", "-created_at"]

    def __str__(self):
        return f"{self.essential_asset.reference} — {self.evaluation_date}"
