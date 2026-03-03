from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0017_add_dashboard_show_indicator_chart"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="dashboard_indicators",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of indicator IDs pinned to the dashboard (max 10).",
                verbose_name="Dashboard indicators",
            ),
        ),
    ]
