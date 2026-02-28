#!/bin/sh
set -e

echo "Waiting for database to be ready…"
max_retries=30
retry_count=0
until python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; do
    retry_count=$((retry_count + 1))
    if [ "$retry_count" -ge "$max_retries" ]; then
        echo "Error: Database not available after $max_retries attempts, exiting."
        exit 1
    fi
    echo "Database not ready yet (attempt $retry_count/$max_retries), waiting 1s…"
    sleep 1
done
echo "Database is ready."

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
