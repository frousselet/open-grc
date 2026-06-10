from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    Activity,
    Indicator,
    IndicatorMeasurement,
    Issue,
    Objective,
    Role,
    Scope,
    Site,
    Stakeholder,
    StakeholderExpectation,
    StakeholderFeedback,
    SwotAnalysis,
    SwotItem,
    SwotStrategy,
    Responsibility,
    Tag,
)
from .widgets import IconPickerWidget, ScopeTreeRadioWidget, ScopeTreeWidget
from core.modal_forms import Step, SteppedFormMixin

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}
TAGS_WIDGET = forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4})


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
            # Build tree data for the widget
            selected_ids = []
            if self.instance and self.instance.pk:
                selected_ids = list(self.instance.scopes.values_list("pk", flat=True))
            elif self.data:
                selected_ids = self.data.getlist(self.add_prefix("scopes"))
            field.widget.build_tree_data(qs, selected_ids)


class ScopeBaseForm(SteppedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "diagram-3",
             [[("icon", "auto"), "name"], "parent_scope", "status", "description"]),
        Step(_("Boundaries"), "bounding-box",
             ["boundaries", "justification_exclusions",
              "geographic_scope", "organizational_scope", "technical_scope"]),
        Step(_("Sites & people"), "geo-alt",
             ["included_sites", "excluded_sites", "managers"]),
        Step(_("Dates & tags"), "calendar-event",
             ["effective_date", "review_date", "tags"]),
    ]

    class Meta:
        model = Scope
        fields = [
            "name", "description", "parent_scope", "status", "icon",
            "boundaries", "justification_exclusions",
            "geographic_scope", "organizational_scope", "technical_scope",
            "included_sites", "excluded_sites",
            "managers",
            "effective_date", "review_date", "tags",
        ]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "parent_scope": ScopeTreeRadioWidget(),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "icon": IconPickerWidget(),
            "boundaries": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "justification_exclusions": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "geographic_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "organizational_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "technical_scope": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "included_sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "excluded_sites": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 6}),
            "managers": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "effective_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the scope."),
            "parent_scope": _("Parent scope, if this is a sub-scope."),
            "status": _("Lifecycle state of the scope."),
            "icon": _("Icon representing the scope."),
            "description": _("What this scope covers."),
            "boundaries": _("Where the scope starts and stops."),
            "justification_exclusions": _("Why certain elements are excluded."),
            "geographic_scope": _("Geographic perimeter covered."),
            "organizational_scope": _("Organizational perimeter covered."),
            "technical_scope": _("Technical perimeter covered."),
            "included_sites": _("Sites inside the scope."),
            "excluded_sites": _("Sites explicitly left out."),
            "managers": _("Users responsible for this scope; they automatically get access."),
            "effective_date": _("Date the scope takes effect."),
            "review_date": _("Next date this scope should be reviewed."),
            "tags": _("Free-form labels for filtering and grouping."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Scope.objects.exclude(status="archived")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        field = self.fields["parent_scope"]
        field.queryset = qs
        # Build tree data for the radio widget
        selected_id = self.instance.parent_scope_id if self.instance.pk else None
        if self.data and self.add_prefix("parent_scope") in self.data:
            selected_id = self.data.get(self.add_prefix("parent_scope"))
        field.widget.build_tree_data(qs, selected_id)
        # Site tree choices for included/excluded
        site_qs = Site.objects.exclude(status="archived")
        site_choices = _site_tree_choices(site_qs)
        for fname in ("included_sites", "excluded_sites"):
            self.fields[fname].queryset = site_qs
            self.fields[fname].choices = site_choices
        # Managers: only active users
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["managers"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name", "email")


class ScopeCreateForm(ScopeBaseForm):
    """Scope creation modal form."""


class ScopeUpdateForm(ScopeBaseForm):
    """Scope edition modal form."""


class IssueBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "flag",
             ["name", "type", "category", "source", "description"]),
        Step(_("Assessment & status"), "graph-up",
             ["impact_level", "trend", "review_date", "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Issue
        fields = [
            "scopes", "name", "description", "type", "category",
            "impact_level", "trend", "source", "review_date", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "impact_level": forms.Select(attrs=SELECT_ATTRS),
            "trend": forms.Select(attrs=SELECT_ATTRS),
            "source": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Short title summarizing the issue."),
            "type": _("Whether the issue is internal or external."),
            "category": _("Domain the issue belongs to."),
            "source": _("Where this issue was identified."),
            "description": _("What the issue is and why it matters."),
            "impact_level": _("How strongly this issue affects the organization."),
            "trend": _("Whether the issue is improving, stable or worsening."),
            "review_date": _("Next date this issue should be reviewed."),
            "status": _("Lifecycle state of the issue."),
            "scopes": _("Organizational scopes this issue applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class IssueCreateForm(IssueBaseForm):
    """Issue creation modal form."""


class IssueUpdateForm(IssueBaseForm):
    """Issue edition modal form."""


class StakeholderBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "person-badge", ["name", "type", "category", "description"]),
        Step(_("Contact"), "envelope", ["contact_name", "contact_email", "contact_phone"]),
        Step(_("Assessment & status"), "graph-up",
             ["influence_level", "interest_level", "review_date", "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Stakeholder
        fields = [
            "scopes", "name", "type", "category", "description",
            "contact_name", "contact_email", "contact_phone",
            "influence_level", "interest_level", "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
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
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the stakeholder or group."),
            "type": _("Internal or external stakeholder."),
            "category": _("Kind of stakeholder."),
            "description": _("Who they are and their relationship to the organization."),
            "contact_name": _("Primary contact person."),
            "contact_email": _("Email of the primary contact."),
            "contact_phone": _("Phone of the primary contact."),
            "influence_level": _("How much influence this stakeholder has."),
            "interest_level": _("How interested this stakeholder is."),
            "review_date": _("Next date this stakeholder should be reviewed."),
            "status": _("Lifecycle state of the stakeholder."),
            "scopes": _("Organizational scopes this stakeholder applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class StakeholderCreateForm(StakeholderBaseForm):
    """Stakeholder creation modal form."""


class StakeholderUpdateForm(StakeholderBaseForm):
    """Stakeholder edition modal form."""


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


class ObjectiveBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "bullseye",
             ["name", "category", "type", "owner", "parent_objective", "description"]),
        Step(_("Measurement"), "rulers",
             ["target_value", "current_value", "unit", "progress_percentage",
              "measurement_method", "measurement_frequency"]),
        Step(_("Scope & status"), "diagram-3",
             ["target_date", "review_date", "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Objective
        fields = [
            "scopes", "name", "description",
            "category", "type", "target_value", "current_value", "unit",
            "measurement_method", "measurement_frequency", "target_date",
            "owner", "status", "progress_percentage",
            "parent_objective", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
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
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the objective."),
            "category": _("Category of the objective."),
            "type": _("Type of objective."),
            "owner": _("Person accountable for the objective."),
            "parent_objective": _("Parent objective, if this is a sub-objective."),
            "description": _("What the objective aims to achieve."),
            "target_value": _("Value to reach."),
            "current_value": _("Current measured value."),
            "unit": _("Unit of measure."),
            "progress_percentage": _("Completion from 0 to 100."),
            "measurement_method": _("How the value is measured."),
            "measurement_frequency": _("How often it is measured."),
            "target_date": _("Date the objective should be reached."),
            "review_date": _("Next date this objective should be reviewed."),
            "status": _("Lifecycle state of the objective."),
            "scopes": _("Organizational scopes this objective applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class ObjectiveCreateForm(ObjectiveBaseForm):
    """Objective creation modal form."""


class ObjectiveUpdateForm(ObjectiveBaseForm):
    """Objective edition modal form."""


class SwotAnalysisBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "grid-3x3",
             ["name", "analysis_date", "review_date", "description"]),
        Step(_("Scope & status"), "diagram-3", ["status", "scopes", "tags"]),
    ]

    class Meta:
        model = SwotAnalysis
        fields = [
            "scopes", "name", "description", "analysis_date",
            "status", "review_date", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4, "class": "form-control no-jodit"}),
            "analysis_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Title of the SWOT analysis."),
            "analysis_date": _("Date the analysis was conducted."),
            "review_date": _("Next date this analysis should be reviewed."),
            "description": _("Purpose and context of the analysis."),
            "status": _("Lifecycle state of the analysis."),
            "scopes": _("Organizational scopes this analysis applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class SwotAnalysisCreateForm(SwotAnalysisBaseForm):
    """SWOT analysis creation modal form."""


class SwotAnalysisUpdateForm(SwotAnalysisBaseForm):
    """SWOT analysis edition modal form."""


class SwotItemForm(forms.ModelForm):
    class Meta:
        model = SwotItem
        fields = ["quadrant", "description", "impact_level", "order"]
        widgets = {
            "quadrant": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control no-jodit"}),
            "impact_level": forms.Select(attrs=SELECT_ATTRS),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class SwotStrategyForm(forms.ModelForm):
    class Meta:
        model = SwotStrategy
        fields = ["quadrant", "description", "order"]
        widgets = {
            "quadrant": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3, "class": "form-control no-jodit"}),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }


class RoleBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Shared base for the Role create / edit modals.

    Declares the step grouping and per-field helpers once; the create and
    update forms are thin subclasses (one form per action).
    """

    steps = [
        Step(
            _("Identity"),
            "shield-check",
            ["name", "type", "source_standard", "description", "is_mandatory"],
        ),
        Step(_("Scope & status"), "diagram-3", ["scopes", "status", "tags"]),
    ]

    class Meta:
        model = Role
        fields = [
            "scopes", "name", "description", "type",
            "is_mandatory", "source_standard", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "is_mandatory": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "source_standard": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Short, recognizable title for the role."),
            "type": _("Category the role belongs to."),
            "source_standard": _(
                "Standard or framework the role originates from, if any."
            ),
            "description": _("What the role is responsible for."),
            "is_mandatory": _("A mandatory role must always have an assigned user."),
            "scopes": _("Organizational scopes this role applies to."),
            "status": _("Lifecycle state of the role."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class RoleCreateForm(RoleBaseForm):
    """Role creation modal form."""


class RoleUpdateForm(RoleBaseForm):
    """Role edition modal form."""


class ActivityBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "activity",
             ["name", "type", "criticality", "owner", "parent_activity", "description"]),
        Step(_("Scope & status"), "diagram-3", ["scopes", "status", "tags"]),
    ]

    class Meta:
        model = Activity
        fields = [
            "scopes", "name", "description",
            "type", "criticality", "owner", "parent_activity", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "criticality": forms.Select(attrs=SELECT_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "parent_activity": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Short, recognizable name of the activity."),
            "type": _("Business, support or management nature."),
            "criticality": _("How critical this activity is to the organization."),
            "owner": _("Person accountable for the activity."),
            "parent_activity": _("Parent activity, if this is a sub-process."),
            "description": _("What the activity covers."),
            "scopes": _("Organizational scopes this activity applies to."),
            "status": _("Lifecycle state of the activity."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class ActivityCreateForm(ActivityBaseForm):
    """Activity creation modal form."""


class ActivityUpdateForm(ActivityBaseForm):
    """Activity edition modal form."""


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


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "color": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "type": "color", "style": "width:80px;height:38px;padding:4px"}),
        }


class IndicatorBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    steps = [
        Step(_("Identity"), "bar-chart-line",
             ["name", "collection_method", "format", "description"]),
        Step(_("Format & thresholds"), "sliders",
             ["unit", "expected_level", "critical_threshold_operator",
              "critical_threshold_value", "critical_threshold_min",
              "critical_threshold_max"]),
        Step(_("Review & status"), "calendar-event",
             ["review_frequency", "first_review_date", "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Indicator
        fields = [
            "scopes", "name", "description",
            "collection_method", "format", "unit",
            "expected_level", "critical_threshold_operator",
            "critical_threshold_value",
            "critical_threshold_min", "critical_threshold_max",
            "review_frequency",
            "first_review_date", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "collection_method": forms.Select(attrs=SELECT_ATTRS),
            "format": forms.Select(attrs={**SELECT_ATTRS, "id": "id_format"}),
            "unit": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "expected_level": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_operator": forms.Select(attrs=SELECT_ATTRS),
            "critical_threshold_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_min": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "critical_threshold_max": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "review_frequency": forms.Select(attrs=SELECT_ATTRS),
            "first_review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the indicator."),
            "collection_method": _("How the indicator is collected."),
            "format": _("Data format of the indicator."),
            "description": _("What the indicator measures."),
            "unit": _("Unit of measure."),
            "expected_level": _("Target level to reach."),
            "critical_threshold_operator": _("Comparison used to flag a critical value."),
            "critical_threshold_value": _("Value beyond which the indicator is critical."),
            "critical_threshold_min": _("Lower bound of the acceptable range."),
            "critical_threshold_max": _("Upper bound of the acceptable range."),
            "review_frequency": _("How often the indicator is reviewed."),
            "first_review_date": _("Date of the first review."),
            "status": _("Lifecycle state of the indicator."),
            "scopes": _("Organizational scopes this indicator applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class IndicatorCreateForm(IndicatorBaseForm):
    """Indicator creation modal form."""


class IndicatorUpdateForm(IndicatorBaseForm):
    """Indicator edition modal form."""


class PredefinedIndicatorBaseForm(SteppedFormMixin, ScopedFormMixin, forms.ModelForm):
    """Form for creating predefined Cairn indicators."""

    steps = [
        Step(_("Identity"), "bar-chart-line",
             ["name", "internal_source", "internal_source_parameter", "description"]),
        Step(_("Format & thresholds"), "sliders",
             ["expected_level", "critical_threshold_operator",
              "critical_threshold_value", "critical_threshold_min",
              "critical_threshold_max"]),
        Step(_("Review & status"), "calendar-event",
             ["review_frequency", "first_review_date", "status", "scopes", "tags"]),
    ]

    class Meta:
        model = Indicator
        fields = [
            "scopes", "name", "description",
            "internal_source", "internal_source_parameter",
            "expected_level", "critical_threshold_operator",
            "critical_threshold_value",
            "critical_threshold_min", "critical_threshold_max",
            "review_frequency",
            "first_review_date", "status", "tags",
        ]
        widgets = {
            "scopes": ScopeTreeWidget(),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "internal_source": forms.Select(attrs=SELECT_ATTRS),
            "internal_source_parameter": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "expected_level": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_operator": forms.Select(attrs=SELECT_ATTRS),
            "critical_threshold_value": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "critical_threshold_min": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "critical_threshold_max": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "step": "any"}),
            "review_frequency": forms.Select(attrs=SELECT_ATTRS),
            "first_review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "tags": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
        }
        help_texts = {
            "name": _("Name of the indicator."),
            "internal_source": _("Cairn data source feeding this indicator."),
            "internal_source_parameter": _("Parameter passed to the data source."),
            "description": _("What the indicator measures."),
            "expected_level": _("Target level to reach."),
            "critical_threshold_operator": _("Comparison used to flag a critical value."),
            "critical_threshold_value": _("Value beyond which the indicator is critical."),
            "critical_threshold_min": _("Lower bound of the acceptable range."),
            "critical_threshold_max": _("Upper bound of the acceptable range."),
            "review_frequency": _("How often the indicator is reviewed."),
            "first_review_date": _("Date of the first review."),
            "status": _("Lifecycle state of the indicator."),
            "scopes": _("Organizational scopes this indicator applies to."),
            "tags": _("Free-form labels for filtering and grouping."),
        }


class PredefinedIndicatorCreateForm(PredefinedIndicatorBaseForm):
    """Predefined indicator creation modal form."""


class PredefinedIndicatorUpdateForm(PredefinedIndicatorBaseForm):
    """Predefined indicator edition modal form."""


class IndicatorMeasurementForm(forms.ModelForm):
    class Meta:
        model = IndicatorMeasurement
        fields = ["value", "notes"]
        widgets = {
            "value": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "placeholder": _("Value")}),
            "notes": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "placeholder": _("Notes (optional)")}),
        }

    def __init__(self, *args, indicator_format=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.indicator_format = indicator_format
        if indicator_format == "boolean":
            self.fields["value"] = forms.ChoiceField(
                choices=[("true", _("True")), ("false", _("False"))],
                widget=forms.Select(attrs=SELECT_ATTRS),
                label=self.fields["value"].label,
            )
        elif indicator_format == "number":
            self.fields["value"].widget = forms.TextInput(
                attrs={**FORM_WIDGET_ATTRS, "inputmode": "decimal", "placeholder": _("Value")},
            )

    def clean_value(self):
        value = self.cleaned_data.get("value", "")
        if self.indicator_format == "number":
            # Normalize locale-specific separators: strip thousand separators
            # (space, non-breaking space) and convert decimal comma to dot.
            normalized = value.replace("\u00a0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
            try:
                float(normalized)
            except (ValueError, TypeError):
                raise forms.ValidationError(_("Please enter a valid number."))
            return normalized
        return value


class StakeholderFeedbackForm(forms.ModelForm):
    class Meta:
        model = StakeholderFeedback
        fields = [
            "stakeholder", "channel", "received_date", "subject", "content",
            "sentiment", "severity", "status", "response",
            "linked_issues", "linked_expectations",
            "scopes", "tags",
        ]
        widgets = {
            "stakeholder": forms.Select(attrs=SELECT_ATTRS),
            "channel": forms.Select(attrs=SELECT_ATTRS),
            "received_date": forms.DateInput(
                attrs={**FORM_WIDGET_ATTRS, "type": "date"},
            ),
            "subject": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "content": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "sentiment": forms.Select(attrs=SELECT_ATTRS),
            "severity": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "response": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "linked_issues": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "linked_expectations": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "scopes": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 4}),
            "tags": TAGS_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stakeholder"].queryset = Stakeholder.objects.order_by("name")
        self.fields["scopes"].queryset = Scope.objects.exclude(
            status="archived",
        ).order_by("name")
        self.fields["linked_issues"].queryset = Issue.objects.order_by("-updated_at")
        self.fields["linked_expectations"].queryset = (
            StakeholderExpectation.objects.select_related("stakeholder")
            .order_by("stakeholder__name")
        )
