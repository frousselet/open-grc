"""
Data migration: add 'approve' permissions for all domain features and
assign them to the appropriate system groups (Super Admin, Admin, RSSI/DPO).
Also removes the old scope_approve and swot_validate permissions.
"""

from django.db import migrations


MODULE_LABELS = {
    "context": "Gouvernance",
    "assets": "Risques",
}

# Features that get the new 'approve' action
APPROVE_FEATURES = {
    "context": {
        "scope": "Périmètres",
        "issue": "Enjeux",
        "stakeholder": "Parties intéressées",
        "objective": "Objectifs",
        "swot": "Analyses SWOT",
        "role": "Rôles",
        "activity": "Activités",
    },
    "assets": {
        "essential_asset": "Biens essentiels",
        "support_asset": "Biens supports",
        "dependency": "Dépendances",
        "group": "Groupes d'actifs",
    },
}

# Old permissions to remove (replaced by the new generic approve)
OLD_PERMISSIONS = [
    "context.scope_approve.update",
    "context.swot_validate.update",
]

# Groups that should get the approve permissions
GROUPS_WITH_APPROVE = [
    "Super Administrateur",
    "Administrateur",
    "RSSI / DPO",
]


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    # Remove old permissions
    Permission.objects.filter(codename__in=OLD_PERMISSIONS).delete()

    # Create new approve permissions
    new_perms = []
    for module, features in APPROVE_FEATURES.items():
        module_label = MODULE_LABELS[module]
        for feature, feature_label in features.items():
            codename = f"{module}.{feature}.approve"
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": f"{module_label} — {feature_label} — Approuver",
                    "module": module,
                    "feature": feature,
                    "action": "approve",
                    "is_system": True,
                },
            )
            new_perms.append(perm)

    # Assign to appropriate groups
    for group_name in GROUPS_WITH_APPROVE:
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.add(*new_perms)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    # Remove the approve permissions
    for module, features in APPROVE_FEATURES.items():
        for feature in features:
            Permission.objects.filter(codename=f"{module}.{feature}.approve").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_group_allowed_scopes"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
