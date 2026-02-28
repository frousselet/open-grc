import django_filters

from risks.models import (
    ISO27005Risk,
    Risk,
    RiskAcceptance,
    RiskAssessment,
    RiskCriteria,
    RiskTreatmentPlan,
    Threat,
    Vulnerability,
)


class RiskCriteriaFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = RiskCriteria
        fields = {
            "status": ["exact"],
            "is_default": ["exact"],
        }


class RiskAssessmentFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")
    assessor = django_filters.UUIDFilter(field_name="assessor_id")

    class Meta:
        model = RiskAssessment
        fields = {
            "status": ["exact"],
            "methodology": ["exact"],
        }


class RiskFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    risk_owner = django_filters.UUIDFilter(field_name="risk_owner_id")

    class Meta:
        model = Risk
        fields = {
            "status": ["exact"],
            "priority": ["exact"],
            "risk_source": ["exact"],
            "treatment_decision": ["exact"],
        }


class RiskTreatmentPlanFilter(django_filters.FilterSet):
    risk = django_filters.UUIDFilter(field_name="risk_id")
    assessment = django_filters.UUIDFilter(field_name="risk__assessment_id")
    owner = django_filters.UUIDFilter(field_name="owner_id")

    class Meta:
        model = RiskTreatmentPlan
        fields = {
            "status": ["exact"],
            "treatment_type": ["exact"],
        }


class RiskAcceptanceFilter(django_filters.FilterSet):
    risk = django_filters.UUIDFilter(field_name="risk_id")
    assessment = django_filters.UUIDFilter(field_name="risk__assessment_id")

    class Meta:
        model = RiskAcceptance
        fields = {
            "status": ["exact"],
        }


class ThreatFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Threat
        fields = {
            "type": ["exact"],
            "origin": ["exact"],
            "category": ["exact"],
            "status": ["exact"],
            "is_from_catalog": ["exact"],
        }


class VulnerabilityFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Vulnerability
        fields = {
            "category": ["exact"],
            "severity": ["exact"],
            "status": ["exact"],
            "is_from_catalog": ["exact"],
        }


class ISO27005RiskFilter(django_filters.FilterSet):
    assessment = django_filters.UUIDFilter(field_name="assessment_id")
    threat = django_filters.UUIDFilter(field_name="threat_id")
    vulnerability = django_filters.UUIDFilter(field_name="vulnerability_id")

    class Meta:
        model = ISO27005Risk
        fields = {}
