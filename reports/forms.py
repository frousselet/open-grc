from django import forms
from django.utils.translation import gettext_lazy as _

from compliance.constants import AssessmentStatus
from compliance.models import ComplianceAssessment, Framework
from context.models import Scope


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


class ManagementReviewForm(forms.Form):
    FORMAT_CHOICES = [
        ("pptx", _("Presentation (PowerPoint)")),
        ("docx", _("Meeting minutes (Word)")),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        label=_("Format"),
        initial="pptx",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    period_start = forms.DateField(
        label=_("Period start"),
        required=False,
        help_text=_("Start of the review period. Leave empty to include all past data."),
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )
    period_end = forms.DateField(
        label=_("Period end"),
        required=False,
        help_text=_("End of the review period. Defaults to today."),
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )

    scopes = forms.ModelMultipleChoiceField(
        queryset=Scope.objects.filter(status="active").order_by("name"),
        label=_("Scopes"),
        required=False,
        help_text=_("Optionally filter data by scope. Leave empty to include all data."),
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": 6,
        }),
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and start > end:
            raise forms.ValidationError(
                _("The period start date must be before the end date.")
            )
        return cleaned
