"""Populate unique references for all compliance items."""

from django.db import migrations


MODEL_PREFIXES = [
    ("Framework", "FWK"),
    ("ComplianceAssessment", "CA"),
    ("ComplianceActionPlan", "CAP"),
]


def populate_references(apps, schema_editor):
    for model_name, prefix in MODEL_PREFIXES:
        Model = apps.get_model("compliance", model_name)
        items = Model.objects.all().order_by("created_at")
        for i, item in enumerate(items, start=1):
            item.reference = f"{prefix}-{i}"
        Model.objects.bulk_update(items, ["reference"])


def clear_references(apps, schema_editor):
    for model_name, _ in MODEL_PREFIXES:
        Model = apps.get_model("compliance", model_name)
        Model.objects.filter(reference__regex=r"^[A-Z]+-\d+$").update(reference=None)


class Migration(migrations.Migration):
    dependencies = [
        (
            "compliance",
            "0007_complianceassessment_reference_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(populate_references, clear_references),
    ]
