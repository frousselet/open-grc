"""Standardise risk reference prefixes to exactly 4 characters."""

from django.db import migrations


RENAMES = [
    ("RiskAssessment", "RA", "RASS"),
    ("RiskTreatmentPlan", "RTP", "RTPL"),
    ("RiskCriteria", "RC", "RCRT"),
    ("Threat", "THR", "THRT"),
    ("HistoricalRiskCriteria", "RC", "RCRT"),
    ("HistoricalISO27005Risk", "I27R", "I27R"),  # already 4
    ("HistoricalRiskAcceptance", "RACC", "RACC"),  # already 4
]


def rename_prefixes(apps, schema_editor):
    for model_name, old_prefix, new_prefix in RENAMES:
        if old_prefix == new_prefix:
            continue
        Model = apps.get_model("risks", model_name)
        old_with_dash = f"{old_prefix}-"
        for obj in Model.objects.filter(reference__startswith=old_with_dash):
            obj.reference = f"{new_prefix}-{obj.reference[len(old_with_dash):]}"
            obj.save(update_fields=["reference"])


def undo_rename(apps, schema_editor):
    for model_name, old_prefix, new_prefix in RENAMES:
        if old_prefix == new_prefix:
            continue
        Model = apps.get_model("risks", model_name)
        new_with_dash = f"{new_prefix}-"
        for obj in Model.objects.filter(reference__startswith=new_with_dash):
            obj.reference = f"{old_prefix}-{obj.reference[len(new_with_dash):]}"
            obj.save(update_fields=["reference"])


class Migration(migrations.Migration):
    dependencies = [
        ("risks", "0009_add_unique_reference_constraint"),
    ]

    operations = [
        migrations.RunPython(rename_prefixes, undo_rename),
    ]
