"""
Data migration: add create and delete actions for assets.config permissions.

These permissions are needed for MCP tools that manage SupplierType and
SupplierTypeRequirement entities.
"""

from django.db import migrations


NEW_PERMISSIONS = [
    ("assets.config.create", "Actifs \u2014 Configuration \u2014 Cr\u00e9er", "assets", "config", "create"),
    ("assets.config.delete", "Actifs \u2014 Configuration \u2014 Supprimer", "assets", "config", "delete"),
]

GROUP_FILTERS = {
    "Super Administrateur": lambda codename: True,
    "Administrateur": lambda codename: True,
    "RSSI / DPO": lambda codename: codename.endswith(".create"),
    "Contributeur": lambda codename: codename.endswith(".create"),
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
        ("accounts", "0032_add_user_type"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
