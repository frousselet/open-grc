"""
Data migration: add reports permissions (report.create, report.read, report.delete)
and assign them to system groups.
"""

from django.db import migrations


NEW_PERMISSIONS = [
    {
        "codename": "reports.report.create",
        "name": "Reports — Reports — Create",
        "module": "reports",
        "feature": "report",
        "action": "create",
    },
    {
        "codename": "reports.report.read",
        "name": "Reports — Reports — Read",
        "module": "reports",
        "feature": "report",
        "action": "read",
    },
    {
        "codename": "reports.report.delete",
        "name": "Reports — Reports — Delete",
        "module": "reports",
        "feature": "report",
        "action": "delete",
    },
]

# Assign based on SYSTEM_GROUPS filter rules in constants.py:
# - Super Admin: all permissions
# - Admin: all except system.admin_django.access
# - RSSI/DPO: read, create, access, approve (no delete, no system.config.update)
# - Auditeur: read only
# - Contributeur: read, create, update on non-system modules
# - Lecteur: read on non-system modules
GROUP_PERMISSION_MAP = {
    "Super Administrateur": [
        "reports.report.create",
        "reports.report.read",
        "reports.report.delete",
    ],
    "Administrateur": [
        "reports.report.create",
        "reports.report.read",
        "reports.report.delete",
    ],
    "RSSI / DPO": [
        "reports.report.create",
        "reports.report.read",
    ],
    "Auditeur": [
        "reports.report.read",
    ],
    "Contributeur": [
        "reports.report.create",
        "reports.report.read",
    ],
    "Lecteur": [
        "reports.report.read",
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
        ("accounts", "0023_company_settings"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
