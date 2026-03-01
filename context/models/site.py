from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import SiteType, Status
from .base import BaseModel


class Site(BaseModel):
    REFERENCE_PREFIX = "SITE"

    name = models.CharField(_("Name"), max_length=255)
    type = models.CharField(
        _("Type"), max_length=20, choices=SiteType.choices, default=SiteType.OTHER
    )
    address = models.TextField(_("Address"), blank=True, default="")
    description = models.TextField(_("Description"), blank=True, default="")
    parent_site = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent site"),
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = _("Site")
        verbose_name_plural = _("Sites")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def clean(self):
        super().clean()
        if self.parent_site_id:
            parent = self.parent_site
            visited = {self.pk}
            while parent is not None:
                if parent.pk in visited:
                    raise ValidationError(
                        {"parent_site": _("Circular reference detected.")}
                    )
                visited.add(parent.pk)
                parent = parent.parent_site

    def get_ancestors(self):
        """Return the list of ancestors from farthest to nearest."""
        ancestors = []
        parent = self.parent_site
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent_site
        return ancestors

    @property
    def full_path(self):
        """Full hierarchical path (e.g. Headquarters / Datacenter)."""
        ancestors = self.get_ancestors()
        names = [a.name for a in ancestors] + [self.name]
        return " / ".join(names)

    @property
    def level(self):
        """Depth in the tree (0 = root)."""
        n, parent = 0, self.parent_site
        while parent:
            n += 1
            parent = parent.parent_site
        return n
