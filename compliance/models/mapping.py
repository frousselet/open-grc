import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import CoverageLevel, MappingType


class RequirementMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.CASCADE,
        related_name="mappings_as_source",
        verbose_name=_("Source requirement"),
    )
    target_requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.CASCADE,
        related_name="mappings_as_target",
        verbose_name=_("Target requirement"),
    )
    mapping_type = models.CharField(
        _("Mapping type"), max_length=20, choices=MappingType.choices
    )
    coverage_level = models.CharField(
        _("Coverage level"),
        max_length=10,
        choices=CoverageLevel.choices,
        blank=True,
        default="",
    )
    description = models.TextField(_("Description"), blank=True, default="")
    justification = models.TextField(_("Justification"), blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mappings",
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Cross-framework mapping")
        verbose_name_plural = _("Cross-framework mappings")
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
                _("A mapping can only exist between requirements from different frameworks.")
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
