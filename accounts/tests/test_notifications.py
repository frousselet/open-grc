"""Tests for the lifecycle notification service (RG-LC-06 / RG-LC-09)."""

import pytest
from django.core import mail

from accounts.constants import NotificationType
from accounts.models import Notification
from accounts.notifications import (
    notify_lifecycle_submitted,
    resolve_lifecycle_recipients,
)
from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


def _scoped_issue(scope):
    """An element whose scopes M2M is set (Issue is a ScopedModel)."""
    from context.tests.factories import IssueFactory

    issue = IssueFactory()
    issue.scopes.set([scope])
    return issue


class TestRecipientResolution:
    def test_scope_managers_first(self):
        manager = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)
        assert set(resolve_lifecycle_recipients(issue)) == {manager}

    def test_inactive_managers_are_skipped(self):
        manager = UserFactory(is_active=False)
        creator = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)
        issue.created_by = creator
        issue.save()
        assert set(resolve_lifecycle_recipients(issue)) == {creator}

    def test_approve_permission_holders_when_unscoped(self):
        approver = UserFactory()
        perm = PermissionFactory(
            codename="context.issue.approve",
            module="context", feature="issue", action="approve",
        )
        group = GroupFactory()
        group.permissions.add(perm)
        group.users.add(approver)

        from context.tests.factories import IssueFactory

        issue = IssueFactory()  # no scopes
        assert set(resolve_lifecycle_recipients(issue)) == {approver}

    def test_creator_fallback(self):
        creator = UserFactory()
        from context.tests.factories import IssueFactory

        issue = IssueFactory()
        issue.created_by = creator
        issue.save()
        assert set(resolve_lifecycle_recipients(issue)) == {creator}

    def test_actor_is_excluded(self):
        manager = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)
        assert set(resolve_lifecycle_recipients(issue, actor=manager)) == set()


class TestNotifyLifecycleSubmitted:
    def test_creates_notification_rows(self):
        manager = UserFactory()
        actor = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)

        created = notify_lifecycle_submitted(issue, actor=actor)
        assert len(created) == 1
        notification = created[0]
        assert notification.recipient == manager
        assert notification.actor == actor
        assert notification.notification_type == NotificationType.LIFECYCLE_SUBMITTED
        assert notification.target == issue
        assert notification.is_read is False

    def test_email_sent_on_commit(self, django_capture_on_commit_callbacks):
        manager = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)

        with django_capture_on_commit_callbacks(execute=True):
            notify_lifecycle_submitted(issue, actor=UserFactory())
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [manager.email]

    def test_email_opt_out_respected(self, django_capture_on_commit_callbacks):
        manager = UserFactory(email_notifications=False)
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)

        with django_capture_on_commit_callbacks(execute=True):
            notify_lifecycle_submitted(issue, actor=UserFactory())
        assert len(mail.outbox) == 0
        # The in-app notification still exists.
        assert Notification.objects.filter(recipient=manager).count() == 1

    def test_rendered_in_recipient_language(self):
        manager = UserFactory(language="fr")
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)

        created = notify_lifecycle_submitted(issue, actor=UserFactory())
        assert "attente de validation" in created[0].title

    def test_no_recipients_no_rows(self):
        from context.tests.factories import IssueFactory

        issue = IssueFactory()  # unscoped, no approver group, no creator
        assert notify_lifecycle_submitted(issue) == []
        assert Notification.objects.count() == 0


class TestTransitionTriggersNotification:
    def test_submit_notifies_scope_managers(self, django_capture_on_commit_callbacks):
        manager = UserFactory()
        actor = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)

        with django_capture_on_commit_callbacks(execute=True):
            issue.transition_to("pending", actor)

        notification = Notification.objects.get(recipient=manager)
        assert notification.notification_type == NotificationType.LIFECYCLE_SUBMITTED
        assert len(mail.outbox) == 1

    def test_validate_does_not_notify(self):
        manager = UserFactory()
        actor = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)
        issue.transition_to("pending", actor)
        Notification.objects.all().delete()

        issue.transition_to("validated", actor)
        assert Notification.objects.count() == 0

    def test_scope_itself_notifies_its_managers(self):
        """Submitting a Scope notifies its own managers (scope-like container)."""
        manager = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)

        scope.transition_to("pending", UserFactory())
        assert Notification.objects.filter(recipient=manager).exists()

    def test_mark_read(self):
        manager = UserFactory()
        scope = ScopeFactory()
        scope.managers.add(manager)
        issue = _scoped_issue(scope)
        created = notify_lifecycle_submitted(issue)
        notification = created[0]
        notification.mark_read()
        notification.refresh_from_db()
        assert notification.is_read is True
        assert notification.read_at is not None
