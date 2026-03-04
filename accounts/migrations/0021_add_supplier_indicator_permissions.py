"""
Data migration: add supplier, supplier_dependency, and indicator permissions
and assign them to the appropriate system groups.
"""

from django.db import migrations


NEW_PERMISSIONS = [
    # assets.supplier
    ("assets.supplier.create", "Actifs — Fournisseurs — Créer", "assets", "supplier", "create"),
    ("assets.supplier.read", "Actifs — Fournisseurs — Lire", "assets", "supplier", "read"),
    ("assets.supplier.update", "Actifs — Fournisseurs — Modifier", "assets", "supplier", "update"),
    ("assets.supplier.delete", "Actifs — Fournisseurs — Supprimer", "assets", "supplier", "delete"),
    ("assets.supplier.approve", "Actifs — Fournisseurs — Approuver", "assets", "supplier", "approve"),
    # assets.supplier_dependency
    ("assets.supplier_dependency.create", "Actifs — Dépendances fournisseurs — Créer", "assets", "supplier_dependency", "create"),
    ("assets.supplier_dependency.read", "Actifs — Dépendances fournisseurs — Lire", "assets", "supplier_dependency", "read"),
    ("assets.supplier_dependency.update", "Actifs — Dépendances fournisseurs — Modifier", "assets", "supplier_dependency", "update"),
    ("assets.supplier_dependency.delete", "Actifs — Dépendances fournisseurs — Supprimer", "assets", "supplier_dependency", "delete"),
    ("assets.supplier_dependency.approve", "Actifs — Dépendances fournisseurs — Approuver", "assets", "supplier_dependency", "approve"),
    # context.indicator
    ("context.indicator.create", "Gouvernance — Indicateurs — Créer", "context", "indicator", "create"),
    ("context.indicator.read", "Gouvernance — Indicateurs — Lire", "context", "indicator", "read"),
    ("context.indicator.update", "Gouvernance — Indicateurs — Modifier", "context", "indicator", "update"),
    ("context.indicator.delete", "Gouvernance — Indicateurs — Supprimer", "context", "indicator", "delete"),
    ("context.indicator.approve", "Gouvernance — Indicateurs — Approuver", "context", "indicator", "approve"),
]

# Groups filter follows SYSTEM_GROUPS logic from accounts/constants.py
GROUP_FILTERS = {
    "Super Administrateur": lambda codename: True,
    "Administrateur": lambda codename: True,
    "RSSI / DPO": lambda codename: (
        codename.endswith(".read")
        or codename.endswith(".create")
        or codename.endswith(".update")
        or codename.endswith(".approve")
    ),
    "Auditeur": lambda codename: codename.endswith(".read"),
    "Contributeur": lambda codename: (
        codename.endswith(".read")
        or codename.endswith(".create")
        or codename.endswith(".update")
    ),
    "Lecteur": lambda codename: codename.endswith(".read"),
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    all_perms = []
    for codename, name, module, feature, action in NEW_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                "name": name,
                "module": module,
                "feature": feature,
                "action": action,
                "is_system": True,
            },
        )
        all_perms.append(perm)

    for group_name, filter_fn in GROUP_FILTERS.items():
        try:
            group = Group.objects.get(name=group_name)
            matching = [p for p in all_perms if filter_fn(p.codename)]
            group.permissions.add(*matching)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [c for c, _, _, _, _ in NEW_PERMISSIONS]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_add_table_preferences"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
