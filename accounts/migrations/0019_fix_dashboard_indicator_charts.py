from django.db import migrations


def fix_dashboard_columns(apps, schema_editor):
    """Clean up the old dashboard_show_indicator_chart column if it was
    created by the original version of migration 0017."""
    connection = schema_editor.connection
    # Introspect actual columns on the table
    with connection.cursor() as cursor:
        columns = [
            col.name
            for col in connection.introspection.get_table_description(
                cursor, "accounts_user"
            )
        ]

    # Drop the stale column if it exists
    if "dashboard_show_indicator_chart" in columns:
        schema_editor.execute(
            "ALTER TABLE accounts_user DROP COLUMN dashboard_show_indicator_chart;"
        )


class Migration(migrations.Migration):
    """Fix-up: clean up the old dashboard_show_indicator_chart column if it
    was created by the original version of migration 0017."""

    dependencies = [
        ("accounts", "0018_alter_user_dashboard_indicators"),
    ]

    operations = [
        migrations.RunPython(fix_dashboard_columns, migrations.RunPython.noop),
    ]
