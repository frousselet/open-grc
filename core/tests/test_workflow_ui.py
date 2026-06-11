"""Tests for the generic workflow UI surfaces (issue #105, phase 7a).

Covers the stepper context mixin, the shared transition endpoint and the
state badge tag, piloted on the Scope detail page (default workflow).
"""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import GroupFactory, PermissionFactory, UserFactory
from context.models import Scope
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


def _user_with_perms(*codenames):
    user = UserFactory()
    group = GroupFactory()
    for codename in codenames:
        module, feature, action = codename.split(".")
        perm = PermissionFactory(
            codename=codename, module=module, feature=feature, action=action,
        )
        group.permissions.add(perm)
    group.users.add(user)
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


class TestStepperContext:
    def test_draft_scope_offers_submit(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        response = client.get(reverse("context:scope-detail", args=[scope.pk]))
        assert response.status_code == 200
        steps = response.context["wf_steps"]
        assert [s["value"] for s in steps] == ["draft", "pending", "validated"]
        assert steps[0]["state"] == "current"
        assert steps[1]["state"] == "next"
        assert response.context["wf_next_status"] == "pending"
        # Archived renders as the branch, not a main step.
        assert response.context["wf_cancelled"]["value"] == "archived"
        assert response.context["wf_can_cancel"] is False  # draft cannot archive

    def test_pending_without_approve_permission_hides_validate(self):
        user = _user_with_perms("context.scope.read", "context.scope.update")
        scope = ScopeFactory()
        scope.transition_to("pending")
        response = _client(user).get(reverse("context:scope-detail", args=[scope.pk]))
        steps = {s["value"]: s["state"] for s in response.context["wf_steps"]}
        assert steps["pending"] == "current"
        assert steps["validated"] == "future"  # not offered without .approve
        # Send back to draft is the backward move.
        assert response.context["wf_refusal"]["status"] == "draft"

    def test_validated_scope_offers_archive_branch(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory(is_approved=True)
        response = client.get(reverse("context:scope-detail", args=[scope.pk]))
        assert response.context["wf_can_cancel"] is True
        assert response.context["wf_next_status"] is None

    def test_stepper_renders_in_page(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        response = client.get(reverse("context:scope-detail", args=[scope.pk]))
        content = response.content.decode()
        assert "workflow-stepper-" in content
        assert "workflowTransitionModal" in content


class TestTransitionEndpoint:
    def _url(self, scope):
        return reverse(
            "workflow:transition",
            kwargs={"app_label": "context", "model": "scope", "pk": scope.pk},
        )

    def test_submit_transition(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        response = client.post(self._url(scope), {"target_status": "pending"})
        assert response.status_code == 302
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_permission_denied_keeps_state(self):
        user = _user_with_perms("context.scope.read", "context.scope.update")
        scope = ScopeFactory()
        scope.transition_to("pending")
        response = _client(user).post(self._url(scope), {"target_status": "validated"})
        assert response.status_code == 302
        scope.refresh_from_db()
        assert scope.workflow_state == "pending"

    def test_illegal_transition_keeps_state(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        response = client.post(self._url(scope), {"target_status": "archived"})
        assert response.status_code == 302
        scope.refresh_from_db()
        assert scope.workflow_state == "draft"

    def test_unsafe_referer_falls_back_to_root(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        response = client.post(
            self._url(scope),
            {"target_status": "pending"},
            HTTP_REFERER="https://evil.example.com/phish",
        )
        assert response.status_code == 302
        assert response["Location"] == "/"

    def test_safe_next_is_honoured(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        detail = reverse("context:scope-detail", args=[scope.pk])
        response = client.post(
            self._url(scope), {"target_status": "pending", "next": detail},
        )
        assert response["Location"] == detail

    def test_unknown_model_is_404(self):
        client = _client(UserFactory(is_superuser=True))
        scope = ScopeFactory()
        url = self._url(scope).replace("/scope/", "/nope/")
        response = client.post(url, {"target_status": "pending"})
        assert response.status_code == 404

    def test_comment_required_transition_rejected_without_comment(self):
        """A requires_comment transition fails politely without a comment."""
        from compliance.constants import ActionPlanStatus
        from compliance.tests.factories import ComplianceActionPlanFactory

        client = _client(UserFactory(is_superuser=True))
        plan = ComplianceActionPlanFactory(status=ActionPlanStatus.TO_VALIDATE)
        url = reverse(
            "workflow:transition",
            kwargs={"app_label": "compliance", "model": "complianceactionplan", "pk": plan.pk},
        )
        response = client.post(url, {"target_status": "to_define"})
        assert response.status_code == 302
        plan.refresh_from_db()
        assert plan.status == "to_validate"
        response = client.post(
            url, {"target_status": "to_define", "comment": "Too vague"},
        )
        plan.refresh_from_db()
        assert plan.status == "to_define"


class TestStepperRollout:
    def test_risk_detail_renders_generic_stepper(self):
        from risks.tests.factories import RiskFactory

        client = _client(UserFactory(is_superuser=True))
        risk = RiskFactory()
        response = client.get(reverse("risks:risk-detail", args=[risk.pk]))
        assert response.status_code == 200
        assert "workflow-stepper-" in response.content.decode()
        steps = response.context["wf_steps"]
        assert steps[0]["value"] == "identified"
        assert steps[0]["state"] == "current"

    def test_assessment_detail_uses_bespoke_transition_url(self):
        from datetime import date

        from compliance.tests.factories import (
            ComplianceAssessmentFactory,
            FrameworkFactory,
        )

        client = _client(UserFactory(is_superuser=True))
        assessment = ComplianceAssessmentFactory(
            assessment_start_date=date(2026, 1, 1),
            assessment_end_date=date(2026, 6, 30),
        )
        assessment.frameworks.add(FrameworkFactory())
        response = client.get(
            reverse("compliance:assessment-detail", args=[assessment.pk])
        )
        assert response.status_code == 200
        assert response.context["wf_transition_url"] == reverse(
            "compliance:assessment-transition", args=[assessment.pk]
        )
        # The bespoke endpoint (required-fields gating, close side effects)
        # accepts the shared component's parameter name.
        response = client.post(
            response.context["wf_transition_url"], {"target_status": "planned"},
        )
        assessment.refresh_from_db()
        assert assessment.status == "planned"
        assert assessment.workflow_state == "planned"


class TestWorkflowBadgeTag:
    def test_badge_renders_tone_and_label(self):
        from helpers.templatetags.workflow_tags import workflow_badge

        scope = ScopeFactory(is_approved=True)
        ctx = workflow_badge(scope)
        assert ctx["badge_class"] == "success"
        assert str(ctx["label"])  # translated label present

    def test_badge_handles_stale_state(self):
        from helpers.templatetags.workflow_tags import workflow_badge

        scope = ScopeFactory()
        Scope.objects.filter(pk=scope.pk).update(workflow_state="ghost")
        scope.refresh_from_db()
        ctx = workflow_badge(scope)
        assert ctx["badge_class"] == "secondary"
