"""Tests for the shared UI template tags in core.templatetags.ui."""
from __future__ import annotations

import pytest
from django.template import Context, Template
from django.test import Client, RequestFactory
from django.urls import reverse

from accounts.tests.factories import UserFactory
from core.templatetags.ui import ILLUSTRATIONS, MODULE_ACCENTS, Step, build_steps

pytestmark = pytest.mark.django_db


def render(tpl: str, ctx: dict | None = None) -> str:
    return Template("{% load ui %}" + tpl).render(Context(ctx or {}))


# ───────────────────────── badge ───────────────────────────────────────


class TestBadgeTag:
    def test_registry_lookup_approval(self):
        out = render('{% badge "approved" type="approval" %}')
        assert "badge-dot" in out
        assert "success" in out
        assert "Approved" in out
        assert "bi-check-circle" in out

    def test_registry_lookup_severity(self):
        out = render('{% badge "critical" type="severity" %}')
        assert "danger" in out
        assert "Critical" in out

    def test_explicit_variant_wins_over_registry(self):
        out = render('{% badge "approved" type="approval" variant="warning" %}')
        assert "warning" in out
        assert "success" not in out.replace("Approved", "")

    def test_explicit_label_wins(self):
        out = render('{% badge "approved" type="approval" label="Validated" %}')
        assert "Validated" in out
        assert "Approved" not in out

    def test_unknown_value_falls_back_to_secondary(self):
        out = render('{% badge "frobnicate" type="approval" %}')
        assert "secondary" in out

    def test_aria_hidden_on_icon(self):
        out = render('{% badge "approved" type="approval" %}')
        assert 'aria-hidden="true"' in out


# ───────────────────────── empty_state ─────────────────────────────────


class TestEmptyStateTag:
    def test_block_level_rendering(self):
        out = render('{% empty_state icon="inbox" title="Nothing" message="No items found." %}')
        assert "empty-state" in out
        assert "bi-inbox" in out
        assert "Nothing" in out
        assert "No items found." in out
        assert "<tr" not in out  # block-level form does not wrap a row

    def test_row_form_wraps_when_colspan_given(self):
        out = render('{% empty_state icon="inbox" title="Nothing" colspan=5 %}')
        assert "<tr" in out
        assert 'colspan="5"' in out

    def test_cta_renders_when_url_and_label_provided(self):
        out = render('{% empty_state icon="inbox" cta_url="/new/" cta_label="Create" %}')
        assert 'href="/new/"' in out
        assert "Create" in out

    def test_no_cta_when_only_url(self):
        out = render('{% empty_state icon="inbox" cta_url="/new/" %}')
        assert 'href="/new/"' not in out

    def test_illustration_supersedes_icon(self):
        out = render('{% empty_state illustration="shield" title="No risks" %}')
        assert "empty-state__illustration" in out
        assert "empty-state--illustrated" in out
        assert "<svg" in out
        assert "empty-state__icon" not in out

    def test_unknown_illustration_falls_back_to_icon(self):
        out = render('{% empty_state illustration="bogus" icon="inbox" title="Nothing" %}')
        assert "empty-state__icon" in out
        assert "empty-state__illustration" not in out


# ───────────────────────── illustration ────────────────────────────────


class TestIllustrationTag:
    def test_renders_svg_for_known_name(self):
        out = render('{% illustration "shield" %}')
        assert "<svg" in out
        assert "viewBox" in out
        assert "fw-illustration" in out

    def test_returns_empty_for_unknown_name(self):
        out = render('{% illustration "frobnicate" %}').strip()
        assert out == ""

    def test_size_kwarg_threads_into_css_variable(self):
        out = render('{% illustration "shield" size="8rem" %}')
        assert "--illustration-size:8rem" in out

    def test_every_registered_illustration_has_an_svg(self):
        assert ILLUSTRATIONS, "ILLUSTRATIONS dict must not be empty"
        for name, svg in ILLUSTRATIONS.items():
            assert "<svg" in svg, f"illustration {name!r} is missing its <svg>"
            assert "viewBox" in svg, f"illustration {name!r} has no viewBox"

    def test_module_accents_are_a_closed_enum(self):
        # All module accents must be referenced from CSS in base.html, but
        # at the data level we at least ensure the set is non-empty and
        # contains the seven business modules + the dashboard alias.
        assert "risks" in MODULE_ACCENTS
        assert "compliance" in MODULE_ACCENTS
        assert "assets" in MODULE_ACCENTS
        assert "context" in MODULE_ACCENTS
        assert "reports" in MODULE_ACCENTS
        assert "accounts" in MODULE_ACCENTS
        assert "helpers" in MODULE_ACCENTS
        assert "dashboard" in MODULE_ACCENTS


# ───────────────────────── page_header ─────────────────────────────────


class TestPageHeaderTag:
    def test_renders_title_and_actions_slot(self):
        out = render(
            '{% page_header "Risks" subtitle="ISO 27005" %}'
            '<a class="my-action">Go</a>'
            "{% endpage_header %}"
        )
        assert "Risks" in out
        assert "ISO 27005" in out
        assert "my-action" in out
        assert "page-header__title" in out
        assert "page-header__actions" in out

    def test_actions_block_optional(self):
        out = render('{% page_header "Risks" %}{% endpage_header %}')
        assert "Risks" in out
        assert "page-header__actions" not in out

    def test_reference_renders(self):
        out = render('{% page_header "Risk-1" reference="RISK-1" %}{% endpage_header %}')
        assert "RISK-1" in out
        assert "ref" in out

    def test_module_accent_applies_modifier_class_and_bar(self):
        out = render('{% page_header "Risk register" accent="risks" %}{% endpage_header %}')
        assert "page-header--accent" in out
        assert "page-header--accent-risks" in out
        assert "page-header__bar" in out

    def test_unknown_accent_is_silently_dropped(self):
        out = render('{% page_header "Title" accent="bogus" %}{% endpage_header %}')
        assert "page-header--accent" not in out
        assert "page-header__bar" not in out

    def test_eyebrow_renders_when_set(self):
        out = render('{% page_header "Risk register" eyebrow="Risks" accent="risks" %}{% endpage_header %}')
        assert "page-header__eyebrow" in out
        assert "Risks" in out

    def test_no_eyebrow_block_when_omitted(self):
        out = render('{% page_header "Title" %}{% endpage_header %}')
        assert "page-header__eyebrow" not in out


# ───────────────────────── kpi_card ────────────────────────────────────


class TestKpiCardTag:
    def test_renders_value_label_icon(self):
        out = render('{% kpi_card icon="shield" value=42 label="Risks" variant="warning" %}')
        assert "kpi-card kpi-card--warning" in out
        assert "bi-shield" in out
        assert "42" in out
        assert "Risks" in out

    def test_trend_up_classified_when_positive(self):
        out = render('{% kpi_card icon="x" value=10 label="x" trend=5 %}')
        assert "kpi-card__trend--up" in out
        assert "bi-arrow-up-right" in out

    def test_trend_down_classified_when_negative(self):
        out = render('{% kpi_card icon="x" value=10 label="x" trend=-3 %}')
        assert "kpi-card__trend--down" in out
        assert "bi-arrow-down-right" in out

    def test_no_trend_block_when_trend_omitted(self):
        out = render('{% kpi_card icon="x" value=10 label="x" %}')
        assert "kpi-card__trend" not in out

    def test_href_renders_as_anchor(self):
        out = render('{% kpi_card icon="x" value=10 label="x" href="/x/" %}')
        assert '<a href="/x/"' in out
        assert "kpi-card--linked" in out

    def test_value_uses_tabular_nums(self):
        out = render('{% kpi_card icon="x" value=10 label="x" %}')
        assert "tabular-nums" in out


# ───────────────────────── approval_banner ─────────────────────────────


class TestFilterChipTag:
    def test_inactive_when_param_missing(self):
        factory = RequestFactory()
        req = factory.get("/risks/")
        out = render(
            '{% filter_chip label="Open" param="status" value="open" %}',
            {"request": req},
        )
        assert "filter-chip" in out
        assert "active" not in out.replace("filter-chip", "")
        assert 'aria-pressed="false"' in out
        assert "?status=open" in out

    def test_active_toggles_off(self):
        factory = RequestFactory()
        req = factory.get("/risks/?status=open")
        out = render(
            '{% filter_chip label="Open" param="status" value="open" %}',
            {"request": req},
        )
        assert 'aria-pressed="true"' in out
        assert "status=open" not in out  # toggled off

    def test_other_params_preserved(self):
        factory = RequestFactory()
        req = factory.get("/risks/?priority=high")
        out = render(
            '{% filter_chip label="Open" param="status" value="open" %}',
            {"request": req},
        )
        assert "priority=high" in out
        assert "status=open" in out

    def test_count_renders(self):
        factory = RequestFactory()
        req = factory.get("/risks/")
        out = render(
            '{% filter_chip label="Open" param="status" value="open" count=42 %}',
            {"request": req},
        )
        assert "42" in out


# ───────────────────────── sidebar_card ────────────────────────────────


class TestSidebarCardTag:
    def test_title_and_body(self):
        out = render(
            '{% sidebar_card "Status" icon="info-circle" %}'
            '<p>body</p>'
            "{% endsidebar_card %}"
        )
        assert "Status" in out
        assert "<p>body</p>" in out
        assert "bi-info-circle" in out
        assert "sidebar-card--sticky" in out

    def test_sticky_disabled(self):
        out = render(
            '{% sidebar_card "Status" sticky=False %}x{% endsidebar_card %}'
        )
        assert "sidebar-card--sticky" not in out


# ───────────────────────── confirm_delete ──────────────────────────────


class TestConfirmDeleteTag:
    def test_renders_button_and_modal(self):
        out = render('{% confirm_delete url="/risks/1/delete/" name="MY-1234" %}')
        assert 'data-bs-toggle="modal"' in out
        assert "MY-1234" in out
        assert 'action="/risks/1/delete/"' in out
        assert 'aria-labelledby' in out

    def test_modal_id_is_unique_per_call(self):
        out = render(
            '{% confirm_delete url="/a/" %}{% confirm_delete url="/b/" %}'
        )
        # Each invocation generates a distinct modal id
        ids = [chunk for chunk in out.split('id="confirm-del-') if chunk]
        assert len(ids) >= 2
        first_id = ids[1].split('"', 1)[0]
        second_id = ids[2].split('"', 1)[0] if len(ids) > 2 else None
        assert second_id is not None
        assert first_id != second_id


# ───────────────────────── bulk_actions_bar ────────────────────────────


class TestBulkActionsBarTag:
    def test_renders_actions(self):
        actions = [
            {"label": "Export", "url": "/x/", "variant": "secondary", "icon": "download"},
            {"label": "Delete", "url": "/d/", "variant": "danger", "icon": "trash"},
        ]
        out = render(
            '{% bulk_actions_bar target_id="my-table" actions=actions %}',
            {"actions": actions},
        )
        assert 'data-bulk-target="my-table"' in out
        assert "Export" in out
        assert "Delete" in out
        assert "btn-danger" in out
        assert "btn-secondary" in out
        assert 'role="region"' in out
        assert "hidden" in out  # starts collapsed


# ───────────────────────── stepper ─────────────────────────────────────


class TestStepperTag:
    def test_renders_steps_in_order(self):
        steps = [
            Step("a", "Alpha", "done"),
            Step("b", "Bravo", "current"),
            Step("c", "Charlie", "next"),
            Step("d", "Delta", "future"),
        ]
        out = render(
            '{% stepper steps=steps next_status="c" transition_url="/go/" %}',
            {"steps": steps},
        )
        assert "Alpha" in out
        assert "Bravo" in out
        assert "Charlie" in out
        assert "Delta" in out
        # Done step pill class present
        assert "stepper__pill--done" in out
        assert "stepper__pill--current" in out
        # Next step renders a form
        assert 'action="/go/"' in out
        assert 'aria-current="step"' in out

    def test_cancelled_branch_renders_svg_when_anchors_set(self):
        steps = [
            Step("draft", "Draft", "current"),
            Step("planned", "Planned", "next"),
            Step("closed", "Closed", "future"),
        ]
        cancelled = Step("cancelled", "Cancelled", "future")
        out = render(
            '{% stepper steps=steps next_status="planned" transition_url="/go/" '
            'cancelled=cancelled can_cancel=True transition_modal_callback="showM" '
            'entity_id="1" start_value="draft" branch_value="planned" terminal_value="closed" %}',
            {"steps": steps, "cancelled": cancelled},
        )
        assert "Cancelled" in out
        assert "data-stepper-svg" in out
        assert "showM(" in out  # JS callback wired

    def test_no_svg_without_anchors(self):
        steps = [Step("a", "Alpha", "current")]
        cancelled = Step("cancelled", "Cancelled", "future")
        out = render(
            '{% stepper steps=steps cancelled=cancelled %}',
            {"steps": steps, "cancelled": cancelled},
        )
        assert "data-stepper-svg" not in out

    def test_build_steps_helper_marks_current_and_next(self):
        defs = [("a", "Alpha"), ("b", "Bravo"), ("c", "Charlie"), ("closed", "Closed")]
        steps = build_steps(defs, current_value="b", terminal_values={"closed"})
        assert [s.state for s in steps] == ["done", "current", "next", "future"]

    def test_build_steps_handles_unknown_current(self):
        defs = [("a", "Alpha"), ("b", "Bravo")]
        steps = build_steps(defs, current_value="zzz")
        # Unknown current → no "done" pills, first is promoted to next
        assert steps[0].state == "next"
        assert steps[1].state == "future"


# ───────────────────────── /styleguide/ ────────────────────────────────


class TestStyleGuideView:
    def test_anonymous_redirected(self):
        resp = Client().get(reverse("styleguide"))
        assert resp.status_code == 302

    def test_authenticated_user_can_view(self):
        user = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("styleguide"))
        assert resp.status_code == 200
        # Every component is present
        assert b"page-header__title" in resp.content
        assert b"badge-dot" in resp.content
        assert b"empty-state" in resp.content
        assert b"kpi-card" in resp.content
        assert b"sidebar-card" in resp.content
        assert b"filter-chip" in resp.content
        assert b"stepper__pill" in resp.content
        assert b"bulk-actions-bar" in resp.content
