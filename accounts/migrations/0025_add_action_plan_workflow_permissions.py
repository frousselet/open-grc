"""
Data migration: add action plan workflow permissions
(validate, implement, close, cancel) and assign to system groups.
"""

from django.db import migrations


NEW_PERMISSIONS = [
    {
        "codename": "compliance.action_plan.validate",
        "name": "Compliance — Action plans — Validate",
        "module": "compliance",
        "feature": "action_plan",
        "action": "validate",
    },
    {
        "codename": "compliance.action_plan.implement",
        "name": "Compliance — Action plans — Implement",
        "module": "compliance",
        "feature": "action_plan",
        "action": "implement",
    },
    {
        "codename": "compliance.action_plan.close",
        "name": "Compliance — Action plans — Close",
        "module": "compliance",
        "feature": "action_plan",
        "action": "close",
    },
    {
        "codename": "compliance.action_plan.cancel",
        "name": "Compliance — Action plans — Cancel",
        "module": "compliance",
        "feature": "action_plan",
        "action": "cancel",
    },
]

GROUP_PERMISSION_MAP = {
    "Super Administrateur": [
        "compliance.action_plan.validate",
        "compliance.action_plan.implement",
        "compliance.action_plan.close",
        "compliance.action_plan.cancel",
    ],
    "Administrateur": [
        "compliance.action_plan.validate",
        "compliance.action_plan.implement",
        "compliance.action_plan.close",
        "compliance.action_plan.cancel",
    ],
    "RSSI / DPO": [
        "compliance.action_plan.validate",
        "compliance.action_plan.close",
        "compliance.action_plan.cancel",
    ],
    "Contributeur": [
        "compliance.action_plan.implement",
    ],
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
        ("accounts", "0024_add_reports_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
