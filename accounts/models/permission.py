import uuid

from django.db import models

from accounts.constants import PermissionAction


class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codename = models.CharField(
        "Code technique",
        max_length=255,
        unique=True,
        help_text="Format : module.feature.action",
    )
    name = models.CharField("Libellé", max_length=255)
    module = models.CharField("Module", max_length=100, db_index=True)
    feature = models.CharField("Feature", max_length=100, db_index=True)
    action = models.CharField(
        "Action",
        max_length=20,
        choices=PermissionAction.choices,
    )
    description = models.TextField("Description", blank=True, default="")
    is_system = models.BooleanField("Permission système", default=True)

    class Meta:
        ordering = ["module", "feature", "action"]
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"

    def __str__(self):
        return self.codename
