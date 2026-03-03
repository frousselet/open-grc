from django.db import migrations


class Migration(migrations.Migration):
    """Fix-up: ensure dashboard_indicator_charts column exists and clean up
    the old dashboard_show_indicator_chart column if it was created by the
    original version of migration 0017."""

    dependencies = [
        ("accounts", "0017_add_dashboard_show_indicator_chart"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user ADD COLUMN IF NOT EXISTS dashboard_indicator_charts jsonb NOT NULL DEFAULT '[]';",
            reverse_sql="ALTER TABLE accounts_user DROP COLUMN IF EXISTS dashboard_indicator_charts;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE accounts_user DROP COLUMN IF EXISTS dashboard_show_indicator_chart;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
