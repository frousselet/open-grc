from django.db import models


class PermissionAction(models.TextChoices):
    CREATE = "create", "Créer"
    READ = "read", "Lire"
    UPDATE = "update", "Modifier"
    DELETE = "delete", "Supprimer"
    ACCESS = "access", "Accéder"
    APPROVE = "approve", "Approuver"


class AccessEventType(models.TextChoices):
    LOGIN_SUCCESS = "login_success", "Connexion réussie"
    LOGIN_FAILED = "login_failed", "Connexion échouée"
    LOGOUT = "logout", "Déconnexion"
    TOKEN_REFRESH = "token_refresh", "Rafraîchissement de token"
    PASSWORD_CHANGE = "password_change", "Changement de mot de passe"
    ACCOUNT_LOCKED = "account_locked", "Compte verrouillé"
    ACCOUNT_UNLOCKED = "account_unlocked", "Compte déverrouillé"


class FailureReason(models.TextChoices):
    INVALID_PASSWORD = "invalid_password", "Mot de passe invalide"
    ACCOUNT_LOCKED = "account_locked", "Compte verrouillé"
    ACCOUNT_INACTIVE = "account_inactive", "Compte inactif"
    USER_NOT_FOUND = "user_not_found", "Utilisateur introuvable"


# Lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Permission registry: module -> feature -> list of actions
# Each entry generates Permission objects in the data migration.
PERMISSION_REGISTRY = {
    "context": {
        "scope": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Périmètres",
        },
        "issue": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Enjeux",
        },
        "stakeholder": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Parties intéressées",
        },
        "expectation": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Attentes",
        },
        "objective": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Objectifs",
        },
        "swot": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Analyses SWOT",
        },
        "role": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Rôles",
        },
        "role_assign": {
            "actions": ["update"],
            "label": "Affectation des rôles",
        },
        "activity": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Activités",
        },
        "site": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Sites",
        },
        "config": {
            "actions": ["read", "update"],
            "label": "Configuration du contexte",
        },
        "export": {
            "actions": ["read"],
            "label": "Export du contexte",
        },
        "audit_trail": {
            "actions": ["read"],
            "label": "Journal d'audit du contexte",
        },
    },
    "assets": {
        "essential_asset": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Biens essentiels",
        },
        "essential_asset_evaluate": {
            "actions": ["update"],
            "label": "Évaluation des biens essentiels",
        },
        "support_asset": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Biens supports",
        },
        "dependency": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Dépendances",
        },
        "group": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Groupes d'actifs",
        },
        "import": {
            "actions": ["create"],
            "label": "Import des actifs",
        },
        "config": {
            "actions": ["read", "update"],
            "label": "Configuration des actifs",
        },
        "export": {
            "actions": ["read"],
            "label": "Export des actifs",
        },
        "audit_trail": {
            "actions": ["read"],
            "label": "Journal d'audit des actifs",
        },
    },
    "compliance": {
        "framework": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Référentiels",
        },
        "section": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Sections",
        },
        "requirement": {
            "actions": ["create", "read", "update", "delete", "approve", "assess"],
            "label": "Exigences",
        },
        "assessment": {
            "actions": ["create", "read", "update", "delete", "approve", "validate"],
            "label": "Évaluations de conformité",
        },
        "mapping": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Mappings inter-référentiels",
        },
        "action_plan": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Plans d'action",
        },
        "config": {
            "actions": ["read", "update"],
            "label": "Configuration de la conformité",
        },
        "export": {
            "actions": ["read"],
            "label": "Export de la conformité",
        },
        "audit_trail": {
            "actions": ["read"],
            "label": "Journal d'audit de la conformité",
        },
    },
    "risks": {
        "assessment": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Appréciations des risques",
        },
        "criteria": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Critères de risque",
        },
        "risk": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Registre des risques",
        },
        "treatment": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": "Plans de traitement",
        },
        "acceptance": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Acceptations de risque",
        },
        "threat": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Menaces",
        },
        "vulnerability": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Vulnérabilités",
        },
        "iso27005": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Analyses ISO 27005",
        },
        "export": {
            "actions": ["read"],
            "label": "Export des risques",
        },
        "audit_trail": {
            "actions": ["read"],
            "label": "Journal d'audit des risques",
        },
    },
    "system": {
        "admin_django": {
            "actions": ["access"],
            "label": "Administration Django",
        },
        "users": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Utilisateurs",
        },
        "groups": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Groupes",
        },
        "audit_trail": {
            "actions": ["read"],
            "label": "Journal d'audit système",
        },
        "config": {
            "actions": ["read", "update"],
            "label": "Configuration système",
        },
        "webhooks": {
            "actions": ["create", "read", "update", "delete"],
            "label": "Webhooks",
        },
        "notifications": {
            "actions": ["read", "update"],
            "label": "Notifications",
        },
    },
}

# Action labels for display
ACTION_LABELS = {
    "create": "Créer",
    "read": "Lire",
    "update": "Modifier",
    "delete": "Supprimer",
    "access": "Accéder",
    "approve": "Approuver",
    "assess": "Évaluer",
    "validate": "Valider",
}

# Module labels for display
MODULE_LABELS = {
    "context": "Gouvernance",
    "assets": "Actifs",
    "risks": "Gestion des risques",
    "compliance": "Conformité",
    "system": "Système",
}


def _build_permission_name(module, feature, action):
    """Build a human-readable permission name."""
    module_label = MODULE_LABELS.get(module, module)
    feature_info = PERMISSION_REGISTRY.get(module, {}).get(feature, {})
    feature_label = feature_info.get("label", feature)
    action_label = ACTION_LABELS.get(action, action)
    return f"{module_label} — {feature_label} — {action_label}"


def get_all_permissions():
    """Yield (codename, name, module, feature, action) for every registered permission."""
    for module, features in PERMISSION_REGISTRY.items():
        for feature, info in features.items():
            for action in info["actions"]:
                codename = f"{module}.{feature}.{action}"
                name = _build_permission_name(module, feature, action)
                yield codename, name, module, feature, action


# System groups definition: name -> description + permission filter function
SYSTEM_GROUPS = {
    "Super Administrateur": {
        "description": "Administration technique complète de la plateforme. Toutes les permissions.",
        "filter": lambda codename: True,  # all permissions
    },
    "Administrateur": {
        "description": "Administration fonctionnelle complète. Toutes les permissions sauf l'accès à l'admin Django.",
        "filter": lambda codename: codename != "system.admin_django.access",
    },
    "RSSI / DPO": {
        "description": "Pilotage du dispositif GRC. Lecture, création, modification, approbation. Pas de suppression ni de configuration système.",
        "filter": lambda codename: (
            codename.endswith(".read")
            or codename.endswith(".create")
            or codename.endswith(".update")
            or codename.endswith(".approve")
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
