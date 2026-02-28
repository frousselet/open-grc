import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from compliance.constants import CoverageLevel, MappingType


class RequirementMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.CASCADE,
        related_name="mappings_as_source",
        verbose_name="Exigence source",
    )
    target_requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.CASCADE,
        related_name="mappings_as_target",
        verbose_name="Exigence cible",
    )
    mapping_type = models.CharField(
        "Type de mapping", max_length=20, choices=MappingType.choices
    )
    coverage_level = models.CharField(
        "Niveau de couverture",
        max_length=10,
        choices=CoverageLevel.choices,
        blank=True,
        default="",
    )
    description = models.TextField("Description", blank=True, default="")
    justification = models.TextField("Justification", blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mappings",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Mapping inter-référentiels"
        verbose_name_plural = "Mappings inter-référentiels"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_requirement", "target_requirement"],
                name="unique_requirement_mapping",
            )
        ]

    def __str__(self):
        return f"{self.source_requirement.reference} → {self.target_requirement.reference}"

    def clean(self):
        super().clean()
        # RM-01: mapping only between different frameworks
        if (
            self.source_requirement_id
            and self.target_requirement_id
            and self.source_requirement.framework_id == self.target_requirement.framework_id
        ):
            raise ValidationError(
                "Un mapping ne peut exister qu'entre des exigences de référentiels différents."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
