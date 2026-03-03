from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_add_dismissed_helpers"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="dashboard_indicators",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of indicator IDs pinned to the dashboard (max 6).",
                verbose_name="Dashboard indicators",
            ),
        ),
    ]
