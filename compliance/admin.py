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

admin.site.register(Framework)
admin.site.register(Section)
admin.site.register(Requirement)
admin.site.register(ComplianceAssessment)
admin.site.register(AssessmentResult)
admin.site.register(RequirementMapping)
admin.site.register(ComplianceActionPlan)
