#!/bin/sh
set -e

# Clear stale bytecode from image layer that may conflict with bind-mounted source
find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

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
# One-time fixup: migration 0022_company_settings was renamed to 0023_company_settings
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute(\"SELECT 1 FROM django_migrations WHERE app='accounts' AND name='0022_company_settings'\")
    if c.fetchone():
        c.execute(\"UPDATE django_migrations SET name='0023_company_settings' WHERE app='accounts' AND name='0022_company_settings'\")
" 2>/dev/null || true
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
