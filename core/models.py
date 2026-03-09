import logging

from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class VersioningConfig(models.Model):
    """Per-model configuration for versioning and approval behavior.

    Each record controls how a specific BaseModel subclass handles
    version increments and approval workflow.
    """

    model_name = models.CharField(
        _("Model identifier"),
        max_length=100,
        unique=True,
        help_text=_("Django model label, e.g. 'context.scope'"),
    )
    model_label = models.CharField(
        _("Display name"),
        max_length=200,
        blank=True,
    )
    approval_enabled = models.BooleanField(
        _("Approval enabled"),
        default=True,
        help_text=_("When disabled, approval workflow is hidden for this item type."),
    )
    major_fields = models.JSONField(
        _("Major change fields"),
        default=list,
        blank=True,
        help_text=_(
            "List of field names whose modification triggers a version increment "
            "and approval reset. If empty, all field changes are considered major."
        ),
    )

    class Meta:
        verbose_name = _("Versioning configuration")
        verbose_name_plural = _("Versioning configurations")
        ordering = ["model_name"]

    def __str__(self):
        return self.model_label or self.model_name

    @property
    def major_fields_display(self):
        """Return major_fields as a list of (field_name, verbose_name) tuples."""
        if not self.major_fields:
            return []
        try:
            model = apps.get_model(self.model_name)
            result = []
            for fname in self.major_fields:
                try:
                    field = model._meta.get_field(fname)
                    label = str(field.verbose_name)
                    result.append((fname, label[:1].upper() + label[1:]))
                except Exception:
                    result.append((fname, fname))
            return result
        except (LookupError, ValueError):
            return [(f, f) for f in self.major_fields]

    @classmethod
    def get_config(cls, model_class):
        """Return the VersioningConfig for a model class, or None if not configured."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        try:
            return cls.objects.get(model_name=label)
        except cls.DoesNotExist:
            return None

    @classmethod
    def _get_config_cached(cls, model_label):
        """Return cached config for a model label. Uses a simple module-level cache."""
        cache = _config_cache
        if model_label in cache:
            return cache[model_label]
        try:
            config = cls.objects.get(model_name=model_label)
        except cls.DoesNotExist:
            config = None
        cache[model_label] = config
        return config

    @classmethod
    def is_approval_enabled(cls, model_class):
        """Check if approval is enabled for a given model class."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        config = cls._get_config_cached(label)
        if config is None:
            return True  # Default: approval enabled
        return config.approval_enabled

    @classmethod
    def get_major_fields(cls, model_class):
        """Return the set of major fields for a model, or None if all fields are major."""
        label = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        config = cls._get_config_cached(label)
        if config is None:
            return None  # Default: all fields are major
        fields = config.major_fields
        if not fields:
            return None  # Empty list means all fields are major
        return set(fields)

    @classmethod
    def clear_cache(cls):
        """Clear the in-memory config cache."""
        _config_cache.clear()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        _config_cache.pop(self.model_name, None)

    def delete(self, *args, **kwargs):
        _config_cache.pop(self.model_name, None)
        super().delete(*args, **kwargs)


# Simple in-process cache for VersioningConfig lookups.
_config_cache: dict = {}
