import os

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assets"
    verbose_name = _("Assets")

    def ready(self):
        # In dev mode (runserver), Django spawns two processes; only start
        # the scheduler in the reloader child (RUN_MAIN=true).
        # In production (gunicorn/wsgi), RUN_MAIN is not set — always start.
        if os.environ.get("RUN_MAIN", "true") == "true":
            from assets.services.spof_scheduler import start_spof_scheduler

            start_spof_scheduler()
