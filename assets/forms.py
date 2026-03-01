import base64

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from context.models import Scope, Site
from helpers.image_utils import generate_image_variants

from .models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierType,
    SupplierTypeRequirement,
    SupportAsset,
)


def _file_to_data_uri(uploaded_file):
    """Convert an uploaded file to a base64 data URI string."""
    data = base64.b64encode(uploaded_file.read()).decode()
    return f"data:{uploaded_file.content_type};base64,{data}"


def _set_logo_with_variants(supplier, data_uri):
    """Set the logo field and generate 16/32/64 variants."""
    supplier.logo = data_uri
    variants = generate_image_variants(data_uri)
    supplier.logo_16 = variants[16]
    supplier.logo_32 = variants[32]
    supplier.logo_64 = variants[64]


FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


class ScopedFormMixin:
    """Filter the scope dropdown to only show scopes the user can access (non-archived)."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "scope" in self.fields:
            qs = Scope.objects.exclude(status="archived")
            if user and not user.is_superuser:
                scope_ids = user.get_allowed_scope_ids()
                if scope_ids is not None:
                    qs = qs.filter(id__in=scope_ids)
            self.fields["scope"].queryset = qs


class EssentialAssetForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = EssentialAsset
        fields = [
            "scope", "name", "description",
            "type", "category", "owner", "custodian",
            "confidentiality_level", "integrity_level", "availability_level",
            "confidentiality_justification", "integrity_justification",
            "availability_justification",
            "max_tolerable_downtime", "recovery_time_objective",
            "recovery_point_objective",
            "data_classification", "personal_data",
            "regulatory_constraints",
            "related_activities", "status", "review_date", "tags",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "custodian": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_level": forms.Select(attrs=SELECT_ATTRS),
            "integrity_level": forms.Select(attrs=SELECT_ATTRS),
            "availability_level": forms.Select(attrs=SELECT_ATTRS),
            "confidentiality_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "integrity_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "availability_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "max_tolerable_downtime": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "recovery_time_objective": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "recovery_point_objective": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "data_classification": forms.Select(attrs=SELECT_ATTRS),
            "personal_data": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "regulatory_constraints": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "related_activities": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }


class SupportAssetForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = SupportAsset
        fields = [
            "scope", "name", "description",
            "type", "category", "owner", "custodian",
            "location", "manufacturer", "model_name", "serial_number",
            "software_version", "ip_address", "hostname", "operating_system",
            "acquisition_date", "end_of_life_date", "warranty_expiry_date",
            "contract_reference",
            "exposure_level", "environment",
            "parent_asset", "status", "review_date", "tags",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "custodian": forms.Select(attrs=SELECT_ATTRS),
            "location": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "manufacturer": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "model_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "serial_number": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "software_version": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "ip_address": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "hostname": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "operating_system": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "acquisition_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "end_of_life_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "warranty_expiry_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "contract_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "exposure_level": forms.Select(attrs=SELECT_ATTRS),
            "environment": forms.Select(attrs=SELECT_ATTRS),
            "parent_asset": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }


class AssetDependencyForm(forms.ModelForm):
    class Meta:
        model = AssetDependency
        fields = [
            "essential_asset", "support_asset",
            "dependency_type", "criticality", "description",
            "is_single_point_of_failure", "redundancy_level",
        ]
        widgets = {
            "essential_asset": forms.Select(attrs=SELECT_ATTRS),
            "support_asset": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_single_point_of_failure": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


class AssetGroupForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = AssetGroup
        fields = [
            "scope", "name", "description", "type", "owner", "status", "tags",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }


class SupplierForm(ScopedFormMixin, forms.ModelForm):
    logo = forms.ImageField(
        label=_("Logo"),
        required=False,
        widget=forms.FileInput(attrs={**FORM_WIDGET_ATTRS, "accept": "image/*"}),
    )
    logo_resized = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Supplier
        fields = [
            "scope", "name", "description",
            "type", "criticality", "owner",
            "contact_name", "contact_email", "contact_phone",
            "website", "address", "country",
            "contract_reference", "contract_start_date", "contract_end_date",
            "status", "notes", "tags",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "contact_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "contact_email": forms.EmailInput(attrs=FORM_WIDGET_ATTRS),
            "contact_phone": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "website": forms.URLInput(attrs=FORM_WIDGET_ATTRS),
            "address": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
            "country": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "contract_reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "contract_start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "contract_end_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "notes": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }

    def save(self, commit=True):
        supplier = super().save(commit=False)
        resized = self.cleaned_data.get("logo_resized")
        if resized:
            _set_logo_with_variants(supplier, resized)
        elif self.files.get("logo"):
            _set_logo_with_variants(supplier, _file_to_data_uri(self.files["logo"]))
        if commit:
            supplier.save()
            self.save_m2m()
        return supplier


class SupplierTypeForm(forms.ModelForm):
    class Meta:
        model = SupplierType
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }


class SupplierTypeRequirementForm(forms.ModelForm):
    class Meta:
        model = SupplierTypeRequirement
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 2}),
        }


SupplierTypeRequirementFormSet = inlineformset_factory(
    SupplierType,
    SupplierTypeRequirement,
    form=SupplierTypeRequirementForm,
    extra=1,
    can_delete=True,
)


class SupplierRequirementForm(forms.ModelForm):
    class Meta:
        model = SupplierRequirement
        fields = [
            "requirement", "title", "description",
            "compliance_status", "evidence", "due_date",
        ]
        widgets = {
            "requirement": forms.Select(attrs=SELECT_ATTRS),
            "title": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "compliance_status": forms.Select(attrs=SELECT_ATTRS),
            "evidence": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "due_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class SupplierRequirementReviewForm(forms.ModelForm):
    evidence_file = forms.FileField(
        label=_("Supporting evidence"),
        required=False,
        widget=forms.ClearableFileInput(attrs=FORM_WIDGET_ATTRS),
        help_text=_("Upload a supporting document (certificate, report, etc.)."),
    )

    class Meta:
        model = SupplierRequirementReview
        fields = ["review_date", "result", "comment"]
        widgets = {
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "result": forms.Select(attrs=SELECT_ATTRS),
            "comment": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
        }

    def save(self, commit=True):
        review = super().save(commit=False)
        if self.files.get("evidence_file"):
            f = self.files["evidence_file"]
            review.evidence_file = _file_to_data_uri(f)
            review.evidence_filename = f.name
        if commit:
            review.save()
        return review


class SupplierDependencyForm(forms.ModelForm):
    class Meta:
        model = SupplierDependency
        fields = [
            "support_asset", "supplier",
            "dependency_type", "criticality", "description",
            "is_single_point_of_failure", "redundancy_level",
        ]
        widgets = {
            "support_asset": forms.Select(attrs=SELECT_ATTRS),
            "supplier": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_single_point_of_failure": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


def _site_tree_choices(queryset):
    """Build tree-ordered (pk, label) choices with full path labels (A / B / C)."""
    sites = list(queryset.select_related("parent_site"))
    by_parent = {}
    for s in sites:
        by_parent.setdefault(s.parent_site_id, []).append(s)

    choices = []
    visited = set()

    def walk(parent_id, path):
        for s in sorted(by_parent.get(parent_id, []), key=lambda x: x.name):
            full_path = path + [s.name]
            choices.append((s.pk, " / ".join(full_path)))
            visited.add(s.pk)
            walk(s.pk, full_path)

    walk(None, [])

    for s in sites:
        if s.pk not in visited:
            choices.append((s.pk, s.name))

    return choices


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = [
            "name", "type", "address", "description", "parent_site", "status", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "address": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "parent_site": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Site.objects.exclude(status="archived")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        field = self.fields["parent_site"]
        field.queryset = qs
        field.choices = [("", field.empty_label or "---------")] + _site_tree_choices(qs)


class SiteAssetDependencyForm(forms.ModelForm):
    class Meta:
        model = SiteAssetDependency
        fields = [
            "support_asset", "site",
            "dependency_type", "criticality", "description",
            "is_single_point_of_failure", "redundancy_level",
        ]
        widgets = {
            "support_asset": forms.Select(attrs=SELECT_ATTRS),
            "site": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_single_point_of_failure": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


class SiteSupplierDependencyForm(forms.ModelForm):
    class Meta:
        model = SiteSupplierDependency
        fields = [
            "site", "supplier",
            "dependency_type", "criticality", "description",
            "is_single_point_of_failure", "redundancy_level",
        ]
        widgets = {
            "site": forms.Select(attrs=SELECT_ATTRS),
            "supplier": forms.Select(attrs=SELECT_ATTRS),
            "dependency_type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_single_point_of_failure": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "redundancy_level": forms.Select(attrs=SELECT_ATTRS),
        }


class AssetValuationForm(forms.ModelForm):
    class Meta:
        model = AssetValuation
        fields = [
            "evaluation_date",
            "confidentiality_level", "integrity_level", "availability_level",
            "justification", "context",
        ]
        widgets = {
            "evaluation_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "confidentiality_level": forms.Select(attrs=SELECT_ATTRS),
            "integrity_level": forms.Select(attrs=SELECT_ATTRS),
            "availability_level": forms.Select(attrs=SELECT_ATTRS),
            "justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "context": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
        }
