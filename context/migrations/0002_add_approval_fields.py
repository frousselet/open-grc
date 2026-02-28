"""
Add approval fields (is_approved, approved_by, approved_at) to all context
domain models (via BaseModel) and their historical counterparts.
Remove explicit approved_by/approved_at from Scope (now inherited).
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


# Models that inherit from BaseModel and have HistoricalRecords
DOMAIN_MODELS = ["issue", "stakeholder", "objective", "swotanalysis", "role", "activity"]


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Scope: remove old explicit fields, re-add from BaseModel ──
        migrations.RemoveField(model_name="scope", name="approved_by"),
        migrations.RemoveField(model_name="scope", name="approved_at"),
        migrations.RemoveField(model_name="historicalscope", name="approved_by"),
        migrations.RemoveField(model_name="historicalscope", name="approved_at"),
        # Add new BaseModel fields to Scope + HistoricalScope
        *_add_approval_fields("scope"),
        *_add_historical_approval_fields("historicalscope"),
        # ── Other domain models ──
        *[op for m in DOMAIN_MODELS for op in _add_approval_fields(m)],
        *[op for m in DOMAIN_MODELS for op in _add_historical_approval_fields(f"historical{m}")],
    ]
