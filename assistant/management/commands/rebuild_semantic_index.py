"""Build or refresh the semantic search index (requirement embeddings).

Run after enabling AI_ASSISTANT_SEMANTIC_ENABLED, after bulk requirement
imports, or on a schedule. Idempotent: only objects whose text or embedding
model changed are re-embedded (unless --force), and embeddings for deleted
requirements are pruned.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from assistant.models import SemanticIndex, content_hash
from assistant.providers import get_client
from assistant.semantic import requirement_text, upsert_embedding


class Command(BaseCommand):
    help = "Build or refresh the requirement semantic search index."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Re-embed every requirement, ignoring content hashes.",
        )
        parser.add_argument(
            "--batch-size", type=int, default=32,
            help="Number of texts per embedding API call.",
        )

    def handle(self, *args, **options):
        from compliance.models import Requirement

        force = options["force"]
        batch = max(1, options["batch_size"])
        model = settings.AI_ASSISTANT_EMBED_MODEL
        content_type = SemanticIndex.REQUIREMENT

        existing = dict(
            SemanticIndex.objects.filter(content_type=content_type).values_list(
                "object_id", "content_hash"
            )
        )
        pending, seen = [], set()
        for req in Requirement.objects.all().iterator():
            seen.add(req.pk)
            text = requirement_text(req)
            if not text:
                continue
            if not force and existing.get(req.pk) == content_hash(model, text):
                continue
            pending.append((req, text))

        stale_ids = set(existing) - seen
        if stale_ids:
            SemanticIndex.objects.filter(
                content_type=content_type, object_id__in=stale_ids
            ).delete()

        client = get_client()
        done = 0
        for start in range(0, len(pending), batch):
            chunk = pending[start:start + batch]
            vectors = client.embed([text for _, text in chunk])
            for (obj, text), vector in zip(chunk, vectors):
                upsert_embedding(content_type, obj, text, vector)
                done += 1
            self.stdout.write(f"  embedded {done}/{len(pending)}")

        self.stdout.write(self.style.SUCCESS(
            f"Semantic index updated: {done} embedded, {len(stale_ids)} pruned."
        ))
