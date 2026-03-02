from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mcp"
    verbose_name = _("MCP Server")
