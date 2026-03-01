from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import FrameworkCategory, FrameworkStatus, FrameworkType
from context.models.base import BaseModel


class Framework(BaseModel):
    REFERENCE_PREFIX = "FWK"

    scopes = models.ManyToManyField(
        "context.Scope",
        related_name="frameworks",
        verbose_name=_("Scopes"),
    )
    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    short_name = models.CharField(_("Abbreviation"), max_length=50, blank=True, default="")
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(_("Type"), max_length=30, choices=FrameworkType.choices)
    category = models.CharField(
        _("Category"), max_length=30, choices=FrameworkCategory.choices
    )
    framework_version = models.CharField(
        _("Framework version"), max_length=50, blank=True, default=""
    )
    publication_date = models.DateField(_("Publication date"), null=True, blank=True)
    effective_date = models.DateField(_("Effective date"), null=True, blank=True)
    expiry_date = models.DateField(_("Expiry date"), null=True, blank=True)
    issuing_body = models.CharField(
        _("Issuing body"), max_length=255, blank=True, default=""
    )
    jurisdiction = models.CharField(
        _("Jurisdiction"), max_length=255, blank=True, default=""
    )
    url = models.URLField(_("Official link"), max_length=500, blank=True, default="")
    is_mandatory = models.BooleanField(_("Mandatory"), default=False)
    is_applicable = models.BooleanField(_("Applicable"), default=True)
    applicability_justification = models.TextField(
        _("Applicability justification"), blank=True, default=""
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_frameworks",
        verbose_name=_("Owner"),
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_frameworks",
        verbose_name=_("Interested parties"),
    )
    compliance_level = models.DecimalField(
        _("Compliance level (%)"),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    last_assessment_date = models.DateField(
        _("Last assessment"), null=True, blank=True
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=FrameworkStatus.choices,
        default=FrameworkStatus.DRAFT,
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Framework")
        verbose_name_plural = _("Frameworks")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def recalculate_compliance(self):
        """RC-01: compliance level = average of applicable requirements."""
        from compliance.constants import ComplianceStatus

        reqs = self.requirements.filter(
            is_applicable=True
        ).exclude(
            compliance_status=ComplianceStatus.NOT_APPLICABLE
        )
        if not reqs.exists():
            self.compliance_level = 0
        else:
            total = sum(r.compliance_level or 0 for r in reqs)
            self.compliance_level = total / reqs.count()
        Framework.objects.filter(pk=self.pk).update(
            compliance_level=self.compliance_level
        )
