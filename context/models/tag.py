import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=100, unique=True)
    color = models.CharField(
        _("Color"),
        max_length=7,
        default="#6c757d",
        help_text=_("Hex color code, e.g. #ff5733"),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.name
