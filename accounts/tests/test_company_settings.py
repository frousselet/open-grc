import pytest
from django.test import TestCase

from accounts.models import CompanySettings
from accounts.tests.factories import UserFactory


class TestCompanySettingsModel(TestCase):
    def test_get_creates_singleton(self):
        assert CompanySettings.objects.count() == 0
        instance = CompanySettings.get()
        assert CompanySettings.objects.count() == 1
        assert instance.pk is not None

    def test_get_returns_same_instance(self):
        first = CompanySettings.get()
        first.name = "ACME Corp"
        first.save()
        second = CompanySettings.get()
        assert first.pk == second.pk
        assert second.name == "ACME Corp"

    def test_str_returns_name(self):
        instance = CompanySettings.get()
        instance.name = "Test Company"
        instance.save()
        assert str(instance) == "Test Company"

    def test_str_default(self):
        instance = CompanySettings.get()
        assert "settings" in str(instance).lower() or str(instance) == ""


@pytest.mark.django_db
class TestCompanySettingsView:
    def test_get_requires_login(self, client):
        resp = client.get("/accounts/company/")
        assert resp.status_code == 302
        assert "login" in resp.url

    def test_get_requires_permission(self, client):
        user = UserFactory()
        client.force_login(user)
        resp = client.get("/accounts/company/")
        assert resp.status_code == 302  # redirected (no permission)

    def test_get_with_superuser(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        resp = client.get("/accounts/company/")
        assert resp.status_code == 200
        assert b"Company" in resp.content or b"Entreprise" in resp.content

    def test_post_updates_settings(self, client):
        user = UserFactory(is_superuser=True)
        client.force_login(user)
        resp = client.post("/accounts/company/", {
            "name": "My Company",
            "address": "123 Main Street",
        })
        assert resp.status_code == 302
        instance = CompanySettings.get()
        assert instance.name == "My Company"
        assert instance.address == "123 Main Street"
