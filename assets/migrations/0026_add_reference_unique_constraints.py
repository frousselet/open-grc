# Add unique constraints on reference fields.
# Split from 0025 because PostgreSQL cannot ALTER TABLE when there are
# pending trigger events from row modifications in the same transaction.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0025_assetdependency_reference_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetdependency",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, unique=True, verbose_name="Reference"
            ),
        ),
        migrations.AlterField(
            model_name="siteassetdependency",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, unique=True, verbose_name="Reference"
            ),
        ),
        migrations.AlterField(
            model_name="sitesupplierdependency",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, unique=True, verbose_name="Reference"
            ),
        ),
        migrations.AlterField(
            model_name="supplierdependency",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, unique=True, verbose_name="Reference"
            ),
        ),
        migrations.AlterField(
            model_name="suppliertype",
            name="reference",
            field=models.CharField(
                blank=True, max_length=50, unique=True, verbose_name="Reference"
            ),
        ),
    ]
