"""
Data migration: add 'site' permissions (create, read, update, delete, approve)
and assign them to the appropriate system groups.
"""

from django.db import migrations


SITE_PERMISSIONS = [
    ("context.site.create", "Gouvernance — Sites — Créer", "create"),
    ("context.site.read", "Gouvernance — Sites — Lire", "read"),
    ("context.site.update", "Gouvernance — Sites — Modifier", "update"),
    ("context.site.delete", "Gouvernance — Sites — Supprimer", "delete"),
    ("context.site.approve", "Gouvernance — Sites — Approuver", "approve"),
]

# Groups filter follows SYSTEM_GROUPS logic from accounts/constants.py
GROUP_PERMISSIONS = {
    "Super Administrateur": ["create", "read", "update", "delete", "approve"],
    "Administrateur": ["create", "read", "update", "delete", "approve"],
    "RSSI / DPO": ["create", "read", "update", "approve"],
    "Auditeur": ["read"],
    "Contributeur": ["create", "read", "update"],
    "Lecteur": ["read"],
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    perms_by_action = {}
    for codename, name, action in SITE_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                "name": name,
                "module": "context",
                "feature": "site",
                "action": action,
                "is_system": True,
            },
        )
        perms_by_action[action] = perm

    for group_name, actions in GROUP_PERMISSIONS.items():
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.add(*[perms_by_action[a] for a in actions])
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [c for c, _, _ in SITE_PERMISSIONS]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_alter_permission_action"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
