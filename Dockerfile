FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/frousselet/open-grc"
LABEL org.opencontainers.image.description="Open GRC – Governance, Risk & Compliance platform"
LABEL org.opencontainers.image.licenses="MIT"

ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py compilemessages 2>/dev/null || true
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--worker-tmp-dir", "/dev/shm", \
     "--workers", "3", \
     "--timeout", "120", \
     "--preload", \
     "--forwarded-allow-ips", "*", \
     "--access-logfile", "-"]
