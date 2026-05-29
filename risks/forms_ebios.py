from django import forms
from django.utils.translation import gettext_lazy as _

from risks.constants import EbiosWorkshopStatus
from risks.models import (
    AttackPathStep,
    AttackTechnique,
    BaselineGap,
    EbiosSummary,
    EbiosWorkshopProgress,
    EcosystemStakeholder,
    FearedEvent,
    OperationalScenario,
    PACSMeasure,
    RiskSource,
    RiskSourceObjectivePair,
    SecurityBaseline,
    StrategicScenario,
    StudyFramework,
    TargetedObjective,
)


class StudyFrameworkForm(forms.ModelForm):
    """Workshop 0 main form. Lives on the assessment detail / workshop page."""

    class Meta:
        model = StudyFramework
        fields = [
            "mission_statement",
            "business_perimeter",
            "technical_perimeter",
            "temporal_perimeter",
            "financial_envelope",
            "applicable_frameworks",
            "participants",
            "assumptions",
            "constraints",
            "expected_deliverables",
        ]
        widgets = {
            "mission_statement": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "business_perimeter": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "technical_perimeter": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "temporal_perimeter": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "financial_envelope": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "applicable_frameworks": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "participants": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "assumptions": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "constraints": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "expected_deliverables": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }


class SecurityBaselineForm(forms.ModelForm):
    """Workshop 1 root form. Edits the M2M selections and the DIC summary."""

    class Meta:
        model = SecurityBaseline
        fields = [
            "business_values",
            "essential_assets",
            "support_assets",
            "dic_summary",
            "baseline_references",
        ]
        widgets = {
            "business_values": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "essential_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "support_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "dic_summary": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "baseline_references": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
        }


class FearedEventForm(forms.ModelForm):
    """Inline form for adding / editing a feared event under the W1 baseline."""

    class Meta:
        model = FearedEvent
        fields = [
            "essential_asset",
            "name",
            "description",
            "dic_criterion",
            "gravity_level",
            "gravity_justification",
        ]
        widgets = {
            "essential_asset": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "dic_criterion": forms.Select(attrs={"class": "form-select"}),
            "gravity_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "gravity_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class BaselineGapForm(forms.ModelForm):
    """Inline form for adding / editing a baseline gap under the W1 baseline."""

    class Meta:
        model = BaselineGap
        fields = [
            "reference_source",
            "linked_requirement",
            "description",
            "severity",
            "recommended_remediation",
            "status",
        ]
        widgets = {
            "reference_source": forms.TextInput(attrs={"class": "form-control"}),
            "linked_requirement": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "recommended_remediation": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class WorkshopRejectForm(forms.Form):
    """Form for rejecting a workshop with a mandatory reason."""

    rejection_reason = forms.CharField(
        label=_("Rejection reason"),
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control", "required": "required"}),
        required=True,
    )


# ── Workshop W2 forms ────────────────────────────────────────


class RiskSourceForm(forms.ModelForm):
    class Meta:
        model = RiskSource
        fields = [
            "name", "description", "category",
            "motivation_level", "motivation_description",
            "resources_level", "activity_level",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "motivation_level": forms.Select(attrs={"class": "form-select"}),
            "motivation_description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "resources_level": forms.Select(attrs={"class": "form-select"}),
            "activity_level": forms.Select(attrs={"class": "form-select"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class TargetedObjectiveForm(forms.ModelForm):
    class Meta:
        model = TargetedObjective
        fields = [
            "name", "description", "category",
            "targeted_essential_assets", "targeted_feared_events",
            "is_retained", "order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "targeted_essential_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "targeted_feared_events": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class RiskSourceObjectivePairForm(forms.ModelForm):
    class Meta:
        model = RiskSourceObjectivePair
        fields = [
            "risk_source", "targeted_objective",
            "relevance", "relevance_justification",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "risk_source": forms.Select(attrs={"class": "form-select"}),
            "targeted_objective": forms.Select(attrs={"class": "form-select"}),
            "relevance": forms.Select(attrs={"class": "form-select"}),
            "relevance_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


# ── Workshop W3 forms ────────────────────────────────────────


class EcosystemStakeholderForm(forms.ModelForm):
    class Meta:
        model = EcosystemStakeholder
        fields = [
            "name", "description", "category",
            "stakeholder", "supplier",
            "dependency", "penetration", "maturity", "trust",
            "accessible_support_assets",
            "is_attack_vector", "attack_vector_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "stakeholder": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "dependency": forms.Select(attrs={"class": "form-select"}),
            "penetration": forms.Select(attrs={"class": "form-select"}),
            "maturity": forms.Select(attrs={"class": "form-select"}),
            "trust": forms.Select(attrs={"class": "form-select"}),
            "accessible_support_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "is_attack_vector": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "attack_vector_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class StrategicScenarioForm(forms.ModelForm):
    class Meta:
        model = StrategicScenario
        fields = [
            "name", "description", "sr_ov_pair",
            "targeted_feared_events",
            "gravity_level", "gravity_justification",
            "likelihood_level", "likelihood_justification",
            "existing_security_measures",
            "is_retained", "retention_justification",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "sr_ov_pair": forms.Select(attrs={"class": "form-select"}),
            "targeted_feared_events": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "gravity_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "gravity_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "likelihood_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "likelihood_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "existing_security_measures": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "is_retained": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "retention_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class AttackPathStepForm(forms.ModelForm):
    class Meta:
        model = AttackPathStep
        fields = ["order", "stakeholder", "description", "action_type", "difficulty"]
        widgets = {
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "stakeholder": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "action_type": forms.Select(attrs={"class": "form-select"}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
        }


# ── Workshop W4 forms ────────────────────────────────────────


class OperationalScenarioForm(forms.ModelForm):
    class Meta:
        model = OperationalScenario
        fields = [
            "strategic_scenario", "name", "description",
            "targeted_support_assets",
            "gravity_level", "gravity_inherited", "gravity_override_justification",
            "likelihood_v", "likelihood_justification",
            "existing_controls", "mitre_version",
        ]
        widgets = {
            "strategic_scenario": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "targeted_support_assets": forms.SelectMultiple(attrs={"class": "form-select", "size": "5"}),
            "gravity_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "gravity_inherited": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "gravity_override_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "likelihood_v": forms.Select(attrs={"class": "form-select"}),
            "likelihood_justification": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "existing_controls": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "mitre_version": forms.TextInput(attrs={"class": "form-control"}),
        }


class AttackTechniqueForm(forms.ModelForm):
    class Meta:
        model = AttackTechnique
        fields = [
            "order", "mitre_technique", "custom_name", "description",
            "targeted_support_asset", "difficulty", "detection_difficulty",
        ]
        widgets = {
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "mitre_technique": forms.Select(attrs={"class": "form-select"}),
            "custom_name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "targeted_support_asset": forms.Select(attrs={"class": "form-select"}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "detection_difficulty": forms.Select(attrs={"class": "form-select"}),
        }


# ── Workshop W5 forms ────────────────────────────────────────


class EbiosSummaryForm(forms.ModelForm):
    class Meta:
        model = EbiosSummary
        fields = [
            "residual_risk_strategy", "monitoring_plan", "pacs_summary",
            "next_strategic_cycle_date", "next_operational_cycle_date",
            "status",
        ]
        widgets = {
            "residual_risk_strategy": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "monitoring_plan": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "pacs_summary": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "next_strategic_cycle_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "next_operational_cycle_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class PACSMeasureForm(forms.ModelForm):
    class Meta:
        model = PACSMeasure
        fields = [
            "name", "description", "measure_type",
            "linked_treatment_plans", "linked_baseline_gaps", "linked_requirements",
            "owner", "start_date", "target_date", "completion_date",
            "cost_estimate", "expected_gain",
            "priority", "status", "progress_percentage", "order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "measure_type": forms.Select(attrs={"class": "form-select"}),
            "linked_treatment_plans": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "linked_baseline_gaps": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "linked_requirements": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "target_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "completion_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cost_estimate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "expected_gain": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "progress_percentage": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }
