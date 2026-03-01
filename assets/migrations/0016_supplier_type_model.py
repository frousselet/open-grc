import django.db.models.deletion
from django.db import migrations, models


# Old enum values → human-readable names for seeding SupplierType records
LEGACY_TYPE_NAMES = {
    "cloud_provider": "Cloud provider",
    "software_vendor": "Software vendor",
    "hardware_vendor": "Hardware vendor",
    "consulting": "Consulting",
    "managed_services": "Managed services",
    "telecommunications": "Telecommunications",
    "outsourcing": "Outsourcing",
    "other": "Other",
}


def migrate_supplier_types(apps, schema_editor):
    """Create SupplierType records from existing type values and link suppliers."""
    Supplier = apps.get_model("assets", "Supplier")
    HistoricalSupplier = apps.get_model("assets", "HistoricalSupplier")
    SupplierType = apps.get_model("assets", "SupplierType")

    distinct_types = set(
        Supplier.objects.exclude(type_legacy="")
        .exclude(type_legacy__isnull=True)
        .values_list("type_legacy", flat=True)
        .distinct()
    )
    distinct_types |= set(
        HistoricalSupplier.objects.exclude(type_legacy="")
        .exclude(type_legacy__isnull=True)
        .values_list("type_legacy", flat=True)
        .distinct()
    )

    type_map = {}
    for type_key in distinct_types:
        name = LEGACY_TYPE_NAMES.get(type_key, type_key)
        st, _ = SupplierType.objects.get_or_create(name=name)
        type_map[type_key] = st

    for type_key, st in type_map.items():
        Supplier.objects.filter(type_legacy=type_key).update(type=st)
        HistoricalSupplier.objects.filter(type_legacy=type_key).update(type=st)


def reverse_supplier_types(apps, schema_editor):
    """Reverse: copy FK name back to legacy CharField."""
    Supplier = apps.get_model("assets", "Supplier")
    HistoricalSupplier = apps.get_model("assets", "HistoricalSupplier")

    # Build reverse map from SupplierType name → legacy key
    reverse_map = {v: k for k, v in LEGACY_TYPE_NAMES.items()}

    for model in (Supplier, HistoricalSupplier):
        for obj in model.objects.select_related("type").exclude(type__isnull=True):
            obj.type_legacy = reverse_map.get(obj.type.name, obj.type.name)
            obj.save(update_fields=["type_legacy"])


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0015_supplier_dependency_spof"),
    ]

    operations = [
        # 1. Create SupplierType model
        migrations.CreateModel(
            name="SupplierType",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "name",
                    models.CharField(
                        max_length=255, unique=True, verbose_name="Name"
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, default="", verbose_name="Description"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created at"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
            ],
            options={
                "verbose_name": "Supplier type",
                "verbose_name_plural": "Supplier types",
                "ordering": ["name"],
            },
        ),
        # 2. Rename old CharField type → type_legacy
        migrations.RenameField(
            model_name="supplier",
            old_name="type",
            new_name="type_legacy",
        ),
        migrations.RenameField(
            model_name="historicalsupplier",
            old_name="type",
            new_name="type_legacy",
        ),
        # 3. Add new FK type field
        migrations.AddField(
            model_name="supplier",
            name="type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="suppliers",
                to="assets.suppliertype",
                verbose_name="Type",
            ),
        ),
        migrations.AddField(
            model_name="historicalsupplier",
            name="type",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="assets.suppliertype",
                verbose_name="Type",
            ),
        ),
        # 4. Migrate data: create SupplierType records from old values
        migrations.RunPython(migrate_supplier_types, reverse_supplier_types),
        # 5. Remove legacy field
        migrations.RemoveField(
            model_name="supplier",
            name="type_legacy",
        ),
        migrations.RemoveField(
            model_name="historicalsupplier",
            name="type_legacy",
        ),
    ]
