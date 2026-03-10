import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from context.constants import ImpactLevel, SwotQuadrant
from context.models import SwotItem
from .factories import SwotAnalysisFactory, SwotItemFactory

pytestmark = pytest.mark.django_db


class TestSwotDetailView:
    def test_detail_shows_matrix_tab(self):
        user = UserFactory(is_superuser=True)
        analysis = SwotAnalysisFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("context:swot-detail", args=[analysis.pk]))
        assert resp.status_code == 200
        assert b"Matrix" in resp.content or "Matrice".encode() in resp.content

    def test_detail_shows_items_by_quadrant(self):
        user = UserFactory(is_superuser=True)
        analysis = SwotAnalysisFactory()
        SwotItemFactory(swot_analysis=analysis, quadrant=SwotQuadrant.STRENGTH, description="Strong point")
        SwotItemFactory(swot_analysis=analysis, quadrant=SwotQuadrant.WEAKNESS, description="Weak point")
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("context:swot-detail", args=[analysis.pk]))
        assert resp.status_code == 200
        assert b"Strong point" in resp.content
        assert b"Weak point" in resp.content


class TestSwotItemCreateView:
    def test_login_required(self):
        analysis = SwotAnalysisFactory()
        client = Client()
        resp = client.get(reverse("context:swot-item-create", args=[analysis.pk]))
        assert resp.status_code == 302

    def test_get_form(self):
        user = UserFactory(is_superuser=True)
        analysis = SwotAnalysisFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("context:swot-item-create", args=[analysis.pk]))
        assert resp.status_code == 200

    def test_get_form_with_quadrant_prefill(self):
        user = UserFactory(is_superuser=True)
        analysis = SwotAnalysisFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(
            reverse("context:swot-item-create", args=[analysis.pk]) + "?quadrant=weakness"
        )
        assert resp.status_code == 200

    def test_create_item(self):
        user = UserFactory(is_superuser=True)
        analysis = SwotAnalysisFactory()
        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse("context:swot-item-create", args=[analysis.pk]),
            {
                "quadrant": SwotQuadrant.STRENGTH,
                "description": "New strength item",
                "impact_level": ImpactLevel.HIGH,
                "order": 0,
            },
        )
        assert resp.status_code == 204
        assert SwotItem.objects.filter(
            swot_analysis=analysis, description="New strength item"
        ).exists()


class TestSwotItemUpdateView:
    def test_get_form(self):
        user = UserFactory(is_superuser=True)
        item = SwotItemFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(
            reverse("context:swot-item-update", args=[item.swot_analysis.pk, item.pk])
        )
        assert resp.status_code == 200

    def test_update_item(self):
        user = UserFactory(is_superuser=True)
        item = SwotItemFactory(description="Old description")
        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse("context:swot-item-update", args=[item.swot_analysis.pk, item.pk]),
            {
                "quadrant": item.quadrant,
                "description": "Updated description",
                "impact_level": item.impact_level,
                "order": 0,
            },
        )
        assert resp.status_code == 204
        item.refresh_from_db()
        assert item.description == "Updated description"


class TestSwotItemDeleteView:
    def test_delete_item(self):
        user = UserFactory(is_superuser=True)
        item = SwotItemFactory()
        analysis = item.swot_analysis
        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse("context:swot-item-delete", args=[analysis.pk, item.pk])
        )
        assert resp.status_code == 204
        assert not SwotItem.objects.filter(pk=item.pk).exists()

    def test_delete_requires_login(self):
        item = SwotItemFactory()
        client = Client()
        resp = client.post(
            reverse("context:swot-item-delete", args=[item.swot_analysis.pk, item.pk])
        )
        assert resp.status_code == 302
