from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from context.constants import ActivityStatus, ActivityType, Criticality
from .base import ScopedModel


class Activity(ScopedModel):
    REFERENCE_PREFIX = "ACTV"

    reference = models.CharField(_("Reference"), max_length=50, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    type = models.CharField(_("Type"), max_length=20, choices=ActivityType.choices)
    criticality = models.CharField(
        _("Criticality"), max_length=20, choices=Criticality.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_activities",
        verbose_name=_("Owner"),
    )
    parent_activity = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent activity"),
    )
    related_stakeholders = models.ManyToManyField(
        "context.Stakeholder",
        blank=True,
        related_name="related_activities",
        verbose_name=_("Stakeholders"),
    )
    related_objectives = models.ManyToManyField(
        "context.Objective",
        blank=True,
        related_name="related_activities",
        verbose_name=_("Contributing objectives"),
    )
    # M2M to EssentialAsset omitted — module not yet implemented
    # linked_assets = models.ManyToManyField("assets.EssentialAsset", ...)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ActivityStatus.choices,
        default=ActivityStatus.ACTIVE,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def clean(self):
        super().clean()
        # RS-04: parent and child must share at least one scope
        if self.parent_activity_id and self.pk:
            parent_scopes = set(self.parent_activity.scopes.values_list("pk", flat=True))
            child_scopes = set(self.scopes.values_list("pk", flat=True))
            if parent_scopes and child_scopes and not (parent_scopes & child_scopes):
                raise ValidationError(
                    {
                        "parent_activity": _(
                            "The child activity must share at least one scope with its parent."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
