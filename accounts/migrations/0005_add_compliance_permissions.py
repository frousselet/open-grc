"""
Data migration: add compliance module permissions and assign them
to the appropriate system groups.
"""

from django.db import migrations


MODULE_LABEL = "Conformité"

COMPLIANCE_FEATURES = {
    "framework": {
        "label": "Référentiels",
        "actions": ["create", "read", "update", "delete", "approve"],
    },
    "section": {
        "label": "Sections",
        "actions": ["create", "read", "update", "delete"],
    },
    "requirement": {
        "label": "Exigences",
        "actions": ["create", "read", "update", "delete", "approve", "assess"],
    },
    "assessment": {
        "label": "Évaluations de conformité",
        "actions": ["create", "read", "update", "delete", "approve", "validate"],
    },
    "mapping": {
        "label": "Mappings inter-référentiels",
        "actions": ["create", "read", "update", "delete"],
    },
    "action_plan": {
        "label": "Plans d'action",
        "actions": ["create", "read", "update", "delete", "approve"],
    },
    "config": {
        "label": "Configuration de la conformité",
        "actions": ["read", "update"],
    },
    "export": {
        "label": "Export de la conformité",
        "actions": ["read"],
    },
    "audit_trail": {
        "label": "Journal d'audit de la conformité",
        "actions": ["read"],
    },
}

ACTION_LABELS = {
    "create": "Créer",
    "read": "Lire",
    "update": "Modifier",
    "delete": "Supprimer",
    "approve": "Approuver",
    "assess": "Évaluer",
    "validate": "Valider",
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    all_perms = []
    for feature, info in COMPLIANCE_FEATURES.items():
        for action in info["actions"]:
            codename = f"compliance.{feature}.{action}"
            action_label = ACTION_LABELS.get(action, action)
            name = f"{MODULE_LABEL} — {info['label']} — {action_label}"
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": name,
                    "module": "compliance",
                    "feature": feature,
                    "action": action,
                    "is_system": True,
                },
            )
            all_perms.append(perm)

    # Assign to groups using the same logic as SYSTEM_GROUPS in constants.py
    group_filters = {
        "Super Administrateur": lambda c: True,
        "Administrateur": lambda c: c != "system.admin_django.access",
        "RSSI / DPO": lambda c: (
            c.endswith(".read")
            or c.endswith(".create")
            or c.endswith(".update")
            or c.endswith(".approve")
            or c.endswith(".assess")
            or c.endswith(".validate")
        ),
        "Auditeur": lambda c: c.endswith(".read"),
        "Contributeur": lambda c: (
            c.endswith(".read")
            or c.endswith(".create")
            or c.endswith(".update")
        ),
        "Lecteur": lambda c: c.endswith(".read"),
    }

    for group_name, filter_fn in group_filters.items():
        try:
            group = Group.objects.get(name=group_name)
            matching = [p for p in all_perms if filter_fn(p.codename)]
            group.permissions.add(*matching)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(module="compliance").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_add_approve_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
