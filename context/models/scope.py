from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import Status
from .base import BaseModel


class Scope(BaseModel):
    REFERENCE_PREFIX = "SCOPE"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"))
    parent_scope = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent scope"),
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    boundaries = models.TextField(_("Boundaries and exclusions"), blank=True, default="")
    justification_exclusions = models.TextField(
        _("Justification for exclusions"), blank=True, default=""
    )
    geographic_scope = models.TextField(
        _("Geographic scope"), blank=True, default=""
    )
    organizational_scope = models.TextField(
        _("Organizational scope"), blank=True, default=""
    )
    technical_scope = models.TextField(_("Technical scope"), blank=True, default="")
    included_sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="included_in_scopes",
        verbose_name=_("Included sites"),
    )
    excluded_sites = models.ManyToManyField(
        "context.Site",
        blank=True,
        related_name="excluded_from_scopes",
        verbose_name=_("Excluded sites"),
    )
    # M2M to Referential omitted — module not yet implemented
    # applicable_standards = models.ManyToManyField("referential.Referential", ...)
    effective_date = models.DateField(
        _("Effective date"), null=True, blank=True
    )
    review_date = models.DateField(_("Next review date"), null=True, blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        ordering = ["name"]
        verbose_name = _("Scope")
        verbose_name_plural = _("Scopes")

    def __str__(self):
        return f"{self.reference} — {self.name}"

    def clean(self):
        super().clean()
        if self.parent_scope_id:
            parent = self.parent_scope
            visited = {self.pk}
            while parent is not None:
                if parent.pk in visited:
                    raise ValidationError(
                        {"parent_scope": _("Circular reference detected.")}
                    )
                visited.add(parent.pk)
                parent = parent.parent_scope

    def get_ancestors(self):
        """Return the list of ancestors from farthest to nearest."""
        ancestors = []
        parent = self.parent_scope
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent_scope
        return ancestors

    @property
    def full_path(self):
        """Full hierarchical path (e.g. Group / Subsidiary / Site)."""
        ancestors = self.get_ancestors()
        names = [a.name for a in ancestors] + [self.name]
        return " / ".join(names)

    @property
    def level(self):
        """Depth in the tree (0 = root)."""
        n, parent = 0, self.parent_scope
        while parent:
            n += 1
            parent = parent.parent_scope
        return n
