from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0013_requirement_reference_unique_and_constraints"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="assessmentresult",
            options={
                "ordering": ["requirement__requirement_number"],
                "verbose_name": "Assessment result",
                "verbose_name_plural": "Assessment results",
            },
        ),
        migrations.RemoveField(
            model_name="requirement",
            name="order",
        ),
        migrations.RemoveField(
            model_name="historicalrequirement",
            name="order",
        ),
        migrations.AlterField(
            model_name="requirement",
            name="guidance",
            field=models.TextField(
                blank=True,
                default="",
                verbose_name="Implementation recommendations",
            ),
        ),
        migrations.AlterField(
            model_name="historicalrequirement",
            name="guidance",
            field=models.TextField(
                blank=True,
                default="",
                verbose_name="Implementation recommendations",
            ),
        ),
    ]
