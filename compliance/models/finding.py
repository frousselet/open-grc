from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import (
    FindingType,
    FINDING_REFERENCE_PREFIXES,
)
from context.models.base import BaseModel


class Finding(BaseModel):
    """Audit finding (constat) linked to a compliance assessment.

    Reference is auto-generated from the finding type:
    NCMAJ-1, NCMIN-1, OBS-1, OA-1, STR-1, etc.
    """

    assessment = models.ForeignKey(
        "compliance.ComplianceAssessment",
        on_delete=models.CASCADE,
        related_name="findings",
        verbose_name=_("Assessment"),
    )
    finding_type = models.CharField(
        _("Finding type"),
        max_length=20,
        choices=FindingType.choices,
    )
    description = models.TextField(_("Finding"))
    recommendation = models.TextField(
        _("Auditor recommendation"), blank=True, default=""
    )
    evidence = models.TextField(
        _("Evidence presented"), blank=True, default=""
    )
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="findings",
        verbose_name=_("Assessor"),
    )
    requirements = models.ManyToManyField(
        "compliance.Requirement",
        blank=True,
        related_name="findings",
        verbose_name=_("Related requirements"),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Finding")
        verbose_name_plural = _("Findings")
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} — {self.get_finding_type_display()}"

    @classmethod
    def _generate_reference_for_type(cls, finding_type):
        """Generate the next unique reference for the given finding type."""
        prefix = FINDING_REFERENCE_PREFIXES.get(finding_type, "FIND")
        prefix_with_dash = f"{prefix}-"
        existing_refs = cls.objects.filter(
            reference__startswith=prefix_with_dash
        ).values_list("reference", flat=True)
        max_num = 0
        prefix_len = len(prefix_with_dash)
        for ref in existing_refs:
            try:
                num = int(ref[prefix_len:])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"{prefix}-{max_num + 1}"

    def save(self, *args, **kwargs):
        if not self.reference and self.finding_type:
            self.reference = self._generate_reference_for_type(self.finding_type)
        # Skip ReferenceGeneratorMixin.save() which requires 4-char REFERENCE_PREFIX
        models.Model.save(self, *args, **kwargs)
