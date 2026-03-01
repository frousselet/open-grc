"""Populate unique references for all risks items."""

from django.db import migrations


MODEL_PREFIXES = [
    ("RiskAssessment", "RA"),
    ("Risk", "RISK"),
    ("RiskTreatmentPlan", "RTP"),
    ("RiskCriteria", "RC"),
    ("Threat", "THR"),
    ("Vulnerability", "VULN"),
    ("ISO27005Risk", "I27R"),
    ("RiskAcceptance", "RACC"),
]


def populate_references(apps, schema_editor):
    for model_name, prefix in MODEL_PREFIXES:
        Model = apps.get_model("risks", model_name)
        items = Model.objects.all().order_by("created_at")
        for i, item in enumerate(items, start=1):
            item.reference = f"{prefix}-{i}"
        Model.objects.bulk_update(items, ["reference"])


def clear_references(apps, schema_editor):
    for model_name, _ in MODEL_PREFIXES:
        Model = apps.get_model("risks", model_name)
        Model.objects.filter(reference__regex=r"^[A-Z0-9]+-\d+$").update(reference=None)


class Migration(migrations.Migration):
    dependencies = [
        (
            "risks",
            "0007_historicaliso27005risk_reference_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(populate_references, clear_references),
    ]
