"""Persistent models for the Ask Cairn assistant.

The only persistent entity is user feedback on an answer. Like ``AccessLog``,
it is a plain log row (not a domain ``BaseModel``): no approval workflow, no
versioning, no history. It captures everything needed to later export a set of
feedback and hand it to an LLM to improve the assistant: the prompt, the UI
language, the LLM response (summary and returned record cards), the provider /
model, the thumbs rating and an optional comment.
"""

import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AssistantFeedback(models.Model):
    RATING_UP = "up"
    RATING_DOWN = "down"
    RATING_CHOICES = [
        (RATING_UP, _("Thumbs up")),
        (RATING_DOWN, _("Thumbs down")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_feedback",
        verbose_name=_("User"),
    )
    question = models.TextField(_("Question"))
    language = models.CharField(_("Interface language"), max_length=10, blank=True)
    rating = models.CharField(_("Rating"), max_length=4, choices=RATING_CHOICES)
    comment = models.TextField(_("Comment"), blank=True)
    summary = models.TextField(_("LLM summary"), blank=True)
    results = models.JSONField(_("Returned records"), default=list, blank=True)
    degraded = models.BooleanField(_("Degraded answer"), default=False)
    refused_tools = models.JSONField(_("Refused tools"), default=list, blank=True)
    provider = models.CharField(_("LLM provider"), max_length=50, blank=True)
    model_name = models.CharField(_("LLM model"), max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Assistant feedback")
        verbose_name_plural = _("Assistant feedback")
        indexes = [models.Index(fields=["rating", "created_at"])]

    def __str__(self):
        return f"{self.get_rating_display()} - {self.question[:50]}"

    def as_export_dict(self):
        """Structured record for the export handed to an improvement LLM."""
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user": self.user.email if self.user else None,
            "question": self.question,
            "language": self.language,
            "rating": self.rating,
            "comment": self.comment,
            "summary": self.summary,
            "results": self.results,
            "degraded": self.degraded,
            "refused_tools": self.refused_tools,
            "provider": self.provider,
            "model": self.model_name,
        }


def content_hash(model_name, text):
    """Stable hash of the embedding model + text, to detect stale entries."""
    return hashlib.sha256(f"{model_name}\x00{text}".encode()).hexdigest()


class SemanticIndex(models.Model):
    """Portable embedding store for semantic search (no pgvector).

    One row per indexed object (currently requirements). The embedding is kept
    as a plain JSON list of floats so the column works on PostgreSQL and on the
    SQLite test database alike; ranking is done in Python (see
    ``assistant.semantic``). ``content_hash`` lets the reindex command skip
    objects whose text and model are unchanged.
    """

    REQUIREMENT = "requirement"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.CharField(_("Content type"), max_length=40)
    object_id = models.UUIDField(_("Object id"))
    text = models.TextField(_("Embedded text"))
    content_hash = models.CharField(_("Content hash"), max_length=64)
    embedding = models.JSONField(_("Embedding"), default=list)
    model_name = models.CharField(_("Embedding model"), max_length=100, blank=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        verbose_name = _("Semantic index entry")
        verbose_name_plural = _("Semantic index entries")
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"], name="unique_semantic_object"
            )
        ]
        indexes = [models.Index(fields=["content_type"])]

    def __str__(self):
        return f"{self.content_type}:{self.object_id}"
