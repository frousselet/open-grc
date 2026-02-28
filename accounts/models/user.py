import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from accounts.constants import LOCKOUT_DURATION_MINUTES, MAX_FAILED_ATTEMPTS
from accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("Adresse email", unique=True)
    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)
    job_title = models.CharField("Fonction", max_length=255, blank=True, default="")
    department = models.CharField("Service", max_length=255, blank=True, default="")
    phone = models.CharField("Téléphone", max_length=50, blank=True, default="")
    language = models.CharField(
        "Langue",
        max_length=10,
        choices=[("fr", "Français"), ("en", "English")],
        default="fr",
    )
    timezone = models.CharField(
        "Fuseau horaire",
        max_length=50,
        default="Europe/Paris",
    )
    is_active = models.BooleanField("Actif", default=True)
    is_staff = models.BooleanField("Accès admin Django", default=False)

    password_changed_at = models.DateTimeField(
        "Dernier changement de mot de passe",
        null=True,
        blank=True,
    )
    failed_login_attempts = models.PositiveIntegerField(
        "Tentatives échouées",
        default=0,
    )
    locked_until = models.DateTimeField(
        "Verrouillé jusqu'au",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email

    @property
    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def lock_account(self):
        from datetime import timedelta

        self.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        self.save(update_fields=["locked_until"])

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def increment_failed_attempts(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            self.lock_account()
        else:
            self.save(update_fields=["failed_login_attempts"])

    def get_allowed_scope_ids(self):
        """Return set of allowed scope IDs, or None if unrestricted."""
        from accounts.backends import GroupPermissionBackend

        return GroupPermissionBackend.get_allowed_scope_ids(self)
