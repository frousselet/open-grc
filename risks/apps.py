from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RisksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "risks"
    verbose_name = _("Risk management")
