from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.constants import (
    SupplierCriticality,
    SupplierRequirementStatus,
    SupplierStatus,
    SupplierType,
)
from context.models.base import ScopedModel


class Supplier(ScopedModel):
    REFERENCE_PREFIX = "SUPP"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(
        _("Type"), max_length=30, choices=SupplierType.choices
    )
    criticality = models.CharField(
        _("Criticality"),
        max_length=20,
        choices=SupplierCriticality.choices,
        default=SupplierCriticality.MEDIUM,
    )
    contact_name = models.CharField(
        _("Contact name"), max_length=255, blank=True, default=""
    )
    contact_email = models.EmailField(
        _("Contact email"), blank=True, default=""
    )
    contact_phone = models.CharField(
        _("Contact phone"), max_length=50, blank=True, default=""
    )
    website = models.URLField(_("Website"), blank=True, default="")
    address = models.TextField(_("Address"), blank=True, default="")
    country = models.CharField(
        _("Country"), max_length=100, blank=True, default=""
    )
    contract_reference = models.CharField(
        _("Contract reference"), max_length=255, blank=True, default=""
    )
    contract_start_date = models.DateField(
        _("Contract start date"), null=True, blank=True
    )
    contract_end_date = models.DateField(
        _("Contract end date"), null=True, blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_suppliers",
        verbose_name=_("Owner"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=SupplierStatus.choices,
        default=SupplierStatus.ACTIVE,
    )
    notes = models.TextField(_("Notes"), blank=True, default="")

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    @property
    def is_contract_expired(self):
        from django.utils import timezone

        if self.contract_end_date and self.status == SupplierStatus.ACTIVE:
            return self.contract_end_date <= timezone.now().date()
        return False

    @property
    def requirement_compliance_summary(self):
        """Return a dict with counts per compliance status."""
        reqs = self.requirements.all()
        total = reqs.count()
        if total == 0:
            return {"total": 0, "compliant": 0, "non_compliant": 0, "partially_compliant": 0, "not_assessed": 0}
        return {
            "total": total,
            "compliant": reqs.filter(compliance_status=SupplierRequirementStatus.COMPLIANT).count(),
            "non_compliant": reqs.filter(compliance_status=SupplierRequirementStatus.NON_COMPLIANT).count(),
            "partially_compliant": reqs.filter(compliance_status=SupplierRequirementStatus.PARTIALLY_COMPLIANT).count(),
            "not_assessed": reqs.filter(compliance_status=SupplierRequirementStatus.NOT_ASSESSED).count(),
        }


class SupplierRequirement(models.Model):
    """A requirement applied to a supplier (e.g. must be ISO 27001 certified)."""

    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="requirements",
        verbose_name=_("Supplier"),
    )
    requirement = models.ForeignKey(
        "compliance.Requirement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_requirements",
        verbose_name=_("Linked requirement"),
    )
    title = models.CharField(
        _("Title"),
        max_length=500,
        help_text=_("Custom title when not linked to a compliance requirement."),
    )
    description = models.TextField(_("Description"), blank=True, default="")
    compliance_status = models.CharField(
        _("Compliance status"),
        max_length=25,
        choices=SupplierRequirementStatus.choices,
        default=SupplierRequirementStatus.NOT_ASSESSED,
    )
    evidence = models.TextField(_("Evidence"), blank=True, default="")
    due_date = models.DateField(_("Due date"), null=True, blank=True)
    verified_at = models.DateTimeField(_("Verified at"), null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_supplier_requirements",
        verbose_name=_("Verified by"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Supplier requirement")
        verbose_name_plural = _("Supplier requirements")

    def __str__(self):
        return self.title
