from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_add_dashboard_indicators"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="dashboard_show_indicator_chart",
            field=models.BooleanField(
                default=False,
                help_text="Display the indicator evolution chart on the dashboard.",
                verbose_name="Show indicator chart",
            ),
        ),
    ]
