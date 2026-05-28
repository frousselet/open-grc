"""
Data migration: extend the risk module's approval workflow to threats,
vulnerabilities and ISO 27005 analyses. Add the three new approve
permissions and grant them to the same groups that hold the other risk
approve permissions (Super Admin, Admin, RSSI / DPO).
"""

from django.db import migrations


NEW_PERMISSIONS = [
    (
        "risks.threat.approve",
        "Gestion des risques - Menaces - Approuver",
        "risks", "threat", "approve",
    ),
    (
        "risks.vulnerability.approve",
        "Gestion des risques - Vulnerabilites - Approuver",
        "risks", "vulnerability", "approve",
    ),
    (
        "risks.iso27005.approve",
        "Gestion des risques - Analyses ISO 27005 - Approuver",
        "risks", "iso27005", "approve",
    ),
]


GROUPS_GRANTED = ["Super Administrateur", "Administrateur", "RSSI / DPO"]


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    perms = []
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
        perms.append(perm)

    for group_name in GROUPS_GRANTED:
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.add(*perms)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(
        codename__in=[c for c, _, _, _, _ in NEW_PERMISSIONS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0036_add_risk_acceptance_approve_permission"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
