from django import forms
from django.utils.translation import gettext_lazy as _

from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment, Framework


class SoaReportForm(forms.Form):
    frameworks = forms.ModelMultipleChoiceField(
        queryset=Framework.objects.all(),
        label=_("Frameworks"),
        help_text=_("Select one or more frameworks to include in the Statement of Applicability."),
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": 8,
        }),
    )


class AuditReportForm(forms.Form):
    assessment = forms.ModelChoiceField(
        queryset=ComplianceAssessment.objects.filter(
            status__in=[AssessmentStatus.COMPLETED, AssessmentStatus.CLOSED],
        ).order_by("-assessment_end_date", "-created_at"),
        label=_("Assessment"),
        help_text=_("Select a completed or closed audit to generate the report."),
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )
