"""Lifecycle notification service: recipient resolution and dispatch.

Creates one in-app :class:`~accounts.models.Notification` row per recipient
(title and message rendered in the recipient's language) and delivers the
email + WebSocket push after the surrounding transaction commits, so a rolled
back transition never sends anything.
"""

import logging

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.urls import NoReverseMatch, reverse
from django.utils import translation
from django.utils.translation import gettext as _

from accounts.constants import NotificationType
from accounts.models import Group, Notification

logger = logging.getLogger(__name__)


def resolve_lifecycle_recipients(instance, actor=None):
    """Resolve who to notify for a lifecycle event on ``instance`` (RG-LC-09).

    Fallback chain: managers of the element's scopes if it is scoped, otherwise
    holders of the entity's ``.approve`` permission, otherwise the creator.
    The actor is never notified of their own action; inactive users are skipped.
    """
    User = get_user_model()
    recipients = User.objects.none()

    if hasattr(instance, "managers"):
        # The element is itself a scope-like container (e.g. Scope): its own
        # managers are the owners to notify.
        recipients = instance.managers.filter(is_active=True)
    if not recipients.exists() and hasattr(instance, "scopes"):
        scope_ids = list(instance.scopes.values_list("pk", flat=True))
        if scope_ids:
            recipients = User.objects.filter(
                managed_scopes__pk__in=scope_ids, is_active=True
            ).distinct()

    if not recipients.exists():
        codename = f"{instance.workflow_perm_namespace}.approve"
        recipients = User.objects.filter(
            pk__in=Group.objects.filter(permissions__codename=codename).values("users"),
            is_active=True,
        ).distinct()

    if not recipients.exists() and instance.created_by_id:
        recipients = User.objects.filter(pk=instance.created_by_id, is_active=True)

    if actor is not None:
        recipients = recipients.exclude(pk=actor.pk)
    return recipients


def _target_url(instance):
    """Best-effort detail URL for an element (no get_absolute_url convention)."""
    app = instance._meta.app_label
    model = instance._meta.model_name
    for name in (f"{app}:{model}-detail", f"{app}:{model.replace('_', '-')}-detail"):
        try:
            return reverse(name, kwargs={"pk": instance.pk})
        except NoReverseMatch:
            continue
    return ""


def notify_lifecycle_submitted(instance, actor=None):
    """Notify the element's owners that it is pending validation (RG-LC-06).

    Creates the in-app rows immediately (same transaction as the transition,
    so they roll back together) and schedules email + WebSocket delivery on
    commit. Returns the created notifications.
    """
    recipients = resolve_lifecycle_recipients(instance, actor=actor)
    if not recipients:
        return []

    label = str(instance._meta.verbose_name)
    name = str(instance)
    actor_name = str(actor) if actor is not None else ""
    url = _target_url(instance)

    notifications = []
    for recipient in recipients:
        with translation.override(recipient.language or settings.LANGUAGE_CODE):
            title = _('%(label)s "%(name)s" is pending validation') % {
                "label": label.capitalize(),
                "name": name,
            }
            if actor_name:
                message = _(
                    "%(actor)s submitted %(label)s \"%(name)s\" for validation."
                ) % {"actor": actor_name, "label": label, "name": name}
            else:
                message = _(
                    "%(label)s \"%(name)s\" was submitted for validation."
                ) % {"label": label.capitalize(), "name": name}
        notifications.append(
            Notification.objects.create(
                recipient=recipient,
                actor=actor,
                notification_type=NotificationType.LIFECYCLE_SUBMITTED,
                title=title,
                message=message,
                target=instance,
                target_url=url,
            )
        )

    transaction.on_commit(lambda: _deliver(notifications))
    return notifications


def _deliver(notifications):
    """Send the email and WebSocket push for freshly created notifications."""
    for notification in notifications:
        recipient = notification.recipient
        if recipient.email_notifications and recipient.email:
            try:
                body = notification.message
                if notification.target_url:
                    site_url = getattr(settings, "SITE_URL", "")
                    body = f"{body}\n\n{site_url}{notification.target_url}"
                send_mail(
                    subject=notification.title,
                    message=body,
                    from_email=None,  # DEFAULT_FROM_EMAIL
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception(
                    "Failed to send notification email to %s", recipient.email
                )
        _push(recipient)


def _push(recipient):
    """Nudge the recipient's browser sessions to refresh their notifications."""
    try:
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"notifications_{recipient.pk}",
            {"type": "notification.new"},
        )
    except Exception:
        logger.debug("Failed to push notification via channel layer", exc_info=True)
