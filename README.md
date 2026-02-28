# Open GRC

Open-source Governance, Risk and Compliance (GRC) platform built with Django.

## Features

### Governance (Context & Organisation)

- **Scopes** — hierarchical organisational perimeters with versioning and approval workflow
- **Sites** — physical and logical locations (offices, datacenters, cloud regions) with hierarchy
- **Issues** — internal/external strategic issues (PESTLE categories) with impact and trend tracking
- **Stakeholders** — interested parties with expectations, influence/interest levels and RACI support
- **Objectives** — security and business objectives with KPI tracking (target/current values, progress %)
- **SWOT Analysis** — structured strengths/weaknesses/opportunities/threats with impact levels
- **Roles & Responsibilities** — RACI matrix, mandatory role enforcement, responsibility assignments
- **Activities** — hierarchical business processes (core, support, management) with criticality levels

### Asset Management

- **Essential Assets** — business processes and information assets with DIC valuation (Confidentiality, Integrity, Availability on a 5-level scale)
- **Support Assets** — IT infrastructure (hardware, software, network, services, sites, people) with lifecycle tracking (EOL, warranty)
- **Dependencies** — essential-to-support asset mapping with criticality, SPOF detection and redundancy tracking
- **Asset Groups** — logical grouping of support assets
- **DIC Inheritance** — support assets automatically inherit max DIC levels from linked essential assets
- **Valuations** — historical DIC evaluation tracking per essential asset

### Risk Management

- **Risk Assessments** — ISO 27005 and EBIOS RM methodologies
- **Risk Criteria** — configurable likelihood/impact scales with dynamic risk matrix generation
- **Risks** — three-level tracking (initial, current, residual) with treatment decisions (accept, mitigate, transfer, avoid)
- **Threat Catalog** — reusable threats by type (deliberate, accidental, environmental) and origin
- **Vulnerability Catalog** — reusable vulnerabilities with severity, CVE references and remediation guidance
- **ISO 27005 Analysis** — atomic threat x vulnerability risk scenarios with combined likelihood/impact calculation
- **Treatment Plans** — structured remediation with ordered actions, progress tracking and cost estimates
- **Risk Acceptance** — formal acceptance records with expiry dates, conditions and review tracking
- **Risk Matrices** — visual heatmaps (current vs residual)

### Compliance

- **Frameworks** — regulatory and standard frameworks (ISO 27001, GDPR, NIS2, etc.) with type, category and jurisdiction
- **Sections** — hierarchical framework structure
- **Requirements** — per-framework requirements with compliance status, evidence and gap tracking
- **Assessments** — compliance evaluations with per-requirement results and automatic compliance level calculation
- **Action Plans** — gap remediation plans with priority, progress and cost tracking
- **Inter-Framework Mappings** — requirement-to-requirement mappings across frameworks (equivalent, partial, includes, related)
- **Framework Import** — Excel-based bulk import of frameworks and requirements

### Users & Access Control

- **Custom User Model** — email-based authentication with UUID primary keys
- **Role-Based Access Control** — granular permissions (90+) using `module.feature.action` codenames
- **6 System Groups** — Super Admin, Admin, RSSI/DPO, Auditor, Contributor, Reader
- **Scope-Based Tenancy** — groups can be restricted to specific organisational scopes
- **Account Security** — failed login lockout (5 attempts / 15 min), password complexity enforcement
- **Dual Authentication** — session-based (web UI) + JWT with token rotation (API)
- **Access Logs** — full audit trail of authentication events (login, logout, lockout, password change)

### Cross-Cutting Capabilities

- **Approval Workflows** — two-step approval (submit / approve) on all domain models with dedicated permissions
- **Audit Trail** — full change history on every model via django-simple-history
- **Versioning** — automatic version increment on all domain objects
- **Contextual Help** — inline help banners with multilingual content (FR/EN)
- **Excel Export** — export assets, risks, compliance data to Excel
- **Dark Mode** — automatic theme switching based on OS preference
- **Responsive UI** — collapsible sidebar, mobile-friendly layout
- **REST API** — full CRUD + filtering, search, pagination and export on all resources
- **HTMX Integration** — dynamic partial updates without full page reloads

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 5.2 LTS |
| Database | PostgreSQL 16 |
| REST API | Django REST Framework |
| Authentication | djangorestframework-simplejwt |
| Audit Trail | django-simple-history |
| Filtering | django-filter |
| Frontend | Bootstrap 5.3 + HTMX |
| Export | openpyxl |
| Server | Gunicorn |
| Container | Docker & Docker Compose |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Quick Start

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the services:

```bash
docker compose up --build
```

3. Apply migrations (in another terminal):

```bash
docker compose exec web python manage.py migrate
```

4. Create a superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

The application is available at [http://localhost:8000](http://localhost:8000).
The admin interface is at [http://localhost:8000/admin/](http://localhost:8000/admin/).

### Using the Docker Hub Image

You can run Open GRC directly from the published image without cloning the repository.

Create a `docker-compose.yml` file:

```yaml
services:
  web:
    image: frousselet/open-grc:latest
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
    depends_on:
      db:
        condition: service_healthy

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

## Licence

MIT
