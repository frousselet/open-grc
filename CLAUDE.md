# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open GRC is a Governance, Risk and Compliance (GRC) platform built with Django 5.2, PostgreSQL 16, and Bootstrap 5.3 + HTMX for the frontend. It covers organizational context, asset management, risk management (ISO 27005/EBIOS RM), and compliance tracking.

## Development Commands

### Running with Docker
```bash
docker compose up --build          # Start all services
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### Running Tests
```bash
pytest                             # Run all tests
pytest accounts/tests/             # Run tests for a specific app
pytest accounts/tests/test_models.py  # Run a specific test file
pytest -k "test_name"              # Run a specific test by name
pytest --co                        # List tests without running them
```

Tests use `core.settings_test` (configured in `pytest.ini`), which uses SQLite in-memory and fast MD5 password hashing.

### Django Management
```bash
python manage.py runserver 0.0.0.0:8000   # Dev server (used by docker-compose)
python manage.py makemigrations           # Generate migrations
python manage.py migrate                  # Apply migrations
python manage.py compilemessages          # Compile i18n translation files
python manage.py collectstatic --noinput  # Collect static files
```

## Architecture

### Django Apps

| App | Purpose |
|-----|---------|
| `core` | Project settings, root URL config, shared mixins (`SortableListMixin`), base views (dashboard, calendar) |
| `accounts` | Custom `User` model (email-based auth, UUID PKs), groups with 6 system roles, custom permissions (`module.feature.action` codenames), passkey/WebAuthn support, access logging |
| `context` | Organizational context: Scopes, Sites, Issues, Stakeholders, Objectives, SWOT, Roles, Activities, Tags |
| `assets` | Essential assets (with DIC valuation), support assets (IT infra with lifecycle), dependencies, asset groups, suppliers |
| `compliance` | Frameworks, sections, requirements, assessments, action plans, inter-framework mappings, Excel import |
| `risks` | Risk assessments, risk criteria, risks (3-level tracking), threats, vulnerabilities, ISO 27005 analysis, treatment plans, risk acceptance |
| `helpers` | Help banners with multilingual content |
| `mcp` | MCP (Model Context Protocol) server integration with OAuth 2.0 |

### Key Patterns

**Base Models** (`context/models/base.py`):
- `BaseModel` — UUID PK, timestamps, `created_by`, approval workflow fields (`is_approved`, `approved_by`, `approved_at`), versioning, tags. All domain models inherit from this.
- `ScopedModel` — extends `BaseModel` with many-to-many `scopes` for organizational tenancy.
- `ReferenceGeneratorMixin` — auto-generates sequential references (e.g., `RISK-1`, `ASST-2`). Subclasses set a 4-char `REFERENCE_PREFIX`.

**App Structure** — each domain app follows a consistent layout:
- `models/` — model package with one file per model
- `views.py` — class-based views (Django generic views)
- `forms.py` — model forms
- `urls.py` — web UI URL patterns
- `api/` — DRF serializers, viewsets, and URL routes under `/api/v1/`
- `constants.py` — choice tuples and enums
- `templates/<app>/` — Django templates
- `tests/` — tests with `factories.py` (factory-boy) and `test_*.py` files

**URL Structure**:
- Web UI: `/<app>/...` (e.g., `/context/`, `/assets/`, `/risks/`)
- REST API: `/api/v1/<app>/...`
- Admin: `/admin/`

**Testing**: Uses pytest-django with factory-boy factories. Each app has a `tests/factories.py` defining model factories.

**Audit Trail**: All models use `django-simple-history` (`HistoricalRecords`) for change tracking.

**i18n**: Bilingual support (English/French). Translation files are in `locale/`.

**Frontend**: Server-rendered Django templates with Bootstrap 5.3, HTMX for dynamic partial updates, dark mode via OS preference.

**View Mixins** (`core/mixins.py`, `accounts/mixins.py`):
- `SortableListMixin` — server-side sorting with user preferences persisted in `User.table_preferences` JSON field
- `CreatedByMixin` — auto-populates `created_by` on form save
- `ApprovalContextMixin` / `ApprovableUpdateMixin` — two-step approval workflow (submit → approve)
- `ScopeFilterMixin` — filters querysets by user's assigned scopes

**MCP Server** (`mcp/`): JSON-RPC 2.0 server with 40+ tools across all modules. Tool permissions enforced via `@require_perm` decorator. OAuth 2.0 authorization flow for external clients.

### CI/CD

GitHub Actions (`.github/workflows/`):
- `tests.yml` — runs `pytest -x -v --cov` on push to main and all PRs (Python 3.12)
- `docker-publish.yml` — builds and pushes Docker image to Docker Hub on version tags (`v*`)

### Feature Specifications

Detailed specs live in `features_spec/` (M0–M4 markdown files covering users, context, assets, compliance, and risk modules). Reference these when implementing new features in a module.
