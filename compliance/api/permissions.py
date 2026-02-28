from accounts.api.permissions import ModulePermission

COMPLIANCE_ACTION_MAP = {
    "validate": "validate",
    "assess": "assess",
    "archive": "update",
    "summary": "read",
    "tree": "read",
    "reorder": "update",
    "overdue": "read",
    "dashboard": "read",
    "matrix": "read",
    "coverage": "read",
    "compliance_summary": "read",
}


class CompliancePermission(ModulePermission):
    """RBAC permission check for the compliance module."""

    custom_action_map = COMPLIANCE_ACTION_MAP
