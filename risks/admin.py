from django import forms as dj_forms
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .forms import SELECT_ATTRS, _resolve_criteria_from_assessment_id, get_scale_choices
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


class ScaleLevelInline(admin.TabularInline):
    model = ScaleLevel
    extra = 0
    readonly_fields = ("id",)


class RiskLevelInline(admin.TabularInline):
    model = RiskLevel
    extra = 0
    readonly_fields = ("id",)


class TreatmentActionInline(admin.TabularInline):
    model = TreatmentAction
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(RiskCriteria)
class RiskCriteriaAdmin(SimpleHistoryAdmin):
    list_display = ("name", "is_default", "status", "acceptance_threshold")
    list_filter = ("status", "is_default")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "tags")
    inlines = [ScaleLevelInline, RiskLevelInline]


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(SimpleHistoryAdmin):
    list_display = (
        "reference", "name", "methodology", "assessor",
        "status", "assessment_date",
    )
    list_filter = ("status", "methodology")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "tags")


class RiskAdminForm(dj_forms.ModelForm):
    class Meta:
        model = Risk
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        criteria = None
        if self.instance and self.instance.pk and self.instance.assessment_id:
            criteria = getattr(self.instance.assessment, "risk_criteria", None)
        if not criteria:
            assessment_id = self.data.get("assessment") or self.initial.get("assessment")
            criteria = _resolve_criteria_from_assessment_id(assessment_id)
        l_choices = get_scale_choices("likelihood", criteria)
        i_choices = get_scale_choices("impact", criteria)
        for fname in (
            "initial_likelihood", "current_likelihood", "residual_likelihood",
        ):
            self.fields[fname] = dj_forms.TypedChoiceField(
                choices=l_choices, coerce=int, required=False,
                empty_value=None, label=self.fields[fname].label,
                widget=dj_forms.Select(attrs=SELECT_ATTRS),
            )
        for fname in (
            "initial_impact", "current_impact", "residual_impact",
        ):
            self.fields[fname] = dj_forms.TypedChoiceField(
                choices=i_choices, coerce=int, required=False,
                empty_value=None, label=self.fields[fname].label,
                widget=dj_forms.Select(attrs=SELECT_ATTRS),
            )


@admin.register(Risk)
class RiskAdmin(SimpleHistoryAdmin):
    form = RiskAdminForm
    list_display = (
        "reference", "name", "assessment", "priority", "status",
        "current_risk_level", "treatment_decision", "risk_owner",
    )
    list_filter = ("status", "priority", "treatment_decision", "risk_source")
    search_fields = ("reference", "name", "description")
    readonly_fields = (
        "id", "created_at", "updated_at",
        "initial_risk_level", "current_risk_level", "residual_risk_level",
    )
    filter_horizontal = ("affected_essential_assets", "affected_support_assets", "tags")


class TreatmentPlanAdminForm(dj_forms.ModelForm):
    class Meta:
        model = RiskTreatmentPlan
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        criteria = None
        if self.instance and self.instance.pk and self.instance.risk_id:
            assessment = getattr(self.instance.risk, "assessment", None)
            if assessment:
                criteria = getattr(assessment, "risk_criteria", None)
        self.fields["expected_residual_likelihood"] = dj_forms.TypedChoiceField(
            choices=get_scale_choices("likelihood", criteria),
            coerce=int, required=False, empty_value=None,
            label=self.fields["expected_residual_likelihood"].label,
            widget=dj_forms.Select(attrs=SELECT_ATTRS),
        )
        self.fields["expected_residual_impact"] = dj_forms.TypedChoiceField(
            choices=get_scale_choices("impact", criteria),
            coerce=int, required=False, empty_value=None,
            label=self.fields["expected_residual_impact"].label,
            widget=dj_forms.Select(attrs=SELECT_ATTRS),
        )


@admin.register(RiskTreatmentPlan)
class RiskTreatmentPlanAdmin(SimpleHistoryAdmin):
    form = TreatmentPlanAdminForm
    list_display = (
        "reference", "name", "risk", "treatment_type",
        "owner", "progress_percentage", "status", "target_date",
    )
    list_filter = ("status", "treatment_type")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    inlines = [TreatmentActionInline]


@admin.register(RiskAcceptance)
class RiskAcceptanceAdmin(SimpleHistoryAdmin):
    list_display = (
        "risk", "accepted_by", "accepted_at",
        "risk_level_at_acceptance", "status", "valid_until",
    )
    list_filter = ("status",)
    search_fields = ("justification", "conditions")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("tags",)


@admin.register(Threat)
class ThreatAdmin(SimpleHistoryAdmin):
    list_display = (
        "reference", "name", "type", "origin", "category",
        "status", "is_from_catalog",
    )
    list_filter = ("type", "origin", "category", "status", "is_from_catalog")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "tags")


@admin.register(Vulnerability)
class VulnerabilityAdmin(SimpleHistoryAdmin):
    list_display = (
        "reference", "name", "category", "severity",
        "status", "is_from_catalog",
    )
    list_filter = ("category", "severity", "status", "is_from_catalog")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "affected_assets", "tags")


@admin.register(ISO27005Risk)
class ISO27005RiskAdmin(SimpleHistoryAdmin):
    list_display = (
        "assessment", "threat", "vulnerability",
        "combined_likelihood", "max_impact", "risk_level",
    )
    list_filter = ("assessment",)
    search_fields = ("threat__name", "vulnerability__name", "description")
    readonly_fields = (
        "id", "created_at", "updated_at",
        "combined_likelihood", "max_impact", "risk_level",
    )
    filter_horizontal = ("affected_essential_assets", "affected_support_assets", "tags")
