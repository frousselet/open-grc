"""Assistant signals: keep the semantic index in sync with requirements.

A deleted requirement's embedding is pruned immediately - a network-free DB
delete, safe to run even when semantic search is disabled. New and edited
requirements are picked up by the rebuild (``assistant.semantic.rebuild_index``)
run on a schedule, at startup, or on demand from the admin, which re-embeds via
the LLM provider off the request path.
"""

import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from assistant.models import SemanticIndex

logger = logging.getLogger(__name__)


@receiver(post_delete, sender="compliance.Requirement")
def prune_requirement_embedding(sender, instance, **kwargs):
    try:
        SemanticIndex.objects.filter(
            content_type=SemanticIndex.REQUIREMENT, object_id=instance.pk
        ).delete()
    except Exception:
        # Never let index maintenance bubble up from a delete signal.
        logger.exception(
            "Failed to prune semantic index for requirement %s", instance.pk
        )
