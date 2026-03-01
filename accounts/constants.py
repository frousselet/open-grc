from django.db import models
from django.utils.translation import gettext_lazy as _


class PermissionAction(models.TextChoices):
    CREATE = "create", _("Create")
    READ = "read", _("Read")
    UPDATE = "update", _("Update")
    DELETE = "delete", _("Delete")
    ACCESS = "access", _("Access")
    APPROVE = "approve", _("Approve")


class AccessEventType(models.TextChoices):
    LOGIN_SUCCESS = "login_success", _("Successful login")
    LOGIN_FAILED = "login_failed", _("Failed login")
    LOGOUT = "logout", _("Logout")
    TOKEN_REFRESH = "token_refresh", _("Token refresh")
    PASSWORD_CHANGE = "password_change", _("Password change")
    ACCOUNT_LOCKED = "account_locked", _("Account locked")
    ACCOUNT_UNLOCKED = "account_unlocked", _("Account unlocked")


class FailureReason(models.TextChoices):
    INVALID_PASSWORD = "invalid_password", _("Invalid password")
    ACCOUNT_LOCKED = "account_locked", _("Account locked")
    ACCOUNT_INACTIVE = "account_inactive", _("Inactive account")
    USER_NOT_FOUND = "user_not_found", _("User not found")


# Lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Permission registry: module -> feature -> list of actions
# Each entry generates Permission objects in the data migration.
PERMISSION_REGISTRY = {
    "context": {
        "scope": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Scopes"),
        },
        "issue": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Issues"),
        },
        "stakeholder": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Stakeholders"),
        },
        "expectation": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Expectations"),
        },
        "objective": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Objectives"),
        },
        "swot": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("SWOT analyses"),
        },
        "role": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Roles"),
        },
        "role_assign": {
            "actions": ["update"],
            "label": _("Role assignment"),
        },
        "activity": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Activities"),
        },
        "site": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Sites"),
        },
        "config": {
            "actions": ["read", "update"],
            "label": _("Context configuration"),
        },
        "export": {
            "actions": ["read"],
            "label": _("Context export"),
        },
        "audit_trail": {
            "actions": ["read"],
            "label": _("Context audit trail"),
        },
    },
    "assets": {
        "essential_asset": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Essential assets"),
        },
        "essential_asset_evaluate": {
            "actions": ["update"],
            "label": _("Essential asset evaluation"),
        },
        "support_asset": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Support assets"),
        },
        "dependency": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Dependencies"),
        },
        "group": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Asset groups"),
        },
        "supplier": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Suppliers"),
        },
        "supplier_dependency": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Supplier dependencies"),
        },
        "import": {
            "actions": ["create"],
            "label": _("Asset import"),
        },
        "config": {
            "actions": ["read", "update"],
            "label": _("Asset configuration"),
        },
        "export": {
            "actions": ["read"],
            "label": _("Asset export"),
        },
        "audit_trail": {
            "actions": ["read"],
            "label": _("Asset audit trail"),
        },
    },
    "compliance": {
        "framework": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Frameworks"),
        },
        "section": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Sections"),
        },
        "requirement": {
            "actions": ["create", "read", "update", "delete", "approve", "assess"],
            "label": _("Requirements"),
        },
        "assessment": {
            "actions": ["create", "read", "update", "delete", "approve", "validate"],
            "label": _("Compliance assessments"),
        },
        "mapping": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Inter-framework mappings"),
        },
        "action_plan": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Action plans"),
        },
        "config": {
            "actions": ["read", "update"],
            "label": _("Compliance configuration"),
        },
        "export": {
            "actions": ["read"],
            "label": _("Compliance export"),
        },
        "audit_trail": {
            "actions": ["read"],
            "label": _("Compliance audit trail"),
        },
    },
    "risks": {
        "assessment": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Risk assessments"),
        },
        "criteria": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Risk criteria"),
        },
        "risk": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Risk register"),
        },
        "treatment": {
            "actions": ["create", "read", "update", "delete", "approve"],
            "label": _("Treatment plans"),
        },
        "acceptance": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Risk acceptances"),
        },
        "threat": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Threats"),
        },
        "vulnerability": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Vulnerabilities"),
        },
        "iso27005": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("ISO 27005 analyses"),
        },
        "export": {
            "actions": ["read"],
            "label": _("Risk export"),
        },
        "audit_trail": {
            "actions": ["read"],
            "label": _("Risk audit trail"),
        },
    },
    "system": {
        "admin_django": {
            "actions": ["access"],
            "label": _("Django administration"),
        },
        "users": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Users"),
        },
        "groups": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Groups"),
        },
        "audit_trail": {
            "actions": ["read"],
            "label": _("System audit trail"),
        },
        "config": {
            "actions": ["read", "update"],
            "label": _("System configuration"),
        },
        "webhooks": {
            "actions": ["create", "read", "update", "delete"],
            "label": _("Webhooks"),
        },
        "notifications": {
            "actions": ["read", "update"],
            "label": _("Notifications"),
        },
    },
}

# Action labels for display
ACTION_LABELS = {
    "create": _("Create"),
    "read": _("Read"),
    "update": _("Update"),
    "delete": _("Delete"),
    "access": _("Access"),
    "approve": _("Approve"),
    "assess": _("Assess"),
    "validate": _("Validate"),
}

# Module labels for display
MODULE_LABELS = {
    "context": _("Governance"),
    "assets": _("Assets"),
    "risks": _("Risk management"),
    "compliance": _("Compliance"),
    "system": _("System"),
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
        "description": _("Full technical administration of the platform. All permissions."),
        "filter": lambda codename: True,  # all permissions
    },
    "Administrateur": {
        "description": _("Full functional administration. All permissions except Django admin access."),
        "filter": lambda codename: codename != "system.admin_django.access",
    },
    "RSSI / DPO": {
        "description": _("GRC system steering. Read, create, update, approve. No deletion or system configuration."),
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
        "description": _("Platform consultation and audit. Read-only access to all modules."),
        "filter": lambda codename: codename.endswith(".read"),
    },
    "Contributeur": {
        "description": _("GRC content contribution. Read, create, update. No deletion or system access."),
        "filter": lambda codename: (
            codename.endswith(".read")
            or codename.endswith(".create")
            or codename.endswith(".update")
        )
        and not codename.startswith("system."),
    },
    "Lecteur": {
        "description": _("Read-only access. Read on all modules except system."),
        "filter": lambda codename: codename.endswith(".read")
        and not codename.startswith("system."),
    },
}
