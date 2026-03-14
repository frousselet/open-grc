import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ActionPlanTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_plan = models.ForeignKey(
        "compliance.ComplianceActionPlan",
        on_delete=models.CASCADE,
        related_name="transitions",
        verbose_name=_("Action plan"),
    )
    from_status = models.CharField(_("From status"), max_length=30)
    to_status = models.CharField(_("To status"), max_length=30)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="action_plan_transitions",
        verbose_name=_("Performed by"),
    )
    comment = models.TextField(_("Comment"), blank=True, default="")
    is_refusal = models.BooleanField(_("Is refusal"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Action plan transition")
        verbose_name_plural = _("Action plan transitions")

    def __str__(self):
        return f"{self.action_plan} : {self.from_status} → {self.to_status}"
