FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/frousselet/open-grc"
LABEL org.opencontainers.image.description="Open GRC – Governance, Risk & Compliance platform"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG APP_VERSION=dev

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gettext \
       libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
       libffi-dev libcairo2 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN echo "${APP_VERSION}" > /etc/app-version

RUN python manage.py compilemessages 2>/dev/null || true
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "core.asgi:application", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "3", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--access-log"]
