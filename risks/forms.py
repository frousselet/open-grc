from django import forms

from context.models import Scope
from .constants import DEFAULT_IMPACT_SCALES, DEFAULT_LIKELIHOOD_SCALES
from .models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskLevel,
    RiskTreatmentPlan,
    ScaleLevel,
    Threat,
    TreatmentAction,
    Vulnerability,
)

# ── Criteria resolution for scale choices ────────────────────

def _resolve_criteria_from_assessment_id(assessment_id):
    """Look up the RiskCriteria linked to an assessment, or None."""
    if not assessment_id:
        return None
    try:
        assessment = RiskAssessment.objects.select_related(
            "risk_criteria"
        ).get(pk=assessment_id)
        return assessment.risk_criteria
    except (RiskAssessment.DoesNotExist, ValueError):
        return None

FORM_WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}
CHECKBOX_ATTRS = {"class": "form-check-input"}


def get_scale_choices(scale_type, criteria=None):
    """Return (value, label) choices for likelihood or impact Select fields.

    Tries the given criteria first, then the default criteria, then any active
    criteria.  Falls back to hardcoded constants only when no criteria with
    ScaleLevels exists in the database at all.
    """
    # Build ordered list of criteria to try
    candidates = []
    if criteria is not None:
        candidates.append(criteria)
    default_c = RiskCriteria.objects.filter(is_default=True).first()
    if default_c and default_c not in candidates:
        candidates.append(default_c)
    active_c = RiskCriteria.objects.filter(status="active").first()
    if active_c and active_c not in candidates:
        candidates.append(active_c)

    for c in candidates:
        levels = list(
            c.scale_levels.filter(scale_type=scale_type)
            .order_by("level")
            .values_list("level", "name")
        )
        if levels:
            return [("", "---------")] + [
                (lvl, f"{lvl} — {name}") for lvl, name in levels
            ]

    # Ultimate fallback to hardcoded defaults
    defaults = (
        DEFAULT_LIKELIHOOD_SCALES if scale_type == "likelihood"
        else DEFAULT_IMPACT_SCALES
    )
    return [("", "---------")] + [
        (lvl, f"{lvl} — {name}") for lvl, name in defaults
    ]


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


class RiskCriteriaForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = RiskCriteria
        fields = [
            "scope", "name", "description", "acceptance_threshold",
            "is_default", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "acceptance_threshold": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "is_default": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }


class RiskAssessmentForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = RiskAssessment
        fields = [
            "scope", "reference", "name", "description", "methodology",
            "assessment_date", "assessor", "risk_criteria", "status",
            "next_review_date", "summary",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "methodology": forms.Select(attrs=SELECT_ATTRS),
            "assessment_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "assessor": forms.Select(attrs=SELECT_ATTRS),
            "risk_criteria": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "next_review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "summary": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
        }


class RiskForm(forms.ModelForm):
    class Meta:
        model = Risk
        fields = [
            "assessment", "reference", "name", "description", "risk_source",
            "affected_essential_assets", "affected_support_assets",
            "impact_confidentiality", "impact_integrity", "impact_availability",
            "initial_likelihood", "initial_impact",
            "current_likelihood", "current_impact",
            "treatment_decision", "treatment_justification",
            "risk_owner", "priority", "status", "review_date",
        ]
        widgets = {
            "assessment": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "risk_source": forms.Select(attrs=SELECT_ATTRS),
            "affected_essential_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "affected_support_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "impact_confidentiality": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "impact_integrity": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "impact_availability": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "initial_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "initial_impact": forms.Select(attrs=SELECT_ATTRS),
            "current_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "current_impact": forms.Select(attrs=SELECT_ATTRS),
            "treatment_decision": forms.Select(attrs=SELECT_ATTRS),
            "treatment_justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "risk_owner": forms.Select(attrs=SELECT_ATTRS),
            "priority": forms.Select(attrs=SELECT_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        criteria = self._resolve_criteria()
        l_choices = get_scale_choices("likelihood", criteria)
        i_choices = get_scale_choices("impact", criteria)
        for fname in ("initial_likelihood", "current_likelihood"):
            self.fields[fname] = forms.TypedChoiceField(
                choices=l_choices, coerce=int, required=False,
                empty_value=None, label=self.fields[fname].label,
                widget=forms.Select(attrs=SELECT_ATTRS),
            )
        for fname in ("initial_impact", "current_impact"):
            self.fields[fname] = forms.TypedChoiceField(
                choices=i_choices, coerce=int, required=False,
                empty_value=None, label=self.fields[fname].label,
                widget=forms.Select(attrs=SELECT_ATTRS),
            )
        # When editing an existing risk, lock the assessment and source fields
        if self.instance and self.instance.pk:
            self.fields["assessment"].disabled = True
            self.fields["risk_source"].disabled = True

    def _resolve_criteria(self):
        """Find the best RiskCriteria for populating scale choices."""
        # 1. Existing risk → assessment's criteria
        if self.instance and self.instance.pk and self.instance.assessment_id:
            criteria = getattr(self.instance.assessment, "risk_criteria", None)
            if criteria:
                return criteria
        # 2. From POST data or initial data (selected assessment)
        assessment_id = self.data.get("assessment") or self.initial.get("assessment")
        return _resolve_criteria_from_assessment_id(assessment_id)


class RiskTreatmentPlanForm(forms.ModelForm):
    class Meta:
        model = RiskTreatmentPlan
        fields = [
            "risk", "reference", "name", "description", "treatment_type",
            "expected_residual_likelihood", "expected_residual_impact",
            "cost_estimate", "owner", "start_date", "target_date", "status",
        ]
        widgets = {
            "risk": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "treatment_type": forms.Select(attrs=SELECT_ATTRS),
            "expected_residual_likelihood": forms.Select(attrs=SELECT_ATTRS),
            "expected_residual_impact": forms.Select(attrs=SELECT_ATTRS),
            "cost_estimate": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "start_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        criteria = None
        # 1. Existing plan → risk → assessment → criteria
        if self.instance and self.instance.pk and self.instance.risk_id:
            assessment = getattr(self.instance.risk, "assessment", None)
            if assessment:
                criteria = getattr(assessment, "risk_criteria", None)
        # 2. From POST/initial data: get risk → assessment → criteria
        if not criteria:
            risk_id = self.data.get("risk") or self.initial.get("risk")
            if risk_id:
                try:
                    risk_obj = Risk.objects.select_related(
                        "assessment__risk_criteria"
                    ).get(pk=risk_id)
                    criteria = getattr(risk_obj.assessment, "risk_criteria", None)
                except (Risk.DoesNotExist, ValueError):
                    pass
        self.fields["expected_residual_likelihood"] = forms.TypedChoiceField(
            choices=get_scale_choices("likelihood", criteria),
            coerce=int, required=False, empty_value=None,
            label=self.fields["expected_residual_likelihood"].label,
            widget=forms.Select(attrs=SELECT_ATTRS),
        )
        self.fields["expected_residual_impact"] = forms.TypedChoiceField(
            choices=get_scale_choices("impact", criteria),
            coerce=int, required=False, empty_value=None,
            label=self.fields["expected_residual_impact"].label,
            widget=forms.Select(attrs=SELECT_ATTRS),
        )


class RiskAcceptanceForm(forms.ModelForm):
    class Meta:
        model = RiskAcceptance
        fields = [
            "risk", "justification", "conditions", "valid_until", "review_date",
        ]
        widgets = {
            "risk": forms.Select(attrs=SELECT_ATTRS),
            "justification": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "conditions": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "valid_until": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "review_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
        }


class ThreatForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Threat
        fields = [
            "scope", "reference", "name", "description", "type", "origin",
            "category", "typical_likelihood", "is_from_catalog", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "type": forms.Select(attrs=SELECT_ATTRS),
            "origin": forms.Select(attrs=SELECT_ATTRS),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "typical_likelihood": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "is_from_catalog": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }


class VulnerabilityForm(ScopedFormMixin, forms.ModelForm):
    class Meta:
        model = Vulnerability
        fields = [
            "scope", "reference", "name", "description", "category",
            "severity", "affected_assets", "remediation_guidance",
            "is_from_catalog", "status",
        ]
        widgets = {
            "scope": forms.Select(attrs=SELECT_ATTRS),
            "reference": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
            "category": forms.Select(attrs=SELECT_ATTRS),
            "severity": forms.Select(attrs=SELECT_ATTRS),
            "affected_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "remediation_guidance": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "is_from_catalog": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
            "status": forms.Select(attrs=SELECT_ATTRS),
        }


# ── Matrix configuration formsets ────────────────────────────

class ScaleLevelForm(forms.ModelForm):
    class Meta:
        model = ScaleLevel
        fields = ["level", "name", "description"]
        widgets = {
            "level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "style": "width:80px"}),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "description": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
        }


class RiskLevelForm(forms.ModelForm):
    class Meta:
        model = RiskLevel
        fields = ["level", "name", "color", "requires_treatment"]
        widgets = {
            "level": forms.NumberInput(attrs={**FORM_WIDGET_ATTRS, "style": "width:80px"}),
            "name": forms.TextInput(attrs=FORM_WIDGET_ATTRS),
            "color": forms.TextInput(attrs={**FORM_WIDGET_ATTRS, "type": "color", "style": "width:60px; padding:2px"}),
            "requires_treatment": forms.CheckboxInput(attrs=CHECKBOX_ATTRS),
        }


LikelihoodFormSet = forms.inlineformset_factory(
    RiskCriteria, ScaleLevel,
    form=ScaleLevelForm,
    extra=0,
    can_delete=True,
)

ImpactFormSet = forms.inlineformset_factory(
    RiskCriteria, ScaleLevel,
    form=ScaleLevelForm,
    extra=0,
    can_delete=True,
)

RiskLevelFormSet = forms.inlineformset_factory(
    RiskCriteria, RiskLevel,
    form=RiskLevelForm,
    extra=0,
    can_delete=True,
)


class ISO27005RiskForm(forms.ModelForm):
    class Meta:
        model = ISO27005Risk
        fields = [
            "assessment", "threat", "vulnerability",
            "affected_essential_assets", "affected_support_assets",
            "threat_likelihood", "vulnerability_exposure",
            "impact_confidentiality", "impact_integrity", "impact_availability",
            "existing_controls", "description",
        ]
        widgets = {
            "assessment": forms.Select(attrs=SELECT_ATTRS),
            "threat": forms.Select(attrs=SELECT_ATTRS),
            "vulnerability": forms.Select(attrs=SELECT_ATTRS),
            "affected_essential_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "affected_support_assets": forms.SelectMultiple(attrs={**SELECT_ATTRS, "size": 5}),
            "threat_likelihood": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "vulnerability_exposure": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "impact_confidentiality": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "impact_integrity": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "impact_availability": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
            "existing_controls": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show ISO 27005 assessments
        self.fields["assessment"].queryset = RiskAssessment.objects.filter(
            methodology="iso27005"
        )


class TreatmentActionForm(forms.ModelForm):
    class Meta:
        model = TreatmentAction
        fields = [
            "treatment_plan", "description", "owner", "target_date", "status", "order",
        ]
        widgets = {
            "treatment_plan": forms.Select(attrs=SELECT_ATTRS),
            "description": forms.Textarea(attrs={**FORM_WIDGET_ATTRS, "rows": 3}),
            "owner": forms.Select(attrs=SELECT_ATTRS),
            "target_date": forms.DateInput(attrs={**FORM_WIDGET_ATTRS, "type": "date"}, format="%Y-%m-%d"),
            "status": forms.Select(attrs=SELECT_ATTRS),
            "order": forms.NumberInput(attrs=FORM_WIDGET_ATTRS),
        }
