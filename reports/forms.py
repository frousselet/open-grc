from django import forms
from django.utils.translation import gettext_lazy as _

from compliance.models import Framework


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
