# Fix for databases where 0018 was fake-applied over stale/incomplete tables.
# Drops stale tables and recreates them with the correct schema.
# On clean databases (where 0018 ran normally), this is a no-op.

from django.db import connection, migrations


def recreate_if_schema_wrong(apps, schema_editor):
    """Drop and recreate Finding tables only if the schema is stale."""
    existing_tables = set(connection.introspection.table_names())
    if "compliance_finding" not in existing_tables:
        return

    # Use Django's introspection (works with both SQLite and PostgreSQL)
    with connection.cursor() as cursor:
        columns = {
            col.name
            for col in connection.introspection.get_table_description(
                cursor, "compliance_finding"
            )
        }

    expected_columns = {
        "id", "reference", "created_at", "updated_at", "is_approved",
        "approved_at", "version", "finding_type", "description",
        "recommendation", "evidence", "approved_by_id", "assessment_id",
        "assessor_id", "created_by_id",
    }

    if expected_columns.issubset(columns):
        # Schema is correct, nothing to do
        return

    # Schema is wrong — drop stale tables and recreate
    tables_to_drop = [
        "compliance_finding_requirements",
        "compliance_finding_tags",
        "compliance_historicalfinding",
        "compliance_finding",
    ]
    for table in tables_to_drop:
        if table in existing_tables:
            schema_editor.execute(f'DROP TABLE "{table}" CASCADE')

    Finding = apps.get_model("compliance", "Finding")
    HistoricalFinding = apps.get_model("compliance", "HistoricalFinding")
    schema_editor.create_model(Finding)
    schema_editor.create_model(HistoricalFinding)


class Migration(migrations.Migration):

    dependencies = [
        ("compliance", "0018_finding_historicalfinding"),
    ]

    operations = [
        migrations.RunPython(recreate_if_schema_wrong, migrations.RunPython.noop),
    ]
