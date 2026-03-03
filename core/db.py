from django.db import connection
from django.db.models import CharField, Func
from django.db.models.expressions import Col


class NaturalSortKey(Func):
    """PostgreSQL function that pads all numeric sequences to 20 digits.

    This makes lexicographic ordering equivalent to natural ordering:
        'REQT-1'  → 'REQT-00000000000000000001'
        'REQT-10' → 'REQT-00000000000000000010'
        '4.1.a'   → '00000000000000000004.00000000000000000001.a'

    Requires the natural_sort_key() function in PostgreSQL
    (see helpers/migrations/0006_natural_sort_key_function.py).

    On non-PostgreSQL backends (e.g. SQLite) it falls back to the raw
    column value, so ordering still works but is purely lexicographic.
    """

    function = "natural_sort_key"
    output_field = CharField()

    def as_sql(self, compiler, connection, **extra_context):
        if connection.vendor != "postgresql":
            # Fallback: just return the inner expression as-is
            return self.source_expressions[0].as_sql(compiler, connection)
        return super().as_sql(compiler, connection, **extra_context)
