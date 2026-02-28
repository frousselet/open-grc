from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from compliance.constants import FrameworkCategory, FrameworkStatus, FrameworkType
from context.models.base import BaseModel


class Framework(BaseModel):
    scopes = models.ManyToManyField(
        "context.Scope",
        related_name="frameworks",
        verbose_name="Périmètres",
    )
    reference = models.CharField("Référence", max_length=50, unique=True)
    name = models.CharField("Nom", max_length=255)
    short_name = models.CharField("Abréviation", max_length=50, blank=True, default="")
    description = models.TextField("Description", blank=True, default="")
    type = models.CharField("Type", max_length=30, choices=FrameworkType.choices)
    category = models.CharField(
        "Catégorie", max_length=30, choices=FrameworkCategory.choices
    )
    framework_version = models.CharField(
        "Version du référentiel", max_length=50, blank=True, default=""
    )
    publication_date = models.DateField("Date de publication", null=True, blank=True)
    effective_date = models.DateField("Date d'entrée en vigueur", null=True, blank=True)
    expiry_date = models.DateField("Date d'expiration", null=True, blank=True)
    issuing_body = models.CharField(
        "Organisme émetteur", max_length=255, blank=True, default=""
    )
    jurisdiction = models.CharField(
        "Juridiction", max_length=255, blank=True, default=""
    )
    url = models.URLField("Lien officiel", max_length=500, blank=True, default="")
    is_mandatory = models.BooleanField("Obligatoire", default=False)
    is_applicable = models.BooleanField("Applicable", default=True)
    applicability_justification = models.TextField(
        "Justification d'applicabilité", blank=True, default=""
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_frameworks",
        verbose_name="Responsable",
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_frameworks",
        verbose_name="Parties intéressées",
    )
    compliance_level = models.DecimalField(
        "Niveau de conformité (%)",
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    last_assessment_date = models.DateField(
        "Dernière évaluation", null=True, blank=True
    )
    status = models.CharField(
        "Statut",
        max_length=20,
        choices=FrameworkStatus.choices,
        default=FrameworkStatus.DRAFT,
    )
    review_date = models.DateField("Prochaine date de revue", null=True, blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = "Référentiel"
        verbose_name_plural = "Référentiels"

    def __str__(self):
        return f"{self.reference} — {self.name}"

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
