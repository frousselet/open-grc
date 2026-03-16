import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class ActionPlanComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_plan = models.ForeignKey(
        "compliance.ComplianceActionPlan",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Action plan"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="action_plan_comments",
        verbose_name=_("Author"),
    )
    content = models.TextField(_("Content"))
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name=_("Parent comment"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Action plan comment")
        verbose_name_plural = _("Action plan comments")

    def __str__(self):
        return f"{self.author} — {self.created_at:%Y-%m-%d %H:%M}"

    def clean(self):
        if self.parent and self.parent.parent_id is not None:
            raise ValidationError(_("Replies cannot be nested more than one level."))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
