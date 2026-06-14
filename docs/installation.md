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

"Ask Cairn" answers simple natural-language questions from the command palette (Ctrl+K), e.g. *"Quelles décisions ont été prises lors de la dernière revue de direction ?"*. Every data access enforces the asking user's permissions, and the answer cites the real matching records. The LLM backend is a **pluggable provider** (`AI_ASSISTANT_PROVIDER`); the feature is **off by default** and the palette works unchanged when it is disabled or the backend is unreachable.

Default (Mistral AI, third-party EU-hosted API): no sidecar, no model download, no GPU.

```bash
# In .env, then restart web:
AI_ASSISTANT_ENABLED=True
AI_ASSISTANT_PROVIDER=mistral
AI_ASSISTANT_API_KEY=your-mistral-api-key
AI_ASSISTANT_MODEL=mistral-small-latest
```

Other backends are configured the same way: `openai` for OpenAI (ChatGPT) or any OpenAI-compatible endpoint (vLLM, LiteLLM, LocalAI...), `anthropic` for Claude, and `ollama` for a self-hosted, no-egress deployment pointed at your own [Ollama](https://ollama.com/) instance. With a third-party provider, the question text and the compact record fields used for routing leave the platform. Provider setup, model guidance, the data-egress detail and semantic search are all documented in [docs/modules/assistant/](modules/assistant/README.md).

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

If the **semantic search** of the Ask Cairn assistant is enabled (`AI_ASSISTANT_SEMANTIC_ENABLED`), schedule the index refresh the same way. The command is idempotent (it only re-embeds changed requirements and prunes deleted ones), so a daily run is cheap. The index is also refreshed automatically when the app starts, a deleted requirement is pruned immediately, and an administrator can force a refresh from the Company settings page; the daily cron is the reliable, self-healing backstop.

```cron
25 2 * * * cd /opt/cairn && docker compose exec -T web python manage.py rebuild_semantic_index
```
