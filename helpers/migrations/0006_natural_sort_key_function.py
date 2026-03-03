from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0005_english_help_content"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""\
CREATE OR REPLACE FUNCTION natural_sort_key(val text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT AS $$
  SELECT STRING_AGG(
    CASE WHEN m[1] ~ '^\\d+$' THEN LPAD(m[1], 20, '0') ELSE m[1] END,
    ''
  )
  FROM REGEXP_MATCHES(val, '(\\d+|\\D+)', 'g') AS m;
$$;
""",
            reverse_sql="DROP FUNCTION IF EXISTS natural_sort_key(text);",
        ),
    ]
