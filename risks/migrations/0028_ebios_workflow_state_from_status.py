"""Align EBIOS deliverable ``workflow_state`` with their ``status`` machines.

Same rationale as 0027: identity copy now that the EBIOS workshop progress,
study framework, security baseline, summary, baseline gaps and PACS measures
run their specific workflows. Historical rows included.
"""

from django.db import migrations
from django.db.models import F

MODELS = [
    "EbiosWorkshopProgress",
    "HistoricalEbiosWorkshopProgress",
    "StudyFramework",
    "HistoricalStudyFramework",
    "SecurityBaseline",
    "HistoricalSecurityBaseline",
    "EbiosSummary",
    "HistoricalEbiosSummary",
    "BaselineGap",
    "HistoricalBaselineGap",
    "PACSMeasure",
    "HistoricalPACSMeasure",
]


def copy_status_to_workflow_state(apps, schema_editor):
    for model_name in MODELS:
        apps.get_model("risks", model_name).objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    for model_name in MODELS:
        if model_name.startswith("Historical"):
            continue
        model = apps.get_model("risks", model_name)
        model.objects.filter(is_approved=True).update(workflow_state="validated")
        model.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("risks", "0027_risk_workflow_state_from_status"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
