"""Make reference field non-nullable and unique on all context models."""

from django.db import migrations, models


HISTORICAL_MODELS = [
    "HistoricalScope",
    "HistoricalSite",
    "HistoricalIssue",
    "HistoricalStakeholder",
    "HistoricalRole",
    "HistoricalSwotAnalysis",
]


def backfill_historical_nulls(apps, schema_editor):
    for hist_model_name in HISTORICAL_MODELS:
        HistModel = apps.get_model("context", hist_model_name)
        HistModel.objects.filter(reference__isnull=True).update(reference="")


class Migration(migrations.Migration):
    dependencies = [
        ("context", "0012_populate_references"),
    ]

    operations = [
        migrations.RunPython(backfill_historical_nulls, migrations.RunPython.noop),
        # Main models
        migrations.AlterField(
            model_name="scope",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="site",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="issue",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="stakeholder",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="role",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="swotanalysis",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        # Historical models
        migrations.AlterField(
            model_name="historicalscope",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalsite",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalissue",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalstakeholder",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalrole",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalswotanalysis",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
    ]
