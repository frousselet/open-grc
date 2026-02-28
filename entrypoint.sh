#!/bin/sh
set -e

echo "Compiling translation files…"
python manage.py compilemessages

exec "$@"
