"""Populate unique references for all context items."""

from django.db import migrations


MODEL_PREFIXES = [
    ("Scope", "SCOPE"),
    ("Site", "SITE"),
    ("Issue", "ISSUE"),
    ("Stakeholder", "STKH"),
    ("Objective", "OBJ"),
    ("Activity", "ACT"),
    ("Role", "ROLE"),
    ("SwotAnalysis", "SWOT"),
]


def populate_references(apps, schema_editor):
    for model_name, prefix in MODEL_PREFIXES:
        Model = apps.get_model("context", model_name)
        items = Model.objects.all().order_by("created_at")
        for i, item in enumerate(items, start=1):
            item.reference = f"{prefix}-{i}"
        Model.objects.bulk_update(items, ["reference"])


def clear_references(apps, schema_editor):
    for model_name, _ in MODEL_PREFIXES:
        Model = apps.get_model("context", model_name)
        Model.objects.all().update(reference=None)


class Migration(migrations.Migration):
    dependencies = [
        (
            "context",
            "0011_historicalissue_reference_historicalrole_reference_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(populate_references, clear_references),
    ]
