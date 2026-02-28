import django.db.models.deletion
import simple_history.models
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0005_alter_scope_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Site",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Date de création")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Date de modification")),
                ("is_approved", models.BooleanField(default=True, verbose_name="Approuvé")),
                ("approved_at", models.DateTimeField(blank=True, null=True, verbose_name="Date d'approbation")),
                ("version", models.PositiveIntegerField(default=1, verbose_name="Version")),
                ("name", models.CharField(max_length=255, verbose_name="Nom")),
                ("type", models.CharField(choices=[("siege", "Siège"), ("bureau", "Bureau"), ("usine", "Usine"), ("entrepot", "Entrepôt"), ("datacenter", "Datacenter"), ("site_distant", "Site distant"), ("autre", "Autre")], default="autre", max_length=20, verbose_name="Type")),
                ("address", models.TextField(blank=True, default="", verbose_name="Adresse")),
                ("description", models.TextField(blank=True, default="", verbose_name="Description")),
                ("status", models.CharField(choices=[("draft", "Brouillon"), ("active", "Actif"), ("archived", "Archivé")], default="draft", max_length=20, verbose_name="Statut")),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_approved", to=settings.AUTH_USER_MODEL, verbose_name="Approuvé par")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL, verbose_name="Créé par")),
                ("parent_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="context.site", verbose_name="Site parent")),
            ],
            options={
                "verbose_name": "Site",
                "verbose_name_plural": "Sites",
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="HistoricalSite",
            fields=[
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("created_at", models.DateTimeField(blank=True, editable=False, verbose_name="Date de création")),
                ("updated_at", models.DateTimeField(blank=True, editable=False, verbose_name="Date de modification")),
                ("is_approved", models.BooleanField(default=True, verbose_name="Approuvé")),
                ("approved_at", models.DateTimeField(blank=True, null=True, verbose_name="Date d'approbation")),
                ("version", models.PositiveIntegerField(default=1, verbose_name="Version")),
                ("name", models.CharField(max_length=255, verbose_name="Nom")),
                ("type", models.CharField(choices=[("siege", "Siège"), ("bureau", "Bureau"), ("usine", "Usine"), ("entrepot", "Entrepôt"), ("datacenter", "Datacenter"), ("site_distant", "Site distant"), ("autre", "Autre")], default="autre", max_length=20, verbose_name="Type")),
                ("address", models.TextField(blank=True, default="", verbose_name="Adresse")),
                ("description", models.TextField(blank=True, default="", verbose_name="Description")),
                ("status", models.CharField(choices=[("draft", "Brouillon"), ("active", "Actif"), ("archived", "Archivé")], default="draft", max_length=20, verbose_name="Statut")),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_type", models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1)),
                ("approved_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Approuvé par")),
                ("created_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Créé par")),
                ("history_user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("parent_site", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to="context.site", verbose_name="Site parent")),
            ],
            options={
                "verbose_name": "historical Site",
                "verbose_name_plural": "historical Sites",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
