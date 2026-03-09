from django import forms
from django.apps import apps
from django.utils.translation import gettext_lazy as _

from context.models.base import BaseModel

from .models import VersioningConfig


def get_base_model_choices():
    """Return choices for all concrete models inheriting from BaseModel."""
    choices = []
    for model in apps.get_models():
        if issubclass(model, BaseModel) and not model._meta.abstract:
            label = f"{model._meta.app_label}.{model._meta.model_name}"
            verbose = f"{model._meta.app_label} — {model._meta.verbose_name}"
            choices.append((label, verbose))
    choices.sort(key=lambda c: c[0])
    return choices


def get_model_field_choices(model_label):
    """Return choices of editable fields for a given model label."""
    if not model_label:
        return []
    try:
        app_label, model_name = model_label.split(".")
        model = apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return []

    base_fields = {
        "id", "created_at", "updated_at", "created_by",
        "is_approved", "approved_by", "approved_at", "version", "reference",
    }
    choices = []
    for field in model._meta.get_fields():
        if not hasattr(field, "column") and not (
            hasattr(field, "field") and hasattr(field.field, "column")
        ):
            continue
        if field.name in base_fields:
            continue
        verbose = getattr(field, "verbose_name", field.name)
        choices.append((field.name, str(verbose).capitalize()))
    choices.sort(key=lambda c: c[1])
    return choices


class VersioningConfigForm(forms.ModelForm):
    major_fields = forms.MultipleChoiceField(
        label=_("Major change fields"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_(
            "Select the fields whose modification triggers a version increment "
            "and approval reset. If none are selected, all changes are considered major."
        ),
    )

    class Meta:
        model = VersioningConfig
        fields = ["model_name", "model_label", "approval_enabled", "major_fields"]
        widgets = {
            "model_name": forms.Select,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Model name choices
        model_choices = [("", _("— Select a model —"))] + get_base_model_choices()
        self.fields["model_name"].widget = forms.Select(choices=model_choices)

        # Determine model_name from POST data or existing instance
        model_name = None
        if self.data.get("model_name"):
            model_name = self.data["model_name"]
        elif self.instance and self.instance.pk and self.instance.model_name:
            model_name = self.instance.model_name

        if model_name:
            field_choices = get_model_field_choices(model_name)
            self.fields["major_fields"].choices = field_choices
            # Set initial from the JSON field (for edit)
            if self.instance and self.instance.pk and self.instance.major_fields:
                self.initial["major_fields"] = self.instance.major_fields
        else:
            self.fields["major_fields"].choices = []

    def clean_major_fields(self):
        return self.cleaned_data.get("major_fields", [])
