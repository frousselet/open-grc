from django.contrib import admin

from .models import (
    ComplianceActionPlan,
    ComplianceAssessment,
    AssessmentResult,
    Framework,
    Requirement,
    RequirementMapping,
    Section,
)


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)


@admin.register(ComplianceAssessment)
class ComplianceAssessmentAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)


@admin.register(ComplianceActionPlan)
class ComplianceActionPlanAdmin(admin.ModelAdmin):
    filter_horizontal = ("tags",)


admin.site.register(Section)
admin.site.register(AssessmentResult)
admin.site.register(RequirementMapping)
