"""
Data migration: add MCP server and OAuth credential permissions,
and update system groups accordingly.
"""

from django.db import migrations


NEW_PERMISSIONS = [
    {
        "codename": "system.mcp.access",
        "name": "Système — Serveur MCP — Accéder",
        "module": "system",
        "feature": "mcp",
        "action": "access",
    },
    {
        "codename": "system.oauth.create",
        "name": "Système — Credentials OAuth — Créer",
        "module": "system",
        "feature": "oauth",
        "action": "create",
    },
    {
        "codename": "system.oauth.read",
        "name": "Système — Credentials OAuth — Lire",
        "module": "system",
        "feature": "oauth",
        "action": "read",
    },
    {
        "codename": "system.oauth.delete",
        "name": "Système — Credentials OAuth — Supprimer",
        "module": "system",
        "feature": "oauth",
        "action": "delete",
    },
]

# Which system groups should get which new permissions
GROUP_PERMISSION_MAP = {
    "Super Administrateur": [
        "system.mcp.access",
        "system.oauth.create",
        "system.oauth.read",
        "system.oauth.delete",
    ],
    "Administrateur": [
        "system.mcp.access",
        "system.oauth.create",
        "system.oauth.read",
        "system.oauth.delete",
    ],
    "RSSI / DPO": [
        "system.mcp.access",
        "system.oauth.create",
        "system.oauth.read",
    ],
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    # Create new permissions
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

    # Add permissions to system groups
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
        ("accounts", "0013_merge_0012_add_avatar_variants_0012_alter_accesslog_event_type_passkey"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
