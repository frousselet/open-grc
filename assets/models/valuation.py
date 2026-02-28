import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from assets.constants import DICLevel


class AssetValuation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    essential_asset = models.ForeignKey(
        "assets.EssentialAsset",
        on_delete=models.CASCADE,
        related_name="valuations",
        verbose_name="Bien essentiel",
    )
    evaluation_date = models.DateField("Date d'évaluation")
    confidentiality_level = models.IntegerField(
        "Confidentialité", choices=DICLevel.choices
    )
    integrity_level = models.IntegerField(
        "Intégrité", choices=DICLevel.choices
    )
    availability_level = models.IntegerField(
        "Disponibilité", choices=DICLevel.choices
    )
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asset_valuations",
        verbose_name="Évaluateur",
    )
    justification = models.TextField("Justification", blank=True, default="")
    context = models.TextField("Contexte", blank=True, default="")
    created_at = models.DateTimeField("Date de création", auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Valorisation DIC"
        verbose_name_plural = "Valorisations DIC"
        ordering = ["-evaluation_date", "-created_at"]

    def __str__(self):
        return f"{self.essential_asset.reference} — {self.evaluation_date}"
