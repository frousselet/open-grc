# REST API

Cairn exposes a full REST API under `/api/v1/`, built with Django REST Framework. Every domain resource supports CRUD, filtering, search, ordering, pagination and batch creation. All endpoints enforce the same RBAC permissions and scope-based tenancy as the web UI.

## Base paths

| Module | Base path |
| ------ | --------- |
| Accounts & auth | `/api/v1/` |
| Context | `/api/v1/context/` |
| Assets | `/api/v1/assets/` |
| Compliance | `/api/v1/compliance/` |
| Risks | `/api/v1/risks/` |
| Reports | `/api/v1/reports/` |
| Assistant | `/api/v1/assistant/` |
| MCP & OAuth | `/api/v1/mcp`, `/api/v1/oauth/` |

The detailed per-entity contracts (fields, validation, business rules) are documented in each module's specification: see [docs/modules/](modules/README.md).

## Authentication

Three authentication methods are accepted:

| Method | Use case |
| ------ | -------- |
| Session | Browser-based access (web UI, same-origin AJAX) |
| JWT | API clients - obtain a token pair via `POST /api/v1/auth/login/`, refresh via `POST /api/v1/auth/refresh/` (token rotation enabled) |
| OAuth 2.0 bearer token | MCP and external integrations - see [mcp-server.md](mcp-server.md) |

Auth endpoints:

```
POST /api/v1/auth/login/     # email + password, returns JWT access/refresh pair
POST /api/v1/auth/refresh/   # rotate the refresh token
POST /api/v1/auth/logout/    # invalidate the session/token
GET  /api/v1/auth/me/        # current user profile
```

## Conventions

- **Pagination**: page-number pagination, 25 items per page by default.
- **Filtering**: field filters via query parameters (django-filter), full-text search via `?search=`, ordering via `?ordering=field` / `?ordering=-field`.
- **Identifiers**: all domain objects use UUID primary keys.
- **Lifecycle**: state transitions go through dedicated transition endpoints/actions, never by patching a status field. Deletion is only allowed from a deletable lifecycle state.
- **Batch creation**: list resources accept batch creation (up to 500 objects, non-atomic with partial success reporting).
- **Audit**: every write is recorded in the object's history (django-simple-history) and increments its version.

## Assistant (Ask Cairn)

`POST /api/v1/assistant/ask/` answers a simple natural-language question using the optional local AI assistant (see [docs/modules/assistant/](modules/assistant/README.md)).

Request body: `{"q": "Quelles décisions ont été prises lors de la dernière revue de direction ?", "language": "fr"}` (`language` optional, defaults to the request language).

Response `200`: `{"summary": "...", "language": "fr", "degraded": false, "refused_tools": [], "results": [{"tool": "list_management_review_decisions", "label": "Decisions", "error": null, "records": [{"title": "DECS-1 ...", "subtitle": "pending", "url": "/reports/decisions/<uuid>/", "icon": "bi-check2-square"}]}]}`. Records are real database objects the caller is allowed to read; the summary sentence is AI-generated and must be verified against them.

Errors: `400` on invalid `q`; `503` with a stable code (`assistant_disabled`, `assistant_unreachable`, `model_missing`, `model_error`) when the assistant or its Ollama sidecar is unavailable.
