"""
Rename SupportAsset.version -> software_version (represents software/firmware
version, not the document version).
Add version (PositiveIntegerField, default=1) to all assets domain models
and their historical counterparts.
"""

from django.db import migrations, models


# All assets models that inherit from ScopedModel/BaseModel
SCOPED_MODELS = ["essentialasset", "supportasset", "assetgroup"]


def _add_version_field(model_name):
    return migrations.AddField(
        model_name=model_name,
        name="version",
        field=models.PositiveIntegerField(default=1, verbose_name="Version"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0003_add_approval_fields"),
    ]

    operations = [
        # ── SupportAsset: rename version -> software_version ──
        migrations.RenameField(
            model_name="supportasset",
            old_name="version",
            new_name="software_version",
        ),
        migrations.RenameField(
            model_name="historicalsupportasset",
            old_name="version",
            new_name="software_version",
        ),
        # Update verbose_name after rename
        migrations.AlterField(
            model_name="supportasset",
            name="software_version",
            field=models.CharField(
                "Version logicielle", max_length=100, blank=True, default=""
            ),
        ),
        migrations.AlterField(
            model_name="historicalsupportasset",
            name="software_version",
            field=models.CharField(
                "Version logicielle", max_length=100, blank=True, default=""
            ),
        ),
        # ── Add integer version to all scoped models + historical ──
        *[_add_version_field(m) for m in SCOPED_MODELS],
        *[_add_version_field(f"historical{m}") for m in SCOPED_MODELS],
        # ── AssetDependency (does NOT inherit BaseModel) ──
        _add_version_field("assetdependency"),
        _add_version_field("historicalassetdependency"),
    ]
