from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_fix_dashboard_indicator_charts"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="table_preferences",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Per-view sort preferences: {view_key: {sort, order}}.",
                verbose_name="Table preferences",
            ),
        ),
    ]
