# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cairn is a Governance, Risk and Compliance (GRC) platform built with Django 5.2, PostgreSQL 16, and Bootstrap 5.3 + HTMX for the frontend. It covers organizational context, asset management, risk management (ISO 27005/EBIOS RM), and compliance tracking.

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
| ----- | --------- |
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

GitHub Actions (`.github/workflows/`) is the CI:

- `tests.yml` (Tests) - on every push to `main` and on pull requests: installs dependencies, runs `ruff check`, compiles `.po` translations, then runs `pytest -x -v --cov`.
- `docker-publish.yml` (Docker) - on version tags (`v*`): builds and pushes the Docker image to Docker Hub (`frousselet/cairn`) with semver + `latest` tags. Requires the `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repository secrets.
- CodeQL scanning runs on pushes to `main` and on a schedule.

Ruff config lives in `pyproject.toml`.

### Feature Specifications

Detailed specs live in `docs/modules/` : one directory per module (`m0-accounts/`, `m1-context/`, `m2-assets/`, `m3-compliance/`, `m4-risks/` with the `ebios-rm/` sub-module, `management-review/`), and one Markdown file per domain entity inside each. Each module's `README.md` holds the cross-cutting sections (business rules, API conventions, permissions, UI, notifications, technical considerations). Reference the right entity file when implementing a feature change, and update it in the same commit. See `docs/modules/README.md` for the layout conventions.

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
- **Branch workflow**: All commits must be made on a new branch (never directly on `main`). The only exception is the release version bump: when tagging a release, the CHANGELOG promotion commit goes directly on `main` with the exact message ``Bump version `vX.Y.Z` ``.
- **Git author**: All commits must be authored as `Claude <noreply@anthropic.com>`. Use `git commit --author="Claude <noreply@anthropic.com>"` for every commit.
- **Commit messages in English**: All git commit messages must be written in English, regardless of the conversation language.
- **English in code**: All code must use English — variable names, constant names, function names, class names, comments, docstrings. French is only used in user-facing translated strings (via `_()`, `pgettext_lazy()`, `{% trans %}`) and DB string values that are already stored.
- **No em dash character**: Never use the em dash character `—` (U+2014) in code, strings, or display text. Use ` : ` or ` - ` instead.
- **Keep README.md up to date**: After any change that adds, removes or modifies a feature, model, MCP tool, dependency, or configuration, update `README.md` accordingly (feature tables, MCP tools section, tech stack, installation instructions). The README is the public-facing documentation and must always reflect the current state of the codebase.
- **Keep CHANGELOG.md up to date**: Before committing and before creating a version tag, update `CHANGELOG.md` following the [Keep a Changelog](https://keepachangelog.com/) format. Add entries under `## [Unreleased]` with the appropriate category (Added, Changed, Fixed, Removed). When tagging a release, move the unreleased entries under a new `## [x.y.z] - YYYY-MM-DD` heading and add the comparison link at the bottom of the file.
- **Brand guidelines must be respected**: Any visual, typographic, motion or component change MUST follow `docs/brand/brand-guidelines.md`. This is the single source of truth for the palette (one identity colour: navy `#1E3A8A`; semantic colours reserved for statuses only), typography (Inter only, weights 400/500/600/700; no display font; no UPPERCASE on titles), spacing / radii / shadow tokens, iconography (Bootstrap Icons exclusively), component principles (1px borders, soft shadows, calm hover states), motion (`--ease-out`, durations 150/220/320 ms, `prefers-reduced-motion` honoured), accessibility commitments (WCAG 2.2 AA), and voice/tone (sober, precise, action-oriented, bilingual). The logo must use the responsive system: `mark.svg` ≥ 24 px, `mark-sm.svg` ≤ 22 px. If a proposed change cannot be expressed within these constraints, update the guidelines first (with user approval), then apply.
- **Persistent instructions**: When the user asks to "always do something" or to "remember something", add it to this `CLAUDE.md` file so it persists across sessions.
