import pytest
from django.test import TestCase

from context.models import Scope
from context.tests.factories import ScopeFactory
from core.models import VersioningConfig, _config_cache


@pytest.mark.django_db
class TestVersioningConfigModel(TestCase):
    """Test the VersioningConfig model and its helper methods."""

    def setUp(self):
        VersioningConfig.clear_cache()

    def tearDown(self):
        VersioningConfig.clear_cache()

    def test_default_approval_enabled(self):
        """Without any config, approval should be enabled by default."""
        assert VersioningConfig.is_approval_enabled(Scope) is True

    def test_default_major_fields_none(self):
        """Without any config, all fields are considered major (returns None)."""
        assert VersioningConfig.get_major_fields(Scope) is None

    def test_approval_disabled(self):
        """When approval_enabled=False, is_approval_enabled returns False."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            approval_enabled=False,
        )
        assert VersioningConfig.is_approval_enabled(Scope) is False

    def test_approval_enabled_explicit(self):
        """When approval_enabled=True, is_approval_enabled returns True."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            approval_enabled=True,
        )
        assert VersioningConfig.is_approval_enabled(Scope) is True

    def test_major_fields_empty_list_means_all(self):
        """An empty major_fields list means all fields are major."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            major_fields=[],
        )
        assert VersioningConfig.get_major_fields(Scope) is None

    def test_major_fields_returns_set(self):
        """A non-empty major_fields list is returned as a set."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            major_fields=["name", "description"],
        )
        result = VersioningConfig.get_major_fields(Scope)
        assert result == {"name", "description"}

    def test_cache_invalidation_on_save(self):
        """Saving a config should invalidate the cache for that model."""
        config = VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            approval_enabled=True,
        )
        # Populate cache
        assert VersioningConfig.is_approval_enabled(Scope) is True

        config.approval_enabled = False
        config.save()

        assert VersioningConfig.is_approval_enabled(Scope) is False

    def test_cache_invalidation_on_delete(self):
        """Deleting a config should clear it from cache."""
        config = VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            approval_enabled=False,
        )
        assert VersioningConfig.is_approval_enabled(Scope) is False

        config.delete()

        assert VersioningConfig.is_approval_enabled(Scope) is True

    def test_get_config(self):
        """get_config returns the config for a model class."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
        )
        config = VersioningConfig.get_config(Scope)
        assert config is not None
        assert config.model_name == "context.scope"

    def test_get_config_returns_none(self):
        """get_config returns None for unconfigured models."""
        config = VersioningConfig.get_config(Scope)
        assert config is None

    def test_str(self):
        config = VersioningConfig(model_name="context.scope", model_label="Scopes")
        assert str(config) == "Scopes"

    def test_str_without_label(self):
        config = VersioningConfig(model_name="context.scope")
        assert str(config) == "context.scope"


@pytest.mark.django_db
class TestApprovableUpdateMixinWithConfig(TestCase):
    """Test that ApprovableUpdateMixin respects VersioningConfig."""

    def setUp(self):
        VersioningConfig.clear_cache()

    def tearDown(self):
        VersioningConfig.clear_cache()

    def test_major_change_increments_version(self):
        """When a major field is changed, version should increment."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            major_fields=["name", "description"],
        )
        scope = ScopeFactory(version=1, is_approved=True)

        # Simulate what ApprovableUpdateMixin._is_major_change does
        from accounts.mixins import ApprovableUpdateMixin
        mixin = ApprovableUpdateMixin()
        mixin.object = scope

        class FakeForm:
            changed_data = ["name"]

        assert mixin._is_major_change(FakeForm()) is True

    def test_minor_change_does_not_trigger(self):
        """When only minor fields change, should not be major."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            major_fields=["name", "description"],
        )
        scope = ScopeFactory(version=1, is_approved=True)

        from accounts.mixins import ApprovableUpdateMixin
        mixin = ApprovableUpdateMixin()
        mixin.object = scope

        class FakeForm:
            changed_data = ["status"]

        assert mixin._is_major_change(FakeForm()) is False

    def test_approval_disabled_never_major(self):
        """When approval is disabled, changes are never considered major."""
        VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            approval_enabled=False,
        )
        scope = ScopeFactory(version=1, is_approved=True)

        from accounts.mixins import ApprovableUpdateMixin
        mixin = ApprovableUpdateMixin()
        mixin.object = scope

        class FakeForm:
            changed_data = ["name"]

        assert mixin._is_major_change(FakeForm()) is False

    def test_no_config_all_changes_major(self):
        """Without any config, all changes are major (backward compatible)."""
        scope = ScopeFactory(version=1, is_approved=True)

        from accounts.mixins import ApprovableUpdateMixin
        mixin = ApprovableUpdateMixin()
        mixin.object = scope

        class FakeForm:
            changed_data = ["status"]

        assert mixin._is_major_change(FakeForm()) is True


@pytest.mark.django_db
class TestVersioningConfigViews(TestCase):
    """Test the admin views for VersioningConfig."""

    def setUp(self):
        from accounts.tests.factories import UserFactory
        self.user = UserFactory(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        VersioningConfig.clear_cache()

    def tearDown(self):
        VersioningConfig.clear_cache()

    def test_list_view(self):
        response = self.client.get("/config/versioning/")
        assert response.status_code == 200

    def test_create_view(self):
        response = self.client.get("/config/versioning/create/")
        assert response.status_code == 200

    def test_create_config(self):
        response = self.client.post("/config/versioning/create/", {
            "model_name": "context.scope",
            "model_label": "Scopes",
            "approval_enabled": True,
        })
        assert response.status_code == 302
        assert VersioningConfig.objects.filter(model_name="context.scope").exists()

    def test_update_config(self):
        config = VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
            approval_enabled=True,
        )
        response = self.client.post(f"/config/versioning/{config.pk}/edit/", {
            "model_name": "context.scope",
            "model_label": "Scopes",
        })
        assert response.status_code == 302
        config.refresh_from_db()
        assert config.approval_enabled is False  # unchecked checkbox

    def test_delete_config(self):
        config = VersioningConfig.objects.create(
            model_name="context.scope",
            model_label="Scopes",
        )
        response = self.client.post(f"/config/versioning/{config.pk}/delete/")
        assert response.status_code == 302
        assert not VersioningConfig.objects.filter(pk=config.pk).exists()

    def test_field_choices_ajax(self):
        response = self.client.get(
            "/config/versioning/field-choices/",
            {"model_name": "context.scope"},
        )
        assert response.status_code == 200
        data = response.json()
        field_values = [f["value"] for f in data]
        assert "name" in field_values
        assert "description" in field_values
        # Base fields should be excluded
        assert "id" not in field_values
        assert "is_approved" not in field_values
        assert "version" not in field_values


@pytest.mark.django_db
class TestTemplateTag(TestCase):
    """Test the approval_enabled_for template tag."""

    def setUp(self):
        VersioningConfig.clear_cache()

    def tearDown(self):
        VersioningConfig.clear_cache()

    def test_tag_with_string_enabled(self):
        from helpers.templatetags.versioning_tags import approval_enabled_for
        assert approval_enabled_for("context.scope") is True

    def test_tag_with_string_disabled(self):
        from helpers.templatetags.versioning_tags import approval_enabled_for
        VersioningConfig.objects.create(
            model_name="context.scope",
            approval_enabled=False,
        )
        assert approval_enabled_for("context.scope") is False

    def test_tag_with_model_class(self):
        from helpers.templatetags.versioning_tags import approval_enabled_for
        assert approval_enabled_for(Scope) is True

    def test_tag_with_invalid_string(self):
        from helpers.templatetags.versioning_tags import approval_enabled_for
        assert approval_enabled_for("nonexistent.model") is True
