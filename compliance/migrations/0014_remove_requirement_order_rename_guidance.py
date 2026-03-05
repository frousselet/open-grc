from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0013_requirement_reference_unique_and_constraints"),
    ]

    operations = [
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
