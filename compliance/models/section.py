import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    framework = models.ForeignKey(
        "compliance.Framework",
        on_delete=models.CASCADE,
        related_name="sections",
        verbose_name=_("Framework"),
    )
    parent_section = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent section"),
    )
    reference = models.CharField(_("Reference"), max_length=50)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    order = models.PositiveIntegerField(_("Order"), default=0)
    compliance_level = models.DecimalField(
        _("Compliance level (%)"),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Section")
        verbose_name_plural = _("Sections")
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "reference"],
                name="unique_section_reference_per_framework",
            )
        ]

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def recalculate_compliance(self):
        """RC-02: section compliance = average of applicable requirements + subsections."""
        from compliance.constants import ComplianceStatus

        reqs = self.requirements.filter(
            is_applicable=True
        ).exclude(
            compliance_status=ComplianceStatus.NOT_APPLICABLE
        )
        levels = [r.compliance_level or 0 for r in reqs]

        for child in self.children.all():
            child.recalculate_compliance()
            levels.append(float(child.compliance_level))

        if levels:
            self.compliance_level = sum(levels) / len(levels)
        else:
            self.compliance_level = 0
        Section.objects.filter(pk=self.pk).update(
            compliance_level=self.compliance_level
        )
