import django_filters

from compliance.models import (
    Auditor,
    ComplianceActionPlan,
    ComplianceAssessment,
    ComplianceAudit,
    ComplianceControl,
    ControlBody,
    Finding,
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


class ComplianceControlFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scopes", lookup_expr="exact")

    class Meta:
        model = ComplianceControl
        fields = {
            "frequency": ["exact"],
            "status": ["exact"],
            "result": ["exact"],
            "owner": ["exact"],
            "support_asset": ["exact"],
            "site": ["exact"],
            "supplier": ["exact"],
        }


class ComplianceAuditFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scopes", lookup_expr="exact")
    framework = django_filters.UUIDFilter(field_name="frameworks", lookup_expr="exact")

    class Meta:
        model = ComplianceAudit
        fields = {
            "audit_type": ["exact"],
            "status": ["exact"],
            "lead_auditor": ["exact"],
            "control_body": ["exact"],
            "planned_start_date": ["gte", "lte"],
        }


class ControlBodyFilter(django_filters.FilterSet):
    framework = django_filters.UUIDFilter(field_name="frameworks", lookup_expr="exact")

    class Meta:
        model = ControlBody
        fields = {
            "is_accredited": ["exact"],
            "country": ["exact"],
        }


class AuditorFilter(django_filters.FilterSet):
    class Meta:
        model = Auditor
        fields = {
            "control_body": ["exact"],
        }


class FindingFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scopes", lookup_expr="exact")
    audit = django_filters.UUIDFilter(field_name="audit_id")
    control = django_filters.UUIDFilter(field_name="control_id")

    class Meta:
        model = Finding
        fields = {
            "finding_type": ["exact"],
            "audit": ["exact"],
            "control": ["exact"],
        }
