import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class CompanySettings(models.Model):
    """Singleton model storing company-wide settings (name, address, logo)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Company name"), max_length=255, blank=True, default="")
    address = models.TextField(_("Address"), blank=True, default="")
    logo = models.TextField(_("Logo"), blank=True, default="")
    logo_32 = models.TextField(_("Logo 32×32"), blank=True, default="")
    logo_64 = models.TextField(_("Logo 64×64"), blank=True, default="")
    logo_128 = models.TextField(_("Logo 128×128"), blank=True, default="")
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Company settings")
        verbose_name_plural = _("Company settings")

    def __str__(self):
        return self.name or str(_("Company settings"))

    def save(self, *args, **kwargs):
        # Enforce singleton: always use the same PK
        if not CompanySettings.objects.exists():
            super().save(*args, **kwargs)
        else:
            existing = CompanySettings.objects.first()
            self.pk = existing.pk
            super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Return the singleton instance, creating it if necessary."""
        obj, _ = cls.objects.get_or_create(
            pk=cls.objects.values_list("pk", flat=True).first()
            or uuid.uuid4()
        )
        return obj
