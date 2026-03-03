from django.db.models import CharField, Func


class NaturalSortKey(Func):
    """PostgreSQL function that pads all numeric sequences to 20 digits.

    This makes lexicographic ordering equivalent to natural ordering:
        'REQT-1'  → 'REQT-00000000000000000001'
        'REQT-10' → 'REQT-00000000000000000010'
        '4.1.a'   → '00000000000000000004.00000000000000000001.a'

    Requires the natural_sort_key() function in PostgreSQL
    (see helpers/migrations/0006_natural_sort_key_function.py).
    """

    function = "natural_sort_key"
    output_field = CharField()
