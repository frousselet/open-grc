"""
Add version (PositiveIntegerField, default=1) to all context domain models
(via BaseModel) and their historical counterparts.
Remove the old CharField version from Scope (replaced by the integer version
inherited from BaseModel).
"""

from django.db import migrations, models


# All context domain models that inherit from BaseModel
DOMAIN_MODELS = [
    "scope", "issue", "stakeholder", "objective",
    "swotanalysis", "role", "activity",
]


def _add_version_field(model_name):
    return migrations.AddField(
        model_name=model_name,
        name="version",
        field=models.PositiveIntegerField(default=1, verbose_name="Version"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0002_add_approval_fields"),
    ]

    operations = [
        # ── Scope: remove old CharField version ──
        migrations.RemoveField(model_name="scope", name="version"),
        migrations.RemoveField(model_name="historicalscope", name="version"),
        # ── Add integer version to all domain models + historical ──
        *[_add_version_field(m) for m in DOMAIN_MODELS],
        *[_add_version_field(f"historical{m}") for m in DOMAIN_MODELS],
    ]
