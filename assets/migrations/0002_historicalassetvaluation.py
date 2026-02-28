import django.db.models.deletion
import simple_history.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalAssetValuation",
            fields=[
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("evaluation_date", models.DateField(verbose_name="Date d'évaluation")),
                ("confidentiality_level", models.IntegerField(choices=[(0, "Négligeable"), (1, "Faible"), (2, "Moyen"), (3, "Élevé"), (4, "Critique")], verbose_name="Confidentialité")),
                ("integrity_level", models.IntegerField(choices=[(0, "Négligeable"), (1, "Faible"), (2, "Moyen"), (3, "Élevé"), (4, "Critique")], verbose_name="Intégrité")),
                ("availability_level", models.IntegerField(choices=[(0, "Négligeable"), (1, "Faible"), (2, "Moyen"), (3, "Élevé"), (4, "Critique")], verbose_name="Disponibilité")),
                ("justification", models.TextField(blank=True, default="", verbose_name="Justification")),
                ("context", models.TextField(blank=True, default="", verbose_name="Contexte")),
                ("created_at", models.DateTimeField(blank=True, editable=False, verbose_name="Date de création")),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_type", models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1)),
                ("essential_asset", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to="assets.essentialasset", verbose_name="Bien essentiel")),
                ("evaluated_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Évaluateur")),
                ("history_user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "historical Valorisation DIC",
                "verbose_name_plural": "historical Valorisations DIC",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
