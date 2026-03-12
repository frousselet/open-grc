import base64

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from context.models import Scope
from context.widgets import ScopeTreeWidget
from helpers.image_utils import generate_image_variants
from .models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    AssessmentResult,
    Finding,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)

User = get_user_model()

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


def _file_to_data_uri(uploaded_file):
    """Convert an uploaded file to a base64 data URI string."""
    data = base64.b64encode(uploaded_file.read()).decode()
    return f"data:{uploaded_file.content_type};base64,{data}"


def _set_logo_with_variants(instance, data_uri):
    """Set the logo field and generate 16/32/64 variants."""
    instance.logo = data_uri
    variants = generate_image_variants(data_uri)
    instance.logo_16 = variants[16]
    instance.logo_32 = variants[32]
    instance.logo_64 = variants[64]


class ScopedFormMixin:
    """Populate the scopes tree widget with the user's accessible scopes."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "scopes" in self.fields:
            qs = Scope.objects.exclude(status="archived")
            if user and not user.is_superuser:
                scope_ids = user.get_allowed_scope_ids()
                if scope_ids is not None:
                    qs = qs.filter(id__in=scope_ids)
            field = self.fields["scopes"]
            field.queryset = qs
            selected_ids = []
            if self.instance and self.instance.pk:
                selected_ids = list(self.instance.scopes.values_list("pk", flat=True))
            elif self.data:
                selected_ids = self.data.getlist(self.add_prefix("scopes"))
            field.widget.build_tree_data(qs, selected_ids)


class FrameworkForm(ScopedFormMixin, forms.ModelForm):
    logo = forms.ImageField(
        label=_("Logo"),
        required=False,
        widget=forms.FileInput(attrs={**FORM_WIDGET_ATTRS, "accept": "image/*"}),
    )
    logo_resized = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Framework
        fields = [
            "scopes", "name", "short_name", "description",
            "type", "category", "framework_version",
            "publication_date", "effective_date", "expiry_date",
            "issuing_body", "jurisdiction", "url",
            "is_mandatory", "is_applicable", "applicability_justification",
            "owner", "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
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
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }

    def save(self, commit=True):
        framework = super().save(commit=False)
        resized = self.cleaned_data.get("logo_resized")
        if resized:
            _set_logo_with_variants(framework, resized)
        elif self.files.get("logo"):
            _set_logo_with_variants(framework, _file_to_data_uri(self.files["logo"]))
        if commit:
            framework.save()
            self.save_m2m()
        return framework


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = [
            "framework", "parent_section", "name",
            "description", "order",
        ]
        widgets = {
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "parent_section": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class RequirementForm(forms.ModelForm):
    linked_risks = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label=_("Linked risks"),
        widget=forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-risks": "true"}),
    )

    class Meta:
        model = Requirement
        fields = [
            "framework", "section", "requirement_number", "name",
            "description", "guidance", "type", "category",
            "is_applicable", "applicability_justification",
            "linked_risks",
            "linked_assets", "linked_stakeholder_expectations",
            "owner", "priority", "target_date",
            "status", "tags",
        ]
        widgets = {
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "section": forms.Select(attrs=SELECT_ATTRS),
            "requirement_number": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 6, "class": "form-control rich-text"}),
            "guidance": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 5, "class": "form-control rich-text"}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "applicability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control rich-text"}),
            "linked_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-assets": "true"}),
            "linked_stakeholder_expectations": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-expectations": "true"}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from risks.models import Risk
        self.fields["linked_risks"].queryset = Risk.objects.all()
        if self.instance and self.instance.pk:
            self.fields["linked_risks"].initial = self.instance.linked_risks.all()

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.linked_risks.set(self.cleaned_data["linked_risks"])
        else:
            old_save_m2m = self.save_m2m
            def save_m2m():
                old_save_m2m()
                instance.linked_risks.set(self.cleaned_data["linked_risks"])
            self.save_m2m = save_m2m
        return instance


class ComplianceAssessmentForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ComplianceAssessment
        fields = [
            "scopes", "framework", "name", "description",
            "assessment_date", "assessor", "methodology",
            "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "framework": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "assessment_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "assessor": forms.Select(attrs=SELECT_ATTRS),
            "methodology": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }


class AssessmentResultForm(forms.ModelForm):
    class Meta:
        model = AssessmentResult
        fields = [
            "requirement", "compliance_status", "compliance_level",
            "finding", "auditor_recommendations", "evidence",
        ]
        widgets = {
            "requirement": forms.Select(attrs=SELECT_ATTRS),
            "compliance_status": forms.Select(attrs={
                **SELECT_ATTRS,
                "data-compliance-level-defaults": (
                    '{"not_assessed":0,"major_non_conformity":0,'
                    '"minor_non_conformity":30,"observation":50,'
                    '"improvement_opportunity":70,"compliant":100,'
                    '"strength":100,"not_applicable":100}'
                ),
            }),
            "compliance_level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "finding": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "auditor_recommendations": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }

    def __init__(self, *args, assessment=None, requirement_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment:
            self.fields["requirement"].queryset = Requirement.objects.filter(
                framework=assessment.framework, is_applicable=True
            ).order_by("requirement_number")
        if requirement_instance:
            self.fields["requirement"].initial = requirement_instance.pk
            self.fields["requirement"].queryset = Requirement.objects.filter(
                pk=requirement_instance.pk
            )
            self.fields["requirement"].widget.attrs["disabled"] = True


class FindingForm(forms.ModelForm):
    class Meta:
        model = Finding
        fields = [
            "finding_type", "requirements",
            "description", "recommendation", "evidence",
        ]
        widgets = {
            "finding_type": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "recommendation": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "requirements": forms.SelectMultiple(attrs={**SELECT_ATTRS, "data-ts-requirements": "true"}),
        }

    def __init__(self, *args, assessment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assessment:
            self.fields["requirements"].queryset = Requirement.objects.filter(
                framework=assessment.framework, is_applicable=True
            ).order_by("requirement_number")
        else:
            self.fields["requirements"].queryset = Requirement.objects.none()


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


MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class FrameworkImportForm(forms.Form):
    file = forms.FileField(
        label=_("File"),
        help_text=_("JSON or Excel (.xlsx) format"),
        widget=forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
    )
    existing_framework = forms.ModelChoiceField(
        queryset=Framework.objects.all(),
        required=False,
        label=_("Existing framework"),
        help_text=_("Leave blank to create a new framework."),
        widget=forms.Select(attrs={**SELECT_ATTRS, "class": "form-select"}),
        empty_label=_("— New framework —"),
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label=_("Framework owner"),
        help_text=_("Required only for a new framework."),
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in ("json", "xlsx"):
            raise forms.ValidationError(
                _("Unsupported format. Please provide a .json or .xlsx file.")
            )
        if f.size > MAX_IMPORT_FILE_SIZE:
            raise forms.ValidationError(
                _("The file exceeds the maximum allowed size (10 MB).")
            )
        return f

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("existing_framework") and not cleaned.get("owner"):
            self.add_error(
                "owner",
                _("The owner is required to create a new framework."),
            )
        return cleaned


class ComplianceActionPlanForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = ComplianceActionPlan
        fields = [
            "scopes", "name", "description",
            "assessment", "requirement",
            "gap_description", "remediation_plan",
            "priority", "owner",
            "start_date", "target_date", "completion_date",
            "progress_percentage", "cost_estimate", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
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
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
