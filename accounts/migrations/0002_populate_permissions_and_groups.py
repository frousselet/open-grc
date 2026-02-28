"""
Data migration: populate Permission objects from PERMISSION_REGISTRY
and create the 6 system groups with their permissions.
"""

from django.db import migrations


# Inline the registry and group definitions to keep migration self-contained.
# This avoids importing from accounts.constants which may change over time.

PERMISSION_REGISTRY = {
    "context": {
        "scope": {"actions": ["create", "read", "update", "delete"], "label": "Périmètres"},
        "scope_approve": {"actions": ["update"], "label": "Approbation des périmètres"},
        "issue": {"actions": ["create", "read", "update", "delete"], "label": "Enjeux"},
        "stakeholder": {"actions": ["create", "read", "update", "delete"], "label": "Parties intéressées"},
        "expectation": {"actions": ["create", "read", "update", "delete"], "label": "Attentes"},
        "objective": {"actions": ["create", "read", "update", "delete"], "label": "Objectifs"},
        "swot": {"actions": ["create", "read", "update", "delete"], "label": "Analyses SWOT"},
        "swot_validate": {"actions": ["update"], "label": "Validation SWOT"},
        "role": {"actions": ["create", "read", "update", "delete"], "label": "Rôles"},
        "role_assign": {"actions": ["update"], "label": "Affectation des rôles"},
        "activity": {"actions": ["create", "read", "update", "delete"], "label": "Activités"},
        "config": {"actions": ["read", "update"], "label": "Configuration du contexte"},
        "export": {"actions": ["read"], "label": "Export du contexte"},
        "audit_trail": {"actions": ["read"], "label": "Journal d'audit du contexte"},
    },
    "assets": {
        "essential_asset": {"actions": ["create", "read", "update", "delete"], "label": "Biens essentiels"},
        "essential_asset_evaluate": {"actions": ["update"], "label": "Évaluation des biens essentiels"},
        "support_asset": {"actions": ["create", "read", "update", "delete"], "label": "Biens supports"},
        "dependency": {"actions": ["create", "read", "update", "delete"], "label": "Dépendances"},
        "group": {"actions": ["create", "read", "update", "delete"], "label": "Groupes d'actifs"},
        "import": {"actions": ["create"], "label": "Import des actifs"},
        "config": {"actions": ["read", "update"], "label": "Configuration des actifs"},
        "export": {"actions": ["read"], "label": "Export des actifs"},
        "audit_trail": {"actions": ["read"], "label": "Journal d'audit des actifs"},
    },
    "system": {
        "admin_django": {"actions": ["access"], "label": "Administration Django"},
        "users": {"actions": ["create", "read", "update", "delete"], "label": "Utilisateurs"},
        "groups": {"actions": ["create", "read", "update", "delete"], "label": "Groupes"},
        "audit_trail": {"actions": ["read"], "label": "Journal d'audit système"},
        "config": {"actions": ["read", "update"], "label": "Configuration système"},
        "webhooks": {"actions": ["create", "read", "update", "delete"], "label": "Webhooks"},
        "notifications": {"actions": ["read", "update"], "label": "Notifications"},
    },
}

MODULE_LABELS = {
    "context": "Gouvernance",
    "assets": "Risques",
    "system": "Système",
}

ACTION_LABELS = {
    "create": "Créer",
    "read": "Lire",
    "update": "Modifier",
    "delete": "Supprimer",
    "access": "Accéder",
}

SYSTEM_GROUPS = {
    "Super Administrateur": {
        "description": "Administration technique complète de la plateforme. Toutes les permissions.",
        "filter": lambda codename: True,
    },
    "Administrateur": {
        "description": "Administration fonctionnelle complète. Toutes les permissions sauf l'accès à l'admin Django.",
        "filter": lambda codename: codename != "system.admin_django.access",
    },
    "RSSI / DPO": {
        "description": "Pilotage du dispositif GRC. Lecture, création, modification. Pas de suppression ni de configuration système.",
        "filter": lambda codename: (
            codename.endswith(".read")
            or codename.endswith(".create")
            or codename.endswith(".update")
            or codename.endswith(".access")
        )
        and codename != "system.admin_django.access"
        and codename != "system.config.update",
    },
    "Auditeur": {
        "description": "Consultation et audit de la plateforme. Lecture seule sur tous les modules.",
        "filter": lambda codename: codename.endswith(".read"),
    },
    "Contributeur": {
        "description": "Contribution au contenu GRC. Lecture, création, modification. Pas de suppression ni d'accès système.",
        "filter": lambda codename: (
            codename.endswith(".read")
            or codename.endswith(".create")
            or codename.endswith(".update")
        )
        and not codename.startswith("system."),
    },
    "Lecteur": {
        "description": "Consultation seule. Lecture sur tous les modules hors système.",
        "filter": lambda codename: codename.endswith(".read")
        and not codename.startswith("system."),
    },
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    # Create all permissions
    all_perms = {}
    for module, features in PERMISSION_REGISTRY.items():
        module_label = MODULE_LABELS.get(module, module)
        for feature, info in features.items():
            for action in info["actions"]:
                codename = f"{module}.{feature}.{action}"
                action_label = ACTION_LABELS.get(action, action)
                name = f"{module_label} — {info['label']} — {action_label}"
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
                all_perms[codename] = perm

    # Create system groups and assign permissions
    for group_name, group_def in SYSTEM_GROUPS.items():
        group, _ = Group.objects.get_or_create(
            name=group_name,
            defaults={
                "description": group_def["description"],
                "is_system": True,
            },
        )
        matching_perms = [
            perm for codename, perm in all_perms.items()
            if group_def["filter"](codename)
        ]
        group.permissions.set(matching_perms)


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")
    Group.objects.filter(is_system=True).delete()
    Permission.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
