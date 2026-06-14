import os
import sys

from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant"

    def ready(self):
        from assistant import signals  # noqa: F401

        self._maybe_refresh_index_on_startup()

    @staticmethod
    def _maybe_refresh_index_on_startup():
        """Refresh the semantic index once when a server process boots.

        Inert unless the assistant and semantic search are both enabled. Skipped
        for management commands (migrate, test, the rebuild command itself...),
        which also run ``ready()`` - only ``runserver`` and app servers
        (uvicorn/gunicorn) trigger it. The work runs in a guarded background
        thread, so a slow or unreachable provider never blocks boot.
        """
        from django.conf import settings

        if not (
            settings.AI_ASSISTANT_ENABLED and settings.AI_ASSISTANT_SEMANTIC_ENABLED
        ):
            return
        prog = os.path.basename(sys.argv[0] or "")
        if prog.startswith("manage") and (
            len(sys.argv) < 2 or sys.argv[1] != "runserver"
        ):
            return

        from assistant.semantic import rebuild_index_async

        rebuild_index_async()
