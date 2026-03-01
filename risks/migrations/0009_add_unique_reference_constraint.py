"""Make reference field non-nullable and unique on RiskCriteria, ISO27005Risk, RiskAcceptance."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("risks", "0008_populate_references"),
    ]

    operations = [
        migrations.AlterField(
            model_name="riskcriteria",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="iso27005risk",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="riskacceptance",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalriskcriteria",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicaliso27005risk",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalriskacceptance",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
    ]
