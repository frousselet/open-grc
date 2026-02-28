from django import forms

from .models import (
    Activity,
    Issue,
    Objective,
    Role,
    Scope,
    Site,
    Stakeholder,
    StakeholderExpectation,
    SwotAnalysis,
    SwotItem,
    Responsibility,
)

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


def _scope_tree_choices(queryset):
    """Build tree-ordered (pk, label) choices with full path labels (A / B / C)."""
    scopes = list(queryset.select_related("parent_scope"))
    by_parent = {}
    for s in scopes:
        by_parent.setdefault(s.parent_scope_id, []).append(s)

    choices = []
    visited = set()

    def walk(parent_id, path):
        for s in sorted(by_parent.get(parent_id, []), key=lambda x: x.name):
            full_path = path + [s.name]
            choices.append((s.pk, " / ".join(full_path)))
            visited.add(s.pk)
            walk(s.pk, full_path)

    walk(None, [])

    for s in scopes:
        if s.pk not in visited:
            choices.append((s.pk, s.name))

    return choices


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
            field = self.fields["scope"]
            field.queryset = qs
            field.choices = [("", field.empty_label or "---------")] + _scope_tree_choices(qs)


class ScopeForm(forms.ModelForm):
    class Meta:
        model = Scope
        fields = [
            "name", "description", "parent_scope", "status",
            "boundaries", "justification_exclusions",
            "geographic_scope", "organizational_scope", "technical_scope",
            "included_sites", "excluded_sites",
            "effective_date", "review_date",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "parent_scope": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "boundaries": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "justification_exclusions": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "geographic_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "organizational_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "technical_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "included_sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "excluded_sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "effective_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Scope.objects.exclude(status="archived")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        field = self.fields["parent_scope"]
        field.queryset = qs
        field.choices = [("", field.empty_label or "---------")] + _scope_tree_choices(qs)
        # Site tree choices for included/excluded
        site_qs = Site.objects.exclude(status="archived")
        site_choices = _site_tree_choices(site_qs)
        for fname in ("included_sites", "excluded_sites"):
            self.fields[fname].queryset = site_qs
            self.fields[fname].choices = site_choices


class IssueForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Issue
        fields = [
            "scope", "name", "description", "type", "category",
            "impact_level", "trend", "source", "review_date", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "impact_level": forms.Select(attrs=SELECT_ATTRS),
            "trend": forms.Select(attrs=SELECT_ATTRS),
            "source": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }


class StakeholderForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Stakeholder
        fields = [
            "scope", "name", "type", "category", "description",
            "contact_name", "contact_email", "contact_phone",
            "influence_level", "interest_level", "status", "review_date",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "contact_name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "contact_email": forms.EmailInput(attrs=FORM_WIDGET_ATTRS),
            "contact_phone": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "influence_level": forms.Select(attrs=SELECT_ATTRS),
            "interest_level": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class StakeholderExpectationForm(forms.ModelForm):
    class Meta:
        model = StakeholderExpectation
        fields = ["description", "type", "priority", "is_applicable"]
        widgets = {
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "is_applicable": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
        }


class ObjectiveForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Objective
        fields = [
            "scope", "reference", "name", "description",
            "category", "type", "target_value", "current_value", "unit",
            "measurement_method", "measurement_frequency", "target_date",
            "owner", "status", "progress_percentage",
            "parent_objective", "review_date",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "target_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "current_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "unit": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "measurement_method": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "measurement_frequency": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "progress_percentage": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "min": 0, "max": 100}),
            "parent_objective": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class SwotAnalysisForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = SwotAnalysis
        fields = [
            "scope", "name", "description", "analysis_date",
            "status", "review_date",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "analysis_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class SwotItemForm(forms.ModelForm):
    class Meta:
        model = SwotItem
        fields = ["quadrant", "description", "impact_level", "order"]
        widgets = {
            "quadrant": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "impact_level": forms.Select(attrs=SELECT_ATTRS),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class RoleForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Role
        fields = [
            "scope", "name", "description", "type",
            "is_mandatory", "source_standard", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "is_mandatory": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "source_standard": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }


class ActivityForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "scope", "reference", "name", "description",
            "type", "criticality", "owner", "parent_activity", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "parent_activity": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
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
            "name", "type", "address", "description", "parent_site", "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "address": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "parent_site": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Site.objects.exclude(status="archived")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        field = self.fields["parent_site"]
        field.queryset = qs
        field.choices = [("", field.empty_label or "---------")] + _site_tree_choices(qs)
