# Installation

Cairn runs as a Docker stack: the Django application (ASGI/Uvicorn), PostgreSQL 16 and Redis 7 (real-time features).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Option 1 : run from source

```bash
# 1. Copy the environment file
cp .env.example .env

# 2. Start the services
docker compose up --build

# 3. Apply migrations (in another terminal)
docker compose exec web python manage.py migrate

# 4. Create a superuser
docker compose exec web python manage.py createsuperuser
```

The application is available at [http://localhost:8000](http://localhost:8000).
The admin interface is at [http://localhost:8000/admin/](http://localhost:8000/admin/).

## Option 2 : run the published image

Run Cairn directly from the published Docker Hub image (`frousselet/cairn`) without cloning the repository.

Create a `docker-compose.yml` file:

```yaml
services:
  web:
    image: frousselet/cairn:latest
    ports:
      - "8000:8000"
    environment:
      SECRET_KEY: change-me-to-a-random-secret-key
      DEBUG: "False"
      ALLOWED_HOSTS: localhost,127.0.0.1
      POSTGRES_DB: open_grc
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      REDIS_HOST: redis
      REDIS_PORT: "6379"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  db:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: open_grc
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

Then start the stack:

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Demo data (optional)

To explore Cairn with realistic sample content, load the fictional **Voltara Energy** dataset (a mid-size renewable energy operator: ISO 27001 / NIS2 / GDPR frameworks, audits, risks, EBIOS RM study, indicators, management reviews) on a **fresh, empty database**:

```bash
docker compose exec -T web python manage.py shell -c "exec(open('scripts/seed_demo_data.py').read())"
```

Then sign in with `elise.moreau@voltara.example` / `VoltaraDemo!2026` (superuser). All seeded accounts share the same password. This script is intended for development and demo environments only.

## AI assistant (optional)

"Ask Cairn" answers simple natural-language questions from the command palette (Ctrl+K), e.g. *"Quelles décisions ont été prises lors de la dernière revue de direction ?"*. It runs entirely on your host through an [Ollama](https://ollama.com/) sidecar: no data leaves the machine, and every data access enforces the asking user's permissions.

```bash
# 1. Start the sidecar (the `ai` profile is opt-in)
docker compose --profile ai up -d

# 2. Pull the model once (kept in the ollama_models volume)
docker compose exec ollama ollama pull qwen3:1.7b

# 3. Enable the feature in .env, then restart web
# AI_ASSISTANT_ENABLED=True
```

Sizing: the default `qwen3:1.7b` model needs roughly 2-4 GB of RAM (CPU-only inference). The first question after startup loads the model (10-20 extra seconds); warm questions take about 5-20 seconds. Any Ollama chat model can be used instead via `AI_ASSISTANT_MODEL`. Without the profile (or if Ollama is down) the palette works exactly as before. Details: [docs/modules/assistant/](modules/assistant/README.md).

## Scheduled lifecycle commands

Two management commands keep the risk register in sync with time and are intended to be run **once a day** by a cron job (host or container side):

```bash
# Set RiskAcceptance.status = EXPIRED for any active acceptance past its
# valid_until date; print upcoming expirations within --reminder-days
# (default 30) for operators to act on.
docker compose exec web python manage.py expire_risk_acceptances

# Set RiskTreatmentPlan.status = OVERDUE for any in-flight plan whose
# target_date has passed (skips COMPLETED, CANCELLED and already-OVERDUE).
docker compose exec web python manage.py mark_overdue_treatment_plans
```

Both accept `--dry-run` to preview changes. A typical host cron entry:

```cron
# /etc/cron.d/cairn-lifecycle
15 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py expire_risk_acceptances
20 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py mark_overdue_treatment_plans
```
