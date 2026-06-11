"""Backfill the new ``workflow_state`` lifecycle field from ``is_approved``.

Every existing row defaults to ``draft`` (the default lifecycle's initial state);
rows that were already approved are promoted to ``validated`` so they keep
counting in reports / KPIs / calendar once enforcement is enabled. Richer mapping
from per-model ``status`` values (e.g. archived) is handled when each model's
specific workflow is defined.
"""

from django.db import migrations


def backfill_workflow_state(apps, schema_editor):
    for model in apps.get_models():
        field_names = {f.name for f in model._meta.fields}
        if "is_approved" in field_names and "workflow_state" in field_names:
            (
                model.objects.filter(is_approved=True)
                .exclude(workflow_state="validated")
                .update(workflow_state="validated")
            )


def reverse_noop(apps, schema_editor):
    # The column is removed by reversing the schema migrations; nothing to undo here.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_versioningconfig_workflow_name"),
        ("assets", "0030_assetgroup_workflow_state_and_more"),
        ("compliance", "0036_complianceactionplan_workflow_state_and_more"),
        ("context", "0030_activity_workflow_state_and_more"),
        ("reports", "0006_historicalmanagementreview_workflow_state_and_more"),
        ("risks", "0026_attackpathstep_workflow_state_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_workflow_state, reverse_noop),
    ]
