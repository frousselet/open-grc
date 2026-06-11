import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class ReferenceGeneratorMixin(models.Model):
    """Mixin that adds an auto-generated reference field (PREFIX-N)."""

    REFERENCE_PREFIX = ""

    reference = models.CharField(_("Reference"), max_length=50, unique=True, blank=True)

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


class BaseModel(ReferenceGeneratorMixin):
    REQUIRED_PREFIX_LENGTH = 4

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        prefix = cls.__dict__.get("REFERENCE_PREFIX")
        if prefix and len(prefix) != cls.REQUIRED_PREFIX_LENGTH:
            raise ValueError(
                f"{cls.__name__}.REFERENCE_PREFIX '{prefix}' must be exactly "
                f"{cls.REQUIRED_PREFIX_LENGTH} characters"
            )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    workflow_state = models.CharField(
        _("Lifecycle state"),
        max_length=32,
        default="draft",
        db_index=True,
        help_text=_("Current state of the element in its lifecycle workflow."),
    )
    tags = models.ManyToManyField(
        "context.Tag",
        blank=True,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("Tags"),
    )

    # --- Lifecycle workflow (see core/workflow.py) -------------------------

    def get_workflow(self):
        """Return the :class:`~core.workflow.Workflow` this element runs."""
        from core.workflow import resolve_workflow

        return resolve_workflow(type(self))

    def get_lifecycle_state(self):
        """Return the current :class:`~core.workflow.State` object."""
        return self.get_workflow().state(self.workflow_state)

    @property
    def lifecycle_label(self):
        """Human label of the current state (falls back to the raw code)."""
        try:
            return self.get_lifecycle_state().label
        except Exception:
            return self.workflow_state

    @property
    def counts_in_reports(self):
        """Whether this element is included in reports / KPIs / calendar."""
        try:
            return self.get_lifecycle_state().counts_in_reports
        except Exception:
            return False

    @property
    def is_linkable(self):
        """Whether this element may currently participate in a link."""
        try:
            return self.get_lifecycle_state().linkable
        except Exception:
            return False

    @property
    def is_deletable(self):
        """Whether this element may currently be deleted."""
        try:
            return self.get_lifecycle_state().deletable
        except Exception:
            return False

    @property
    def workflow_perm_namespace(self):
        """Permission feature path used to build transition codenames.

        Defaults to ``<app_label>.<model_name>``. Models whose permission feature
        differs from their model name (e.g. ``compliance.action_plan``) override
        this when their specific workflow is wired.
        """
        return f"{self._meta.app_label}.{self._meta.model_name}"

    def available_transitions(self, user=None):
        """Transitions leaving the current state (optionally filtered by ``user``)."""
        from core.workflow import allowed_transitions

        has_perm = user.has_perm if user is not None else None
        namespace = self.workflow_perm_namespace if user is not None else None
        return allowed_transitions(
            self.get_workflow(),
            self.workflow_state,
            has_perm=has_perm,
            perm_namespace=namespace,
        )

    def transition_to(self, target, user=None, comment=None, *, enforce_permission=False, save=True):
        """Validate and apply a lifecycle transition, then persist.

        Mutates ``workflow_state`` and keeps the legacy ``is_approved`` flag aligned.
        Permission enforcement is opt-in here (the view / API / MCP layer is the
        enforcement point); ``Effect.NOTIFY_OWNER`` is wired in the notification phase.
        """
        from django.utils import timezone

        from core.workflow import Effect, apply_transition

        workflow = self.get_workflow()
        has_perm = user.has_perm if (enforce_permission and user is not None) else None
        namespace = self.workflow_perm_namespace if (enforce_permission and user is not None) else None
        transition = apply_transition(
            self,
            target,
            workflow=workflow,
            has_perm=has_perm,
            perm_namespace=namespace,
            comment=comment,
        )
        new_state = workflow.state(target)
        self.is_approved = new_state.counts_in_reports
        if Effect.STAMP_VALIDATION in transition.effects and user is not None:
            self.approved_by = user
            self.approved_at = timezone.now()
        if save:
            self.save()
        return transition

    def _sync_lifecycle_with_approval(self, save_kwargs):
        """Keep ``workflow_state`` coherent with the legacy ``is_approved`` flag.

        During the migration period both the legacy approval flow (which writes
        ``is_approved``) and the workflow path (which writes ``workflow_state``)
        are active. For an element on a lifecycle that has both ``validated`` and
        ``draft`` states (the default lifecycle), mirror the binary flag onto the
        state, without clobbering the richer states (``pending``, ``archived``)
        that only the workflow path sets.
        """
        try:
            workflow = self.get_workflow()
        except Exception:
            return
        if not (workflow.has_state("validated") and workflow.has_state("draft")):
            return
        before = self.workflow_state
        if self.is_approved and self.workflow_state in ("", "draft", "pending"):
            self.workflow_state = "validated"
        elif not self.is_approved and self.workflow_state == "validated":
            self.workflow_state = "draft"
        if self.workflow_state != before:
            update_fields = save_kwargs.get("update_fields")
            if update_fields is not None:
                save_kwargs["update_fields"] = set(update_fields) | {"workflow_state"}

    def save(self, *args, **kwargs):
        self._sync_lifecycle_with_approval(kwargs)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ScopedModel(BaseModel):
    scopes = models.ManyToManyField(
        "context.Scope",
        related_name="%(class)s_set",
        verbose_name=_("Scopes"),
        blank=True,
    )

    class Meta:
        abstract = True
