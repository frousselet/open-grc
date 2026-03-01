"""Make reference field non-nullable and unique on AssetGroup."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0009_populate_references"),
    ]

    operations = [
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
