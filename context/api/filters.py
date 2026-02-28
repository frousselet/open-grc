import django_filters

from context.models import (
    Activity,
    Issue,
    Objective,
    Role,
    Scope,
    Site,
    Stakeholder,
    SwotAnalysis,
)


class ScopeFilter(django_filters.FilterSet):
    class Meta:
        model = Scope
        fields = {
            "status": ["exact"],
            "effective_date": ["gte", "lte"],
            "review_date": ["gte", "lte"],
        }


class SiteFilter(django_filters.FilterSet):
    class Meta:
        model = Site
        fields = {
            "type": ["exact"],
            "status": ["exact"],
            "parent_site": ["exact"],
        }


class IssueFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Issue
        fields = {
            "type": ["exact"],
            "category": ["exact"],
            "impact_level": ["exact"],
            "status": ["exact"],
            "trend": ["exact"],
        }


class StakeholderFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Stakeholder
        fields = {
            "type": ["exact"],
            "category": ["exact"],
            "influence_level": ["exact"],
            "interest_level": ["exact"],
            "status": ["exact"],
        }


class ObjectiveFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Objective
        fields = {
            "category": ["exact"],
            "type": ["exact"],
            "status": ["exact"],
            "owner": ["exact"],
            "measurement_frequency": ["exact"],
        }


class SwotAnalysisFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = SwotAnalysis
        fields = {
            "status": ["exact"],
            "analysis_date": ["gte", "lte"],
        }


class RoleFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Role
        fields = {
            "type": ["exact"],
            "status": ["exact"],
            "is_mandatory": ["exact"],
        }


class ActivityFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = Activity
        fields = {
            "type": ["exact"],
            "criticality": ["exact"],
            "status": ["exact"],
            "owner": ["exact"],
        }
