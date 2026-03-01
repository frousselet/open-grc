import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class BaseModel(models.Model):
    REFERENCE_PREFIX = ""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(_("Reference"), max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name=_("Created by"),
    )
    is_approved = models.BooleanField(_("Approved"), default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_approved",
        verbose_name=_("Approved by"),
    )
    approved_at = models.DateTimeField(_("Approval date"), null=True, blank=True)
    version = models.PositiveIntegerField(_("Version"), default=1)
    tags = models.ManyToManyField(
        "context.Tag",
        blank=True,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("Tags"),
    )

    @classmethod
    def _generate_next_reference(cls):
        """Generate the next unique reference in the format PREFIX-N."""
        prefix = cls.REFERENCE_PREFIX
        if not prefix:
            return ""
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
        if not self.reference and self.REFERENCE_PREFIX:
            self.reference = self._generate_next_reference()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ScopedModel(BaseModel):
    scope = models.ForeignKey(
        "context.Scope",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        verbose_name=_("Scope"),
    )

    class Meta:
        abstract = True
