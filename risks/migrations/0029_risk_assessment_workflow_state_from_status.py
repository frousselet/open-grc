"""Align risk assessment ``workflow_state`` with its 5-state ``status`` machine.

Identity copy now that the risk assessment runs its specific
``risk_assessment`` workflow. Historical rows included.
"""

from django.db import migrations
from django.db.models import F


def copy_status_to_workflow_state(apps, schema_editor):
    for model_name in ("RiskAssessment", "HistoricalRiskAssessment"):
        apps.get_model("risks", model_name).objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    RiskAssessment = apps.get_model("risks", "RiskAssessment")
    RiskAssessment.objects.filter(is_approved=True).update(workflow_state="validated")
    RiskAssessment.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("risks", "0028_ebios_workflow_state_from_status"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
