"""Build or refresh the semantic search index (requirement embeddings).

Run after enabling AI_ASSISTANT_SEMANTIC_ENABLED, after bulk requirement
imports, or on a schedule. Idempotent: only objects whose text or embedding
model changed are re-embedded (unless --force), and embeddings for deleted
requirements are pruned.
"""

from django.core.management.base import BaseCommand, CommandError

from assistant.providers import AssistantError
from assistant.semantic import rebuild_index


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
        def progress(done, total):
            self.stdout.write(f"  embedded {done}/{total}")

        try:
            result = rebuild_index(
                force=options["force"],
                batch_size=options["batch_size"],
                progress=progress,
            )
        except AssistantError as exc:
            raise CommandError(
                f"Embedding failed: {exc}. Check the AI assistant configuration "
                f"(provider, API key, model, connectivity)."
            ) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Semantic index updated: {result['embedded']} embedded, "
            f"{result['pruned']} pruned."
        ))
