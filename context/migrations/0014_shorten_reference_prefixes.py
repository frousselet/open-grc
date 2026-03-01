"""Standardise all reference prefixes to exactly 4 characters."""

from django.db import migrations


# (model_name, old_prefix, new_4char_prefix)
RENAMES = [
    ("Scope", "SCOPE", "SCOP"),
    ("Scope", "SCP", "SCOP"),
    ("Issue", "ISSUE", "ISSU"),
    ("Issue", "ISS", "ISSU"),
    ("Objective", "OBJ", "OBJT"),
    ("Activity", "ACT", "ACTV"),
]

HISTORICAL_RENAMES = [
    ("HistoricalScope", "SCOPE", "SCOP"),
    ("HistoricalScope", "SCP", "SCOP"),
    ("HistoricalIssue", "ISSUE", "ISSU"),
    ("HistoricalIssue", "ISS", "ISSU"),
    ("HistoricalObjective", "OBJ", "OBJT"),
    ("HistoricalActivity", "ACT", "ACTV"),
]


def rename_prefixes(apps, schema_editor):
    for model_name, old_prefix, new_prefix in RENAMES + HISTORICAL_RENAMES:
        if old_prefix == new_prefix:
            continue
        Model = apps.get_model("context", model_name)
        old_with_dash = f"{old_prefix}-"
        for obj in Model.objects.filter(reference__startswith=old_with_dash):
            obj.reference = f"{new_prefix}-{obj.reference[len(old_with_dash):]}"
            obj.save(update_fields=["reference"])


def undo_rename(apps, schema_editor):
    # Reverse: new 4-char prefix → original prefix (first occurrence)
    originals = [
        ("Scope", "SCOP", "SCOPE"),
        ("Issue", "ISSU", "ISSUE"),
        ("Objective", "OBJT", "OBJ"),
        ("Activity", "ACTV", "ACT"),
        ("HistoricalScope", "SCOP", "SCOPE"),
        ("HistoricalIssue", "ISSU", "ISSUE"),
        ("HistoricalObjective", "OBJT", "OBJ"),
        ("HistoricalActivity", "ACTV", "ACT"),
    ]
    for model_name, new_prefix, old_prefix in originals:
        Model = apps.get_model("context", model_name)
        new_with_dash = f"{new_prefix}-"
        for obj in Model.objects.filter(reference__startswith=new_with_dash):
            obj.reference = f"{old_prefix}-{obj.reference[len(new_with_dash):]}"
            obj.save(update_fields=["reference"])


class Migration(migrations.Migration):
    dependencies = [
        ("context", "0013_add_unique_reference_constraint"),
    ]

    operations = [
        migrations.RunPython(rename_prefixes, undo_rename),
    ]
