"""
Data migration: add system.users.impersonate permission
and assign to Super Administrateur and Administrateur groups.
"""

from django.db import migrations


NEW_PERMISSIONS = [
    {
        "codename": "system.users.impersonate",
        "name": "System — Users — Impersonate",
        "module": "system",
        "feature": "users",
        "action": "impersonate",
    },
]

GROUP_PERMISSION_MAP = {
    "Super Administrateur": ["system.users.impersonate"],
    "Administrateur": ["system.users.impersonate"],
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    perm_objects = {}
    for perm_data in NEW_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=perm_data["codename"],
            defaults={
                "name": perm_data["name"],
                "module": perm_data["module"],
                "feature": perm_data["feature"],
                "action": perm_data["action"],
                "is_system": True,
            },
        )
        perm_objects[perm_data["codename"]] = perm

    for group_name, codenames in GROUP_PERMISSION_MAP.items():
        try:
            group = Group.objects.get(name=group_name, is_system=True)
            perms_to_add = [perm_objects[c] for c in codenames if c in perm_objects]
            group.permissions.add(*perms_to_add)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [p["codename"] for p in NEW_PERMISSIONS]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0030_calendar_token_model"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
