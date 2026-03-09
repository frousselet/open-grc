import os

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assets"
    verbose_name = _("Assets")

    def ready(self):
        # Only start the SPOF scheduler when running the dev server or
        # production WSGI/ASGI — never during management commands (migrate,
        # compilemessages, etc.) or tests.
        import sys

        if "pytest" in sys.modules or "test" in sys.argv:
            return

        # When invoked via `manage.py <command>`, only start for runserver.
        # In production (gunicorn/uvicorn), sys.argv[0] won't be manage.py
        # and RUN_MAIN is not set — always start in that case.
        is_managepy = any(
            arg.endswith("manage.py") or arg == "django" for arg in sys.argv[:1]
        )
        if is_managepy and "runserver" not in sys.argv:
            return

        if os.environ.get("RUN_MAIN", "true") == "true":
            from assets.services.spof_scheduler import start_spof_scheduler

            start_spof_scheduler()
