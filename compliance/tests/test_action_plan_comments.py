import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse

from accounts.tests.factories import UserFactory
from compliance.models import ActionPlanComment
from compliance.tests.factories import ActionPlanCommentFactory, ComplianceActionPlanFactory


@pytest.mark.django_db
class TestActionPlanCommentModel:
    def test_create_comment(self):
        comment = ActionPlanCommentFactory()
        assert comment.pk is not None
        assert comment.parent is None

    def test_create_reply(self):
        parent = ActionPlanCommentFactory()
        reply = ActionPlanCommentFactory(
            action_plan=parent.action_plan, parent=parent
        )
        assert reply.parent == parent
        assert reply in parent.replies.all()

    def test_nested_reply_raises_error(self):
        parent = ActionPlanCommentFactory()
        reply = ActionPlanCommentFactory(
            action_plan=parent.action_plan, parent=parent
        )
        with pytest.raises(ValidationError):
            ActionPlanCommentFactory(
                action_plan=parent.action_plan, parent=reply
            )

    def test_str(self):
        comment = ActionPlanCommentFactory()
        s = str(comment)
        assert comment.author.display_name in s


@pytest.mark.django_db
class TestActionPlanCommentView:
    def test_detail_view_has_comments(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        comment = ActionPlanCommentFactory(action_plan=ap)
        url = reverse("compliance:action-plan-detail", args=[ap.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert "comments" in response.context
        assert comment in response.context["comments"]

    def test_create_comment_htmx(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        url = reverse("compliance:action-plan-comments", args=[ap.pk])
        response = client.post(
            url,
            {"content": "Test comment"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert ActionPlanComment.objects.filter(action_plan=ap).count() == 1

    def test_create_reply_htmx(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        parent = ActionPlanCommentFactory(action_plan=ap)
        url = reverse("compliance:action-plan-comments", args=[ap.pk])
        response = client.post(
            url,
            {"content": "Test reply", "parent": str(parent.pk)},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        reply = ActionPlanComment.objects.filter(parent=parent).first()
        assert reply is not None
        assert reply.content == "Test reply"

    def test_empty_content_rejected(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        url = reverse("compliance:action-plan-comments", args=[ap.pk])
        response = client.post(
            url,
            {"content": ""},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 400

    def test_login_required(self, client):
        ap = ComplianceActionPlanFactory()
        url = reverse("compliance:action-plan-comments", args=[ap.pk])
        response = client.post(url, {"content": "Test"})
        assert response.status_code == 302  # redirect to login


@pytest.mark.django_db
class TestActionPlanCommentAPI:
    def test_list_comments(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        comment = ActionPlanCommentFactory(action_plan=ap)
        reply = ActionPlanCommentFactory(action_plan=ap, parent=comment)
        url = f"/api/v1/compliance/action-plans/{ap.pk}/comments/"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        # API may wrap in {"data": [...], "status": "success"}
        items = data.get("data", data) if isinstance(data, dict) else data
        assert len(items) == 1  # only top-level
        assert len(items[0]["replies"]) == 1

    def test_create_comment_api(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        url = f"/api/v1/compliance/action-plans/{ap.pk}/comments/"
        response = client.post(
            url,
            {"content": "API comment"},
            content_type="application/json",
        )
        assert response.status_code == 201
        assert ActionPlanComment.objects.filter(action_plan=ap).count() == 1

    def test_create_reply_api(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        ap = ComplianceActionPlanFactory()
        parent = ActionPlanCommentFactory(action_plan=ap)
        url = f"/api/v1/compliance/action-plans/{ap.pk}/comments/"
        response = client.post(
            url,
            {"content": "API reply", "parent": str(parent.pk)},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        item = data.get("data", data) if isinstance(data, dict) and "data" in data else data
        assert item["parent"] == str(parent.pk)
