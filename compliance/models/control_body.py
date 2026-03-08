from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.models.base import BaseModel


class ControlBody(BaseModel):
    REFERENCE_PREFIX = "CBDY"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")

    is_accredited = models.BooleanField(_("Accredited"), default=False)
    accreditation_details = models.TextField(
        _("Accreditation details"), blank=True, default=""
    )

    # Contact
    contact_name = models.CharField(_("Contact name"), max_length=255, blank=True, default="")
    contact_email = models.EmailField(_("Contact email"), blank=True, default="")
    contact_phone = models.CharField(_("Contact phone"), max_length=50, blank=True, default="")
    website = models.URLField(_("Website"), blank=True, default="")
    address = models.TextField(_("Address"), blank=True, default="")
    country = models.CharField(_("Country"), max_length=100, blank=True, default="")

    # Linked frameworks (standards they are associated with)
    frameworks = models.ManyToManyField(
        "compliance.Framework",
        blank=True,
        related_name="control_bodies",
        verbose_name=_("Frameworks"),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Control body / authority")
        verbose_name_plural = _("Control bodies & authorities")

    def __str__(self):
        return f"{self.reference} : {self.name}"


class Auditor(BaseModel):
    REFERENCE_PREFIX = "AUDR"

    first_name = models.CharField(_("First name"), max_length=100)
    last_name = models.CharField(_("Last name"), max_length=100)
    email = models.EmailField(_("Email"), blank=True, default="")
    phone = models.CharField(_("Phone"), max_length=50, blank=True, default="")

    control_body = models.ForeignKey(
        ControlBody,
        on_delete=models.CASCADE,
        related_name="auditors",
        verbose_name=_("Control body"),
    )

    certifications = models.TextField(_("Certifications"), blank=True, default="")
    cv = models.FileField(_("CV"), upload_to="auditors/cv/", blank=True, null=True)
    specializations = models.TextField(_("Specializations"), blank=True, default="")

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Auditor")
        verbose_name_plural = _("Auditors")

    def __str__(self):
        return f"{self.reference} : {self.first_name} {self.last_name}"
