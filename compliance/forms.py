from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from context.models import Scope
from .models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    AssessmentResult,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)

User = get_user_model()

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


class ScopedFormMixin:
    """Filter the scope dropdown to only show scopes the user can access (non-archived)."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        scope_field_name = "scope" if "scope" in self.fields else "scopes" if "scopes" in self.fields else None
        if scope_field_name:
            qs = Scope.objects.exclude(status="archived")
            if user and not user.is_superuser:
                scope_ids = user.get_allowed_scope_ids()
                if scope_ids is not None:
                    qs = qs.filter(id__in=scope_ids)
            self.fields[scope_field_name].queryset = qs


class FrameworkForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Framework
        fields = [
            "scopes", "reference", "name", "short_name", "description",
            "type", "category", "framework_version",
            "publication_date", "effective_date", "expiry_date",
            "issuing_body", "jurisdiction", "url",
            "is_mandatory", "is_applicable", "applicability_justification",
            "owner", "status", "review_date",
        ]
        widgets = {
            "scopes": forms.SelectMultiple(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "short_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "framework_version": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "publication_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "effective_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "expiry_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "issuing_body": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "jurisdiction": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "url": forms.URLInput(attrs=FORM_WIDGET_ATTRS),
            "is_mandatory": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "applicability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = [
            "framework", "parent_section", "reference", "name",
            "description", "order",
        ]
        widgets = {
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "parent_section": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = [
            "framework", "section", "reference", "name",
            "description", "guidance", "type", "category",
            "is_applicable", "applicability_justification",
            "owner", "priority", "target_date",
            "order", "status",
        ]
        widgets = {
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "section": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "guidance": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "applicability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }


class ComplianceAssessmentForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ComplianceAssessment
        fields = [
            "scope", "framework", "name", "description",
            "assessment_date", "assessor", "methodology",
            "status", "review_date",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "assessment_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "assessor": forms.Select(attrs=SELECT_ATTRS),
            "methodology": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class AssessmentResultForm(forms.ModelForm):
    class Meta:
        model = AssessmentResult
        fields = [
            "requirement", "compliance_status", "compliance_level",
            "evidence", "gaps", "observations",
        ]
        widgets = {
            "requirement": forms.Select(attrs=SELECT_ATTRS),
            "compliance_status": forms.Select(attrs=SELECT_ATTRS),
            "compliance_level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "gaps": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "observations": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }


class RequirementMappingForm(forms.ModelForm):
    class Meta:
        model = RequirementMapping
        fields = [
            "source_requirement", "target_requirement",
            "mapping_type", "coverage_level",
            "description", "justification",
        ]
        widgets = {
            "source_requirement": forms.Select(attrs=SELECT_ATTRS),
            "target_requirement": forms.Select(attrs=SELECT_ATTRS),
            "mapping_type": forms.Select(attrs=SELECT_ATTRS),
            "coverage_level": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }


MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 Mo


class FrameworkImportForm(forms.Form):
    file = forms.FileField(
        label="Fichier",
        help_text="Format JSON ou Excel (.xlsx)",
        widget=forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
    )
    existing_framework = forms.ModelChoiceField(
        queryset=Framework.objects.all(),
        required=False,
        label="Référentiel existant",
        help_text="Laisser vide pour créer un nouveau référentiel.",
        widget=forms.Select(attrs={**SELECT_ATTRS, "class": "form-select"}),
        empty_label="— Nouveau référentiel —",
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label="Propriétaire du référentiel",
        help_text="Obligatoire uniquement pour un nouveau référentiel.",
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ("json", "xlsx"):
            raise forms.ValidationError(
                "Format non supporté. Veuillez fournir un fichier .json ou .xlsx."
            )
        if f.size > MAX_IMPORT_FILE_SIZE:
            raise forms.ValidationError(
                "Le fichier dépasse la taille maximale autorisée (10 Mo)."
            )
        return f

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("existing_framework") and not cleaned.get("owner"):
            self.add_error(
                "owner",
                "Le propriétaire est obligatoire pour créer un nouveau référentiel.",
            )
        return cleaned


class ComplianceActionPlanForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ComplianceActionPlan
        fields = [
            "scope", "reference", "name", "description",
            "assessment", "requirement",
            "gap_description", "remediation_plan",
            "priority", "owner",
            "start_date", "target_date", "completion_date",
            "progress_percentage", "cost_estimate", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "assessment": forms.Select(attrs=SELECT_ATTRS),
            "requirement": forms.Select(attrs=SELECT_ATTRS),
            "gap_description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "remediation_plan": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "completion_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "progress_percentage": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "cost_estimate": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "0.01"}),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }
