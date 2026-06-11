from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel
from risks.constants import EbiosBaselineStatus


class SecurityBaseline(BaseModel):
    """EBIOS RM Workshop 1 - Security baseline.

    Root of the W1 deliverables: business values, support assets, DIC summary
    and baseline references. Exactly one instance per ebios_rm RiskAssessment.
    """

    WORKFLOW_NAME = "ebios_security_baseline"

    REFERENCE_PREFIX = "EBSL"

    assessment = models.OneToOneField(
        "risks.RiskAssessment",
        on_delete=models.CASCADE,
        related_name="ebios_security_baseline",
        verbose_name=_("Assessment"),
    )
    business_values = models.ManyToManyField(
        "context.Activity",
        blank=True,
        related_name="ebios_security_baselines",
        verbose_name=_("Business values (activities)"),
    )
    essential_assets = models.ManyToManyField(
        "assets.EssentialAsset",
        blank=True,
        related_name="ebios_security_baselines",
        verbose_name=_("Essential assets"),
    )
    support_assets = models.ManyToManyField(
        "assets.SupportAsset",
        blank=True,
        related_name="ebios_security_baselines",
        verbose_name=_("Support assets"),
    )
    dic_summary = models.TextField(_("DIC needs summary"), blank=True)
    baseline_references = models.ManyToManyField(
        "compliance.Framework",
        blank=True,
        related_name="ebios_security_baselines",
        verbose_name=_("Baseline references"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=EbiosBaselineStatus.choices,
        default=EbiosBaselineStatus.DRAFT,
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("EBIOS RM security baseline")
        verbose_name_plural = _("EBIOS RM security baselines")

    @property
    def workflow_perm_namespace(self):
        return "risks.ebios_baseline"

    def save(self, *args, **kwargs):
        from core.workflow import sync_legacy_status

        sync_legacy_status(self, kwargs, EbiosBaselineStatus.DRAFT)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} : {self.assessment.name}"
