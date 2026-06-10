"""Unit tests for the declarative step model (core.modal_forms)."""

import pytest
from django import forms
from django.core.exceptions import ImproperlyConfigured

from core.modal_forms import Step, SteppedFormMixin


class MultiStepForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()
    email = forms.EmailField(required=False)
    note = forms.CharField(required=False)
    secret = forms.CharField(widget=forms.HiddenInput, required=False)

    steps = [
        Step("Identity", "person", ["name", "email"]),
        Step("Extra", "tag", ["note"]),
    ]


class SingleStepForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()
    note = forms.CharField(required=False)

    steps = [Step("Identity", "person", ["name", "note"])]


class PlainForm(SteppedFormMixin, forms.Form):
    name = forms.CharField()


def test_is_stepped_and_multistep():
    assert MultiStepForm().is_stepped is True
    assert MultiStepForm().is_multistep is True
    assert SingleStepForm().is_stepped is True
    assert SingleStepForm().is_multistep is False
    # No steps declared at all
    assert PlainForm().is_stepped is False
    assert PlainForm().is_multistep is False


def test_iter_steps_grouping_and_order():
    steps = list(MultiStepForm().iter_steps())
    assert [s["title"] for s in steps] == ["Identity", "Extra"]
    assert [bf.name for bf in steps[0]["fields"]] == ["name", "email"]
    assert [bf.name for bf in steps[1]["fields"]] == ["note"]
    assert steps[0]["number"] == 1
    assert steps[0]["is_first"] and not steps[0]["is_last"]
    assert steps[1]["is_last"] and not steps[1]["is_first"]


def test_required_counts():
    steps = list(MultiStepForm().iter_steps())
    assert steps[0]["required_count"] == 1  # name required, email not
    assert steps[1]["required_count"] == 0
    assert MultiStepForm().required_field_count == 1


def test_hidden_field_does_not_need_a_step():
    # `secret` is a HiddenInput and is intentionally left out of every step.
    assert MultiStepForm().is_stepped  # instantiation did not raise


def test_unknown_field_raises():
    class BadForm(SteppedFormMixin, forms.Form):
        name = forms.CharField()
        steps = [Step("Identity", "person", ["nope"])]

    with pytest.raises(ImproperlyConfigured, match="unknown field 'nope'"):
        BadForm()


def test_duplicate_field_raises():
    class BadForm(SteppedFormMixin, forms.Form):
        name = forms.CharField()
        steps = [
            Step("A", "person", ["name"]),
            Step("B", "tag", ["name"]),
        ]

    with pytest.raises(ImproperlyConfigured, match="more than one step"):
        BadForm()


def test_uncovered_visible_field_raises():
    class BadForm(SteppedFormMixin, forms.Form):
        name = forms.CharField()
        orphan = forms.CharField()
        steps = [Step("Identity", "person", ["name"])]

    with pytest.raises(ImproperlyConfigured, match="not assigned to any step"):
        BadForm()
