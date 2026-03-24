"""Tests for the helpers app: models, views, and image utilities."""

import base64
import io
import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client
from django.urls import reverse
from PIL import Image

from accounts.tests.factories import UserFactory
from helpers.image_utils import (
    IMAGE_VARIANT_SIZES,
    _data_uri_to_pil,
    _pil_to_data_uri,
    download_image_to_data_uri,
    generate_image_variants,
    resize_data_uri,
)
from helpers.models import HelpContent

pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────


def _make_png_data_uri(width=128, height=128, color=(255, 0, 0, 255)):
    """Create a minimal PNG data URI for testing."""
    img = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _authenticated_client():
    user = UserFactory()
    client = Client()
    client.force_login(user)
    return client, user


# ── HelpContent model ────────────────────────────────────────


class TestHelpContentModel:
    def test_create_help_content(self):
        hc = HelpContent.objects.create(
            key="test_create.unique_key",
            language="fr",
            title="Aide",
            body="Contenu d'aide",
        )
        assert hc.pk is not None
        assert hc.key == "test_create.unique_key"
        assert hc.language == "fr"

    def test_str_representation(self):
        hc = HelpContent.objects.create(
            key="test_str.repr_key",
            language="de",
            title="Hilfe",
            body="Inhalt",
        )
        assert "test_str.repr_key" in str(hc)
        assert "de" in str(hc)

    def test_unique_together_key_language(self):
        HelpContent.objects.create(
            key="test_unique.dup_key", language="it", title="T", body="B"
        )
        with pytest.raises(Exception):
            HelpContent.objects.create(
                key="test_unique.dup_key", language="it", title="T2", body="B2"
            )

    def test_same_key_different_language(self):
        HelpContent.objects.create(
            key="test_multilang.key", language="ja", title="Aide", body="Corps"
        )
        hc_ko = HelpContent.objects.create(
            key="test_multilang.key", language="ko", title="Help", body="Body"
        )
        assert hc_ko.pk is not None
        assert HelpContent.objects.filter(key="test_multilang.key").count() == 2

    def test_ordering(self):
        HelpContent.objects.create(key="zzz_test.key", language="pt", title="Z", body="B")
        HelpContent.objects.create(key="aaa_test.key", language="pt", title="A", body="B")
        qs = list(HelpContent.objects.filter(key__in=["aaa_test.key", "zzz_test.key"]))
        assert qs[0].key == "aaa_test.key"
        assert qs[1].key == "zzz_test.key"

    def test_updated_at_set_on_create(self):
        hc = HelpContent.objects.create(
            key="test_ts.unique_key", language="sv", title="T", body="B"
        )
        assert hc.updated_at is not None


# ── DismissHelperView ────────────────────────────────────────


class TestDismissHelperView:
    def test_anonymous_redirect(self):
        resp = Client().post(
            reverse("helpers:dismiss"),
            data=json.dumps({"key": "test.key"}),
            content_type="application/json",
        )
        assert resp.status_code == 302

    def test_dismiss_helper_success(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:dismiss"),
            data=json.dumps({"key": "context.scope_list"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["status"] == "ok"
        user.refresh_from_db()
        assert "context.scope_list" in user.dismissed_helpers

    def test_dismiss_same_key_twice_no_duplicate(self):
        client, user = _authenticated_client()
        payload = json.dumps({"key": "context.scope_list"})
        client.post(
            reverse("helpers:dismiss"),
            data=payload,
            content_type="application/json",
        )
        client.post(
            reverse("helpers:dismiss"),
            data=payload,
            content_type="application/json",
        )
        user.refresh_from_db()
        assert user.dismissed_helpers.count("context.scope_list") == 1

    def test_dismiss_invalid_json(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:dismiss"),
            data="not json",
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert "error" in data

    def test_dismiss_missing_key(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:dismiss"),
            data=json.dumps({"key": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert "error" in data

    def test_dismiss_no_key_field(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:dismiss"),
            data=json.dumps({"other": "value"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_dismiss_handles_non_list_dismissed_helpers(self):
        """If dismissed_helpers is somehow not a list, it should reset."""
        client, user = _authenticated_client()
        user.dismissed_helpers = "not_a_list"
        user.save(update_fields=["dismissed_helpers"])
        resp = client.post(
            reverse("helpers:dismiss"),
            data=json.dumps({"key": "test.key"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert "test.key" in user.dismissed_helpers


# ── SaveSortPreferenceView ───────────────────────────────────


class TestSaveSortPreferenceView:
    def test_anonymous_redirect(self):
        resp = Client().post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "scope_list", "sort": "name", "order": "asc"}),
            content_type="application/json",
        )
        assert resp.status_code == 302

    def test_save_sort_success(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "scope_list", "sort": "name", "order": "asc"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["status"] == "ok"
        user.refresh_from_db()
        assert user.table_preferences["scope_list"]["sort"] == "name"
        assert user.table_preferences["scope_list"]["order"] == "asc"

    def test_save_sort_desc_order(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "risk_list", "sort": "priority", "order": "desc"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.table_preferences["risk_list"]["order"] == "desc"

    def test_save_sort_invalid_json(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:save-sort"),
            data="bad",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_sort_missing_view(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "", "sort": "name", "order": "asc"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_sort_missing_sort(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "scope_list", "sort": "", "order": "asc"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_sort_invalid_order(self):
        client, user = _authenticated_client()
        resp = client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "scope_list", "sort": "name", "order": "bad"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_save_sort_handles_non_dict_preferences(self):
        """If table_preferences is somehow not a dict, it should reset."""
        client, user = _authenticated_client()
        user.table_preferences = "not_a_dict"
        user.save(update_fields=["table_preferences"])
        resp = client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "scope_list", "sort": "name", "order": "asc"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert isinstance(user.table_preferences, dict)
        assert "scope_list" in user.table_preferences

    def test_save_sort_multiple_views(self):
        client, user = _authenticated_client()
        client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "scope_list", "sort": "name", "order": "asc"}),
            content_type="application/json",
        )
        client.post(
            reverse("helpers:save-sort"),
            data=json.dumps({"view": "risk_list", "sort": "priority", "order": "desc"}),
            content_type="application/json",
        )
        user.refresh_from_db()
        assert "scope_list" in user.table_preferences
        assert "risk_list" in user.table_preferences


# ── Image utilities ──────────────────────────────────────────


class TestDataUriConversion:
    def test_roundtrip(self):
        original = _make_png_data_uri(64, 64)
        img = _data_uri_to_pil(original)
        assert img.size == (64, 64)
        result = _pil_to_data_uri(img)
        assert result.startswith("data:image/png;base64,")

    def test_pil_to_data_uri_format(self):
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
        uri = _pil_to_data_uri(img)
        assert uri.startswith("data:image/png;base64,")
        # Verify it is valid base64
        b64_part = uri.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert len(decoded) > 0


class TestResizeDataUri:
    def test_resize_to_16(self):
        uri = _make_png_data_uri(128, 128)
        resized = resize_data_uri(uri, 16)
        img = _data_uri_to_pil(resized)
        assert img.size == (16, 16)

    def test_resize_to_64(self):
        uri = _make_png_data_uri(128, 128)
        resized = resize_data_uri(uri, 64)
        img = _data_uri_to_pil(resized)
        assert img.size == (64, 64)


class TestGenerateImageVariants:
    def test_returns_all_sizes(self):
        uri = _make_png_data_uri(128, 128)
        variants = generate_image_variants(uri)
        for size in IMAGE_VARIANT_SIZES:
            assert size in variants
            img = _data_uri_to_pil(variants[size])
            assert img.size == (size, size)

    def test_all_variants_are_data_uris(self):
        uri = _make_png_data_uri(128, 128)
        variants = generate_image_variants(uri)
        for size, data_uri in variants.items():
            assert data_uri.startswith("data:image/png;base64,")


class TestDownloadImageToDataUri:
    @patch("helpers.image_utils.urllib.request.urlopen")
    def test_successful_download(self, mock_urlopen):
        """Mock a successful image download."""
        img = Image.new("RGBA", (256, 256), (0, 255, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers = {"Content-Length": str(len(img_bytes))}
        mock_response.read.return_value = img_bytes
        mock_urlopen.return_value = mock_response

        result = download_image_to_data_uri("https://example.com/logo.png")
        assert result.startswith("data:image/png;base64,")
        result_img = _data_uri_to_pil(result)
        assert result_img.size == (128, 128)

    @patch("helpers.image_utils.urllib.request.urlopen")
    def test_content_too_large_by_header(self, mock_urlopen):
        """Reject images that declare themselves > 5 MB via Content-Length."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers = {"Content-Length": str(10 * 1024 * 1024)}
        mock_urlopen.return_value = mock_response

        with pytest.raises(ValueError, match="too large"):
            download_image_to_data_uri("https://example.com/huge.png")

    @patch("helpers.image_utils.urllib.request.urlopen")
    def test_content_too_large_by_bytes(self, mock_urlopen):
        """Reject images that exceed 5 MB during read."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers = {}
        mock_response.read.return_value = b"\x00" * (5 * 1024 * 1024 + 2)
        mock_urlopen.return_value = mock_response

        with pytest.raises(ValueError, match="too large"):
            download_image_to_data_uri("https://example.com/huge.png")

    @patch("helpers.image_utils.urllib.request.urlopen")
    def test_url_error_raises_value_error(self, mock_urlopen):
        """Network errors should be wrapped in ValueError."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with pytest.raises(ValueError, match="Failed to download"):
            download_image_to_data_uri("https://example.com/bad.png")

    @patch("helpers.image_utils.urllib.request.urlopen")
    def test_invalid_image_data_raises(self, mock_urlopen):
        """Non-image data should raise ValueError."""
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers = {}
        mock_response.read.return_value = b"this is not image data"
        mock_urlopen.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid image"):
            download_image_to_data_uri("https://example.com/text.txt")
