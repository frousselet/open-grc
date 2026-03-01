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

# Models whose reference field was newly added (historical records may have NULLs)
HISTORICAL_MODELS = [
    "HistoricalRiskCriteria",
    "HistoricalISO27005Risk",
    "HistoricalRiskAcceptance",
]


def populate_references(apps, schema_editor):
    for model_name, prefix in MODEL_PREFIXES:
        Model = apps.get_model("risks", model_name)
        items = list(Model.objects.all().order_by("created_at"))
        for i, item in enumerate(items, start=1):
            item.reference = f"{prefix}-{i}"
        if items:
            Model.objects.bulk_update(items, ["reference"])

    # Set NULL references in historical tables to empty string
    for hist_model_name in HISTORICAL_MODELS:
        HistModel = apps.get_model("risks", hist_model_name)
        HistModel.objects.filter(reference__isnull=True).update(reference="")


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
