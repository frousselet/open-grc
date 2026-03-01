"""Make reference field non-nullable and unique on AssetGroup."""

from django.db import migrations, models


HISTORICAL_MODELS = [
    "HistoricalAssetGroup",
]


def backfill_historical_nulls(apps, schema_editor):
    for hist_model_name in HISTORICAL_MODELS:
        HistModel = apps.get_model("assets", hist_model_name)
        HistModel.objects.filter(reference__isnull=True).update(reference="")


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0009_populate_references"),
    ]

    operations = [
        migrations.RunPython(backfill_historical_nulls, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="assetgroup",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalassetgroup",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
    ]
