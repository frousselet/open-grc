"""Make reference field non-nullable and unique on ComplianceAssessment."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0008_populate_references"),
    ]

    operations = [
        migrations.AlterField(
            model_name="complianceassessment",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Reference", blank=True),
        ),
        migrations.AlterField(
            model_name="historicalcomplianceassessment",
            name="reference",
            field=models.CharField(max_length=50, db_index=True, verbose_name="Reference", blank=True),
        ),
    ]
