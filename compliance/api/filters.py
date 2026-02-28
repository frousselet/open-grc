import django_filters

from compliance.models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)


class FrameworkFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scopes", lookup_expr="exact")
    compliance_level_min = django_filters.NumberFilter(
        field_name="compliance_level", lookup_expr="gte"
    )
    compliance_level_max = django_filters.NumberFilter(
        field_name="compliance_level", lookup_expr="lte"
    )

    class Meta:
        model = Framework
        fields = {
            "type": ["exact"],
            "category": ["exact"],
            "is_mandatory": ["exact"],
            "is_applicable": ["exact"],
            "status": ["exact"],
            "owner": ["exact"],
        }


class SectionFilter(django_filters.FilterSet):
    framework = django_filters.UUIDFilter(field_name="framework_id")

    class Meta:
        model = Section
        fields = {
            "framework": ["exact"],
        }


class RequirementFilter(django_filters.FilterSet):
    framework = django_filters.UUIDFilter(field_name="framework_id")
    section = django_filters.UUIDFilter(field_name="section_id")
    compliance_level_min = django_filters.NumberFilter(
        field_name="compliance_level", lookup_expr="gte"
    )
    compliance_level_max = django_filters.NumberFilter(
        field_name="compliance_level", lookup_expr="lte"
    )

    class Meta:
        model = Requirement
        fields = {
            "type": ["exact"],
            "category": ["exact"],
            "is_applicable": ["exact"],
            "compliance_status": ["exact"],
            "priority": ["exact"],
            "owner": ["exact"],
            "status": ["exact"],
        }


class ComplianceAssessmentFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")
    framework = django_filters.UUIDFilter(field_name="framework_id")

    class Meta:
        model = ComplianceAssessment
        fields = {
            "status": ["exact"],
            "assessor": ["exact"],
            "assessment_date": ["gte", "lte"],
        }


class RequirementMappingFilter(django_filters.FilterSet):
    source_framework = django_filters.UUIDFilter(
        field_name="source_requirement__framework_id"
    )
    target_framework = django_filters.UUIDFilter(
        field_name="target_requirement__framework_id"
    )

    class Meta:
        model = RequirementMapping
        fields = {
            "mapping_type": ["exact"],
            "coverage_level": ["exact"],
        }


class ComplianceActionPlanFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")
    framework = django_filters.UUIDFilter(
        field_name="requirement__framework_id"
    )
    requirement = django_filters.UUIDFilter(field_name="requirement_id")
    assessment = django_filters.UUIDFilter(field_name="assessment_id")

    class Meta:
        model = ComplianceActionPlan
        fields = {
            "priority": ["exact"],
            "owner": ["exact"],
            "status": ["exact"],
        }
