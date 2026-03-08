from django.contrib import admin

from .models import (
    Auditor,
    ComplianceActionPlan,
    ComplianceAssessment,
    ComplianceAudit,
    ComplianceControl,
    AssessmentResult,
    ControlBody,
    Finding,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    readonly_fields = ("reference",)


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    readonly_fields = ("reference",)


@admin.register(ComplianceAssessment)
class ComplianceAssessmentAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    readonly_fields = ("reference",)


@admin.register(ComplianceActionPlan)
class ComplianceActionPlanAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    readonly_fields = ("reference",)


admin.site.register(Section)
admin.site.register(AssessmentResult)
admin.site.register(RequirementMapping)


@admin.register(ComplianceControl)
class ComplianceControlAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    readonly_fields = ("reference",)


@admin.register(ComplianceAudit)
class ComplianceAuditAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags", "frameworks", "sections")
    readonly_fields = ("reference",)


@admin.register(ControlBody)
class ControlBodyAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags", "frameworks")
    readonly_fields = ("reference",)


@admin.register(Auditor)
class AuditorAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)
    readonly_fields = ("reference",)


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags", "action_plans", "activities", "requirements", "related_findings")
    readonly_fields = ("reference",)
