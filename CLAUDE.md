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

## Development Guidelines

- **MCP tools are mandatory**: Every new feature must be exposed as MCP tools in `mcp/tools.py` with accurate docstrings and parameter descriptions. MCP is the primary integration surface for external clients.
- **API endpoints are mandatory**: Every new feature must include corresponding DRF endpoints in the app's `api/` directory (serializers, viewsets, URL routes under `/api/v1/`).
- **UI quality in both themes**: All templates and CSS must render correctly in light and dark mode. Test both themes when adding or modifying UI components.
- **Audit-grade rigor**: This platform supports real compliance audits. Data integrity, traceability, and correctness are critical — approval workflows, versioning, history tracking, and permission checks must never be bypassed or degraded.
- **Mobile-first care**: Always test and ensure UI components render well on mobile. Pay special attention to multi-select widgets, sticky bars, and form layouts on small screens.
- **Systematic French translations**: Every new user-facing string must be wrapped with `_()` or `{% trans %}` and have a corresponding French translation in `locale/fr/LC_MESSAGES/django.po`. Never leave untranslated strings.
- **No duplicate translation entries**: After modifying `locale/fr/LC_MESSAGES/django.po`, always verify there are no duplicate `msgid` entries (same `msgid` without different `msgctxt`). Duplicates cause `compilemessages` to fail. If a string already exists in the `.po` file (e.g., from another app/context), use `pgettext_lazy` in Python and `{% trans "..." context "..." %}` in templates to disambiguate, and add the entry with a `msgctxt` line in the `.po` file.
- **Workflow stepper UI for status transitions**: All models with a status workflow (assessments, action plans, etc.) must use the visual stepper component (horizontal pipeline with pills, connecting lines, SVG branch to "Annulé"). Reference the implementation in `compliance/templates/compliance/assessment_detail.html` (stepper HTML + JS) and `compliance/views.py` (`AssessmentDetailView.get_context_data` for stepper context logic). The stepper shows: done steps (checkmark), current step (accent pill), next step (clickable green button), future steps (dashed/faded). Refusal and cancellation transitions use a modal with mandatory comment. Never use simple buttons for workflow transitions.
- **Detail page layout — minimize tabs**: When creating or refactoring detail pages, prefer a **2-column card layout** (main content left, metadata sidebar right) with collapsible sections over Bootstrap nav-tabs. Tabs hide content and increase cognitive load — use them only when truly necessary (e.g., assessment detail with distinct Planning/Findings/History views). For most detail pages, display all information directly using stacked cards, collapsible `<details>` or Bootstrap collapse sections, and a sticky sidebar for key metadata (status, people, dates). Reference `compliance/templates/compliance/action_plan_detail.html` as the canonical example of this pattern.
- **Commit messages in English**: All git commit messages must be written in English, regardless of the conversation language.
- **English in code**: All code must use English — variable names, constant names, function names, class names, comments, docstrings. French is only used in user-facing translated strings (via `_()`, `pgettext_lazy()`, `{% trans %}`) and DB string values that are already stored.
- **Persistent instructions**: When the user asks to "always do something" or to "remember something", add it to this `CLAUDE.md` file so it persists across sessions.
