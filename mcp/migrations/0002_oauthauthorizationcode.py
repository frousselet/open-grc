import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mcp", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OAuthAuthorizationCode",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        unique=True,
                        verbose_name="Authorization code",
                    ),
                ),
                (
                    "client_id",
                    models.CharField(max_length=255, verbose_name="Client ID"),
                ),
                (
                    "redirect_uri",
                    models.URLField(max_length=2048, verbose_name="Redirect URI"),
                ),
                (
                    "scope",
                    models.CharField(
                        blank=True, default="", max_length=512, verbose_name="Scope"
                    ),
                ),
                (
                    "code_challenge",
                    models.CharField(
                        max_length=128, verbose_name="PKCE code challenge"
                    ),
                ),
                (
                    "code_challenge_method",
                    models.CharField(
                        default="S256",
                        max_length=10,
                        verbose_name="PKCE code challenge method",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        blank=True, default="", max_length=512, verbose_name="State"
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(verbose_name="Expires at"),
                ),
                (
                    "used",
                    models.BooleanField(default=False, verbose_name="Used"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created at"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oauth_authorization_codes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "OAuth authorization code",
                "verbose_name_plural": "OAuth authorization codes",
                "ordering": ["-created_at"],
            },
        ),
    ]
