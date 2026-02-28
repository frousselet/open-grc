#!/bin/sh
set -e

echo "Applying database migrations…"
python manage.py migrate --noinput

echo "Compiling translation files…"
python manage.py compilemessages

# Create the initial super-admin if configured and not already present.
# Requires DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD in the environment.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser \
        --noinput \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --first_name "${DJANGO_SUPERUSER_FIRST_NAME:-Admin}" \
        --last_name "${DJANGO_SUPERUSER_LAST_NAME:-}" \
        2>/dev/null || true
    echo "Super-admin check complete."
fi

exec "$@"
