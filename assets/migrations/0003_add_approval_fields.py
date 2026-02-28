"""
Add approval fields (is_approved, approved_by, approved_at) to all assets
domain models and their historical counterparts.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _add_approval_fields(model_name):
    """Return AddField operations for a main model."""
    return [
        migrations.AddField(
            model_name=model_name,
            name="is_approved",
            field=models.BooleanField(default=True, verbose_name="Approuvé"),
        ),
        migrations.AddField(
            model_name=model_name,
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_approved",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Approuvé par",
            ),
        ),
        migrations.AddField(
            model_name=model_name,
            name="approved_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Date d'approbation"
            ),
        ),
    ]


def _add_historical_approval_fields(model_name):
    """Return AddField operations for a historical model."""
    return [
        migrations.AddField(
            model_name=model_name,
            name="is_approved",
            field=models.BooleanField(default=True, verbose_name="Approuvé"),
        ),
        migrations.AddField(
            model_name=model_name,
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Approuvé par",
            ),
        ),
        migrations.AddField(
            model_name=model_name,
            name="approved_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Date d'approbation"
            ),
        ),
    ]


# Models that inherit from ScopedModel/BaseModel
SCOPED_MODELS = ["essentialasset", "supportasset", "assetgroup"]


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0002_historicalassetvaluation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── ScopedModel subclasses (inherit from BaseModel) ──
        *[op for m in SCOPED_MODELS for op in _add_approval_fields(m)],
        *[op for m in SCOPED_MODELS for op in _add_historical_approval_fields(f"historical{m}")],
        # ── AssetDependency (does NOT inherit BaseModel, fields added directly) ──
        migrations.AddField(
            model_name="assetdependency",
            name="is_approved",
            field=models.BooleanField(default=True, verbose_name="Approuvé"),
        ),
        migrations.AddField(
            model_name="assetdependency",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_dependencies",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Approuvé par",
            ),
        ),
        migrations.AddField(
            model_name="assetdependency",
            name="approved_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Date d'approbation"
            ),
        ),
        *_add_historical_approval_fields("historicalassetdependency"),
    ]
