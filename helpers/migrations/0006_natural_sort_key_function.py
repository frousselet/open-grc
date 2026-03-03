from django.db import connection, migrations


def create_natural_sort_key(apps, schema_editor):
    if connection.vendor == "postgresql":
        schema_editor.execute("""\
CREATE OR REPLACE FUNCTION natural_sort_key(val text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT AS $$
  SELECT STRING_AGG(
    CASE WHEN m[1] ~ '^\\d+$' THEN LPAD(m[1], 20, '0') ELSE m[1] END,
    ''
  )
  FROM REGEXP_MATCHES(val, '(\\d+|\\D+)', 'g') AS m;
$$;
""")


def drop_natural_sort_key(apps, schema_editor):
    if connection.vendor == "postgresql":
        schema_editor.execute("DROP FUNCTION IF EXISTS natural_sort_key(text);")


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0005_english_help_content"),
    ]

    operations = [
        migrations.RunPython(create_natural_sort_key, drop_natural_sort_key),
    ]
