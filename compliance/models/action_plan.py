from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from compliance.constants import (
    ACTION_PLAN_CANCELLABLE_STATUSES,
    ACTION_PLAN_REFUSAL_TRANSITIONS,
    ACTION_PLAN_TRANSITIONS,
    ActionPlanStatus,
    Priority,
)
from context.models.base import ScopedModel


class ComplianceActionPlan(ScopedModel):
    REFERENCE_PREFIX = "CAPL"

    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, default="")
    risks = models.ManyToManyField(
        "risks.Risk",
        blank=True,
        related_name="action_plans",
        verbose_name=_("Linked risks"),
    )
    findings = models.ManyToManyField(
        "compliance.Finding",
        blank=True,
        related_name="action_plans",
        verbose_name=_("Linked findings"),
    )
    gap_description = models.TextField(_("Gap description"))
    remediation_plan = models.TextField(_("Remediation plan"))
    priority = models.CharField(
        _("Priority"), max_length=20, choices=Priority.choices
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_action_plans",
        verbose_name=_("Owner"),
    )
    start_date = models.DateField(_("Start date"), null=True, blank=True)
    target_date = models.DateField(_("Target date"))
    completion_date = models.DateField(_("Completion date"), null=True, blank=True)
    progress_percentage = models.PositiveIntegerField(
        _("Progress (%)"), default=0
    )
    cost_estimate = models.DecimalField(
        _("Cost estimate"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=30,
        choices=ActionPlanStatus.choices,
        default=ActionPlanStatus.NOUVEAU,
    )

    history = HistoricalRecords()

    class Meta(ScopedModel.Meta):
        verbose_name = _("Compliance action plan")
        verbose_name_plural = _("Compliance action plans")

    def __str__(self):
        return f"{self.reference} : {self.name}"

    def get_allowed_transitions(self):
        """Return the list of statuses this action plan can transition to."""
        allowed = list(ACTION_PLAN_TRANSITIONS.get(self.status, []))
        if self.status in ACTION_PLAN_CANCELLABLE_STATUSES:
            allowed.append(ActionPlanStatus.ANNULE)
        return allowed

    def transition_to(self, new_status, user, comment=""):
        """Perform a status transition with validation and audit trail.

        Raises ValueError if the transition is not allowed or if a refusal
        comment is missing.
        """
        from compliance.models.action_plan_transition import ActionPlanTransition

        allowed = self.get_allowed_transitions()
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from {self.status} to {new_status}."
            )

        # Check if this is a refusal (backward transition)
        is_refusal = (
            ACTION_PLAN_REFUSAL_TRANSITIONS.get(self.status) == new_status
        )
        if is_refusal and not comment.strip():
            raise ValueError("A comment is required when refusing.")

        old_status = self.status
        self.status = new_status

        # Auto-set completion fields when closing
        if new_status == ActionPlanStatus.CLOTURE:
            self.completion_date = timezone.now().date()
            self.progress_percentage = 100

        self.save()

        ActionPlanTransition.objects.create(
            action_plan=self,
            from_status=old_status,
            to_status=new_status,
            performed_by=user,
            comment=comment,
            is_refusal=is_refusal,
        )
