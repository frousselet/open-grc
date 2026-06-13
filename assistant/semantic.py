"""Semantic search helpers: embed-text building and in-Python cosine ranking.

The corpus here (a GRC instance's requirements) is small enough that a
brute-force cosine over stored embeddings is instant, so no vector database is
needed. Embeddings live in ``SemanticIndex`` as plain JSON lists, which keeps
the column portable across PostgreSQL and the SQLite test database.
"""

import math

from django.conf import settings
from django.utils.html import strip_tags

from assistant.models import SemanticIndex, content_hash
from assistant.providers import get_client


def requirement_text(requirement):
    """Build the text embedded for a requirement (number, name, description)."""
    parts = [
        requirement.requirement_number or "",
        requirement.name or "",
        strip_tags(requirement.description or ""),
        strip_tags(requirement.guidance or ""),
    ]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def cosine(a, b):
    """Cosine similarity between two equal-length vectors (0 if degenerate)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def rank_object_ids(query_vector, content_type, limit):
    """Return up to ``limit`` object ids ranked by cosine to ``query_vector``."""
    scored = []
    rows = SemanticIndex.objects.filter(content_type=content_type).values_list(
        "object_id", "embedding"
    )
    for object_id, embedding in rows:
        score = cosine(query_vector, embedding)
        if score > 0:
            scored.append((score, object_id))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [object_id for _, object_id in scored[:limit]]


def embed_query(text):
    """Embed a single query string; returns the vector or None on failure."""
    vectors = get_client().embed([text])
    return vectors[0] if vectors else None


def upsert_embedding(content_type, obj, text, vector):
    """Create or update the SemanticIndex row for one object."""
    model = settings.AI_ASSISTANT_EMBED_MODEL
    SemanticIndex.objects.update_or_create(
        content_type=content_type,
        object_id=obj.pk,
        defaults={
            "text": text,
            "content_hash": content_hash(model, text),
            "embedding": vector,
            "model_name": model,
        },
    )
