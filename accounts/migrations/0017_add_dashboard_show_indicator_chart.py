from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_add_dashboard_indicators"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="dashboard_indicator_charts",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of indicator IDs whose sparkline is visible on the dashboard.",
                verbose_name="Indicator charts",
            ),
        ),
    ]
