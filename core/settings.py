"""
Django settings for Cairn project.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-change-me-in-production",
)

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")


def _detect_version():
    """Return app version from /etc/app-version, version.txt, or 'dev'."""
    for path in (Path("/etc/app-version"), BASE_DIR / "version.txt"):
        try:
            version = path.read_text().strip()
            if version:
                return version
        except Exception:
            pass
    return "dev"


APP_VERSION = _detect_version()

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Reverse proxy support — trust X-Forwarded-Proto so Django knows the
# original request was HTTPS (required for secure cookies, CSRF, etc.).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Origins allowed to make cross-site requests (needed behind a reverse proxy).
# Example: CSRF_TRUSTED_ORIGINS=https://grc.example.com,https://grc.rslt.fr
_trusted = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _trusted.split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "django_htmx",
    "core",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "simple_history",
    "accounts",
    "helpers",
    "context",
    "assets",
    "compliance",
    "risks",
    "reports",
    "mcp",
    "assistant",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.UserLanguageMiddleware",
    "accounts.middleware.ImpersonationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "core.context_processors.app_version",
                "core.context_processors.assistant_enabled",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Django Channels
#
# RedisPubSubChannelLayer instead of the historical RedisChannelLayer:
# the former uses Redis pub/sub (push) and the latter polls BLPOP with
# a finite socket read timeout. With BLPOP the dashboard WebSocket
# consumer crashed every few seconds with redis.exceptions.TimeoutError
# when no event was published in the polling window, the WS reconnected,
# and the boot log filled with stack traces. PubSub has no polling
# timeout because there is nothing to poll: Redis pushes when a message
# arrives. Trade-off: messages are not queued for consumers that drop
# briefly, which is fine here because the broadcast events are dashboard
# refresh hints (the next save broadcasts another one) rather than
# durable work items.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            "hosts": [(os.environ.get("REDIS_HOST", "redis"), int(os.environ.get("REDIS_PORT", 6379)))],
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "open_grc"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
    }
}

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailAuthBackend",
    "accounts.backends.PasskeyAuthBackend",
    "accounts.backends.GroupPermissionBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.ComplexityValidator"},
]

LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
    ("fr", "Français"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Europe/Paris"

USE_I18N = True

USE_THOUSAND_SEPARATOR = True

USE_TZ = True

STATIC_URL = "static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "mcp.api.authentication.OAuthTokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "context.api.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "context.api.renderers.StandardJSONRenderer",
    ],
}

# Email (notifications)
# Defaults to the console backend in DEBUG so no SMTP setup is needed in dev.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "cairn@localhost")
# Absolute URL prefix used in notification emails (e.g. https://grc.example.com).
SITE_URL = os.environ.get("SITE_URL", "")

# Simple JWT
# WebAuthn / Passkeys
# When not set, RPID and origin are derived from the request automatically.
WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID")
WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Cairn")
WEBAUTHN_ORIGIN = os.environ.get("WEBAUTHN_ORIGIN")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# AI assistant ("Ask Cairn"): optional natural-language question mode in the
# command palette, backed by a pluggable LLM provider. Disabled by default;
# the rest of the application works normally without it. The default provider
# is Mistral AI (third-party, EU-hosted); the self-hosted "ollama" provider
# stays selectable for those pointing at their own instance.
AI_ASSISTANT_ENABLED = os.environ.get("AI_ASSISTANT_ENABLED", "False").lower() in ("true", "1", "yes")
AI_ASSISTANT_PROVIDER = os.environ.get("AI_ASSISTANT_PROVIDER", "mistral")
AI_ASSISTANT_API_KEY = os.environ.get("AI_ASSISTANT_API_KEY", "")
AI_ASSISTANT_BASE_URL = os.environ.get("AI_ASSISTANT_BASE_URL", "https://api.mistral.ai/v1")
AI_ASSISTANT_MODEL = os.environ.get("AI_ASSISTANT_MODEL", "mistral-small-latest")
AI_ASSISTANT_CONNECT_TIMEOUT = float(os.environ.get("AI_ASSISTANT_CONNECT_TIMEOUT", "2"))
AI_ASSISTANT_TIMEOUT = float(os.environ.get("AI_ASSISTANT_TIMEOUT", "30"))
AI_ASSISTANT_MAX_TOOL_ROUNDS = int(os.environ.get("AI_ASSISTANT_MAX_TOOL_ROUNDS", "3"))
AI_ASSISTANT_MAX_RECORDS_PER_TOOL = int(os.environ.get("AI_ASSISTANT_MAX_RECORDS_PER_TOOL", "5"))
# Cap on the completion length (Mistral / OpenAI-compatible backends).
AI_ASSISTANT_MAX_TOKENS = int(os.environ.get("AI_ASSISTANT_MAX_TOKENS", "1024"))
# Semantic search over requirement content (embeddings + in-Python cosine).
# Opt-in: build the index with `manage.py rebuild_semantic_index` after enabling.
AI_ASSISTANT_SEMANTIC_ENABLED = os.environ.get("AI_ASSISTANT_SEMANTIC_ENABLED", "False").lower() in ("true", "1", "yes")
AI_ASSISTANT_EMBED_MODEL = os.environ.get("AI_ASSISTANT_EMBED_MODEL", "mistral-embed")
# Ollama provider only: local instance URL, context window, and chain-of-thought
# during routing (thinking models such as qwen3). Ignored by the Mistral provider.
AI_ASSISTANT_OLLAMA_URL = os.environ.get("AI_ASSISTANT_OLLAMA_URL", "http://ollama:11434")
AI_ASSISTANT_NUM_CTX = int(os.environ.get("AI_ASSISTANT_NUM_CTX", "8192"))
AI_ASSISTANT_ROUTING_THINK = os.environ.get("AI_ASSISTANT_ROUTING_THINK", "False").lower() in ("true", "1", "yes")
