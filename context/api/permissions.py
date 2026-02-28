from accounts.api.permissions import DRF_ACTION_MAP, ModulePermission

# Additional action mappings for context-specific actions
CONTEXT_ACTION_MAP = {
    "archive": "update",
    "validate": "update",
    "assign": "update",
}


class ContextPermission(ModulePermission):
    """
    RBAC permission check for the context module.
    Inherits from ModulePermission with context-specific action mappings.
    """

    custom_action_map = CONTEXT_ACTION_MAP
