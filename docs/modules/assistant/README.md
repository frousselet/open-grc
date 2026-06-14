# Assistant module (Ask Cairn)

Optional natural-language question mode embedded in the command palette (Ctrl+K). An LLM routes the user's question to a curated allowlist of read-only MCP tools executed in-process with the requesting user; the answer displays the real matching records as clickable cards plus a short AI-labeled summary sentence.

The backend is a **pluggable provider** (`assistant/providers/`): [Mistral AI](https://mistral.ai/) (a third-party, EU-hosted API) by default, an `openai` provider for [OpenAI](https://openai.com/) (ChatGPT) and any other OpenAI-compatible endpoint (vLLM, LiteLLM, LocalAI, Together, Groq... selected via `AI_ASSISTANT_BASE_URL`), an `anthropic` provider for [Claude](https://www.anthropic.com/claude) (native Messages API), and a self-hosted [Ollama](https://ollama.com/) provider for those who run their own local LLM. With Mistral, OpenAI or Claude, the question and the compact record fields used for routing leave the platform (see [Data egress](#data-egress)); with Ollama, data never leaves the host.

Django app: `assistant/`. The only persistent entity is **answer feedback** (`AssistantFeedback`, see [Feedback](#feedback)); the question/answer pipeline itself is stateless (no lifecycle workflow, no history). `AssistantFeedback` is a plain log row (like `AccessLog`), not a domain `BaseModel`.

## Pipeline

```
Question (palette or API)
  -> AssistantEngine.ask()
       1 planning call: provider chat completion, JSON-Schema-constrained
       output (Mistral/OpenAI response_format / Claude forced tool use /
       Ollama format; tool names restricted
       by enum to the catalog, at most AI_ASSISTANT_MAX_TOOL_ROUNDS steps;
       "$1.id" placeholders reference earlier steps)
       -> deterministic engine-side execution of the plan:
            sanitization (allowlist re-check, argument whitelist, limit
            clamp), placeholder resolution from the parent step's first
            record (with a one-shot retry without the status filter when
            the parent matches nothing), id-grounding check
            -> in-process execution through McpServer.get_tool() with the
               session user: existing @require_perm decorators and scope
               filters apply, nothing is bypassed
       -> 1 summary call (plain text, user's language, identifier-stripped
          data only)
  -> rendered partial: AI summary + record cards with links + disclaimer
```

Sequencing is deliberately NOT left to the model round after round: very
small models are unreliable at deciding mid-conversation whether to chain a
child call. They are good at one-shot constrained planning, so the engine
owns the execution order, the id plumbing and the fallbacks.

Key code: `assistant/engine.py` (loop), `assistant/catalog.py` (allowlist), `assistant/providers/` (`base.py` error taxonomy + `get_client()` factory, `openai_compatible.py` generic OpenAI client, `mistral.py` thin subclass, `anthropic.py` native Claude client, `ollama.py`), `assistant/prompts.py` (model-facing English prompts).

## Settings

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `AI_ASSISTANT_ENABLED` | `False` | Feature flag; when off the palette behaves exactly as before |
| `AI_ASSISTANT_PROVIDER` | `mistral` | Backend selector: `mistral` (third-party API), `openai` (OpenAI / any OpenAI-compatible endpoint), `anthropic` (Claude, native Messages API), or `ollama` (self-hosted) |
| `AI_ASSISTANT_API_KEY` | `""` | API key. Required for `mistral` / `openai` (sent as a Bearer token) and `anthropic` (sent as the `x-api-key` header) |
| `AI_ASSISTANT_BASE_URL` | `""` | API base URL. Empty falls back to the provider default (`mistral` -> `https://api.mistral.ai/v1`, `openai` -> `https://api.openai.com/v1`, `anthropic` -> `https://api.anthropic.com/v1`). Set it to target a custom OpenAI-compatible gateway (vLLM, LiteLLM, LocalAI, Together, Groq...) |
| `AI_ASSISTANT_MODEL` | `mistral-small-latest` | Chat model id served by the backend (e.g. `gpt-4o-mini` for OpenAI, `claude-opus-4-8` for Anthropic, an Ollama model when `provider=ollama`) |
| `AI_ASSISTANT_MAX_TOKENS` | `1024` | Completion length cap (`mistral` / `openai` / `anthropic` providers) |
| `AI_ASSISTANT_SEMANTIC_ENABLED` | `False` | Enable meaning-based requirement search (see [Semantic search](#semantic-search)). Not available with the `anthropic` provider (Anthropic has no embeddings API) |
| `AI_ASSISTANT_EMBED_MODEL` | `mistral-embed` | Embedding model used to index and query requirements (set to e.g. `text-embedding-3-small` for OpenAI) |
| `AI_ASSISTANT_CONNECT_TIMEOUT` | `2` | Seconds; fast fail when the backend is unreachable |
| `AI_ASSISTANT_TIMEOUT` | `30` | Seconds per LLM call |
| `AI_ASSISTANT_MAX_TOOL_ROUNDS` | `3` | Hard cap on plan steps (also enforced in the plan JSON Schema) |
| `AI_ASSISTANT_MAX_RECORDS_PER_TOOL` | `5` | Limit clamp applied to every tool call |
| `AI_ASSISTANT_OLLAMA_URL` | `http://ollama:11434` | Ollama provider only: base URL of the local service |
| `AI_ASSISTANT_NUM_CTX` | `8192` | Ollama provider only: context window |
| `AI_ASSISTANT_ROUTING_THINK` | `False` | Ollama provider only: chain-of-thought during planning (thinking models) |

## Tool allowlist

Hard-coded in `assistant/catalog.py` (24 read-only tools: `list_*` / `get_*` plus `semantic_search_requirements`). The routing JSON Schema constrains the tool name to the active set at decoding time; the engine re-validates server-side. The semantic tool is only offered to the planner when `AI_ASSISTANT_SEMANTIC_ENABLED` is on (see [Semantic search](#semantic-search)). Permissions are those of the underlying MCP tools (nothing re-declared):

| Tool | Permission |
| ---- | ---------- |
| `list_management_reviews`, `get_management_review`, `list_management_review_decisions`, `list_isms_changes` | `reports.management_review.read` |
| `list_risks`, `get_risk` | `risks.risk.read` |
| `list_risk_treatment_plans` | `risks.treatment.read` |
| `list_risk_acceptances` | `risks.acceptance.read` |
| `list_action_plans`, `get_action_plan` | `compliance.action_plan.read` |
| `list_compliance_assessments` | `compliance.assessment.read` |
| `list_frameworks`, `get_framework_compliance_summary` | `compliance.framework.read` |
| `list_requirements`, `get_requirement`, `semantic_search_requirements` | `compliance.requirement.read` |
| `list_indicators`, `list_indicator_measurements` | `context.indicator.read` |
| `list_issues` | `context.issue.read` |
| `list_objectives` | `context.objective.read` |
| `list_scopes` | `context.scope.read` |
| `list_suppliers` | `assets.supplier.read` |
| `list_essential_assets` | `assets.essential_asset.read` |
| `list_support_assets` | `assets.support_asset.read` |

## Business rules

- **RG-AI-01 - Read-only surface**: the assistant can only reach tools in the catalog, all read-only. A model response naming any other tool is refused server-side (and is already impossible to decode through the constrained schema). Worst case is a useless answer, never a write or an unauthorized read.
- **RG-AI-02 - Bounded execution**: exactly two LLM calls per question (one plan, one summary) and at most `AI_ASSISTANT_MAX_TOOL_ROUNDS` tool executions (plus at most one deterministic parent retry without its status filter).
- **RG-AI-03 - AI output is labeled and escaped**: the summary sentence carries the AI badge and disclaimer, renders through Django autoescaping, and the cards are built server-side from ORM records; the model never produces URLs or markup.
- **RG-AI-04 - Permissions enforced by the platform**: every data access runs the regular MCP handler with the calling user; `@require_perm` denials surface as a neutral "some results were hidden" notice, never as data.
- **RG-AI-05 - Graceful degradation**: assistant disabled, backend unreachable (missing API key, network, server error) or unknown model produce friendly i18n states in the palette; normal search is never affected. A summary-stage failure keeps the record cards (degraded mode).
- **RG-AI-06 - Id grounding**: id-like arguments (`id`, `*_id`) must come from a `$N.id` placeholder resolved against an earlier step's results, or be pasted verbatim in the question. Literal ids from nowhere (typically copied from the prompt examples by the model) are refused without executing the tool.
- **RG-AI-07 - No identifiers in the summary**: the payload fed to the summary stage is recursively stripped of `id` / `*_id` keys and UUID-shaped values, and the prompt forbids citing identifiers; when the data lacks the requested information the model must say so and defer to the record cards.

## Prompt-injection posture

Record contents are user-authored data already visible to the requesting user. They re-enter the model only at the summary stage and can at most steer the wording of one sentence, which is rendered escaped and labeled as AI. Tools are read-only; there is no write or markup escalation path.

## Interfaces

| Surface | Path | Notes |
| ------- | ---- | ----- |
| Palette partial | `POST /api/assistant/ask/` (`assistant:ask`) | Session auth, returns the HTML partial, always 200 with error states inside |
| Feedback partial | `POST /api/assistant/feedback/` (`assistant:feedback`) | Session auth; body `{answer_id, rating, comment}`; returns a small confirmation partial |
| REST API | `POST /api/v1/assistant/ask/` | Session / JWT / OAuth; body `{"q": "...", "language": "fr"}`; 200 with `{summary, language, degraded, results, refused_tools}`; 503 + code (`assistant_disabled`, `assistant_unreachable`, `model_missing`, `model_error`); 400 on invalid `q` |
| REST API | `/api/v1/assistant/feedback/` | DRF viewset: `POST` to submit (any authenticated user); `GET` list/retrieve, `GET .../export/`, and `POST .../{id}/resolve/` \| `.../unresolve/` require `system.assistant_feedback.read` |
| MCP | `ask_assistant` tool | Same outcome shape; error envelope when unavailable |
| MCP | `list_assistant_feedback` tool | Read-only; requires `system.assistant_feedback.read`; for quality analysis |

## Feedback

Each answer in the palette shows a thumbs up / thumbs down control plus an optional free-text comment. Submitting records an `AssistantFeedback` row capturing the prompt, the interface language, the LLM response (summary and the returned record cards), the provider/model, the rating and the comment.

To keep the stored feedback faithful (and not spoofable from the client), the answer is stashed in the session at render time under a one-time token; the feedback POST sends only `{answer_id, rating, comment}` and the server rebuilds the row from the stashed answer, then clears the token (one feedback per answer).

The collected feedback is meant to be exported and handed to an LLM (Claude Code or other) to improve the assistant:

- **In-app Administration page** (`assistant:feedback-list`, sidebar "Assistant feedback"): a server-rendered list with search (question / comment), rating and period filters and an **"Export JSON"** button that downloads the filtered set (`assistant:feedback-export`). This is the primary surface, consistent with the Access log / Action log pages.
- **REST**: `GET /api/v1/assistant/feedback/export/` returns the same structured set (honouring the list filters).
- **MCP**: `list_assistant_feedback` lets an LLM pull the feedback directly.
- **Django admin** (`/admin/`, superusers): the `AssistantFeedback` model is also registered with an "Export selected feedback as JSON" action.

Reading, exporting and the MCP tool require the `system.assistant_feedback.read` permission (granted to Super Admin, Admin, RSSI/DPO and Auditeur); submitting feedback only requires being authenticated.

**Closing the loop**: once a feedback item has been acted on, mark it **corrected** (the in-app list "Mark corrected" button, the admin "Mark selected as corrected" action, or `POST /api/v1/assistant/feedback/{id}/resolve/`). Corrected items are excluded from future exports by default: the in-app list defaults to the "Open" filter and the Export button mirrors it, `GET .../feedback/export/` and the `list_assistant_feedback` MCP tool both drop corrected rows unless `include_resolved=true`. This keeps each export to the improvement LLM focused on still-open feedback. Corrected items remain visible via the "Corrected"/"All" filters and can be reopened.

## Operations

Default (Mistral AI): obtain an API key from the Mistral console, then set in `.env`:

```bash
AI_ASSISTANT_ENABLED=True
AI_ASSISTANT_PROVIDER=mistral
AI_ASSISTANT_API_KEY=your-mistral-api-key
AI_ASSISTANT_MODEL=mistral-small-latest
# restart web
```

No sidecar, no model download, no GPU. `mistral-small-latest` is the recommended default: a good cost/quality balance for the JSON tool routing and the short FR/EN summary sentence. `ministral-3b`/`8b` are cheaper but weaker on multi-step plans; `mistral-medium-latest` improves phrasing at a higher per-call cost. Any model id served by the configured `AI_ASSISTANT_BASE_URL` works without code changes.

To enable meaning-based requirement search, add `AI_ASSISTANT_SEMANTIC_ENABLED=True` and build the index once: `docker compose exec web python manage.py rebuild_semantic_index` (re-run after bulk requirement imports). See [Semantic search](#semantic-search).

### OpenAI and OpenAI-compatible endpoints

The `openai` provider targets OpenAI (ChatGPT) out of the box, and any other backend that implements the OpenAI `/chat/completions` and `/embeddings` API (vLLM, LiteLLM, LocalAI, Together, Groq...) by overriding the base URL:

```bash
AI_ASSISTANT_ENABLED=True
AI_ASSISTANT_PROVIDER=openai
AI_ASSISTANT_API_KEY=your-api-key
AI_ASSISTANT_MODEL=gpt-4o-mini
# AI_ASSISTANT_BASE_URL=https://api.openai.com/v1   # default; set for a custom gateway
# For semantic search, pick a matching embedding model:
# AI_ASSISTANT_EMBED_MODEL=text-embedding-3-small
```

`AI_ASSISTANT_BASE_URL` defaults to `https://api.openai.com/v1` for this provider; point it at any compatible gateway to route through your own deployment. The key is sent as a `Bearer` token. The request/response handling is shared with the Mistral provider (which is itself an OpenAI-compatible client), so the structured-output routing and the `json_object` fallback behave identically.

### Claude (Anthropic)

Claude is not OpenAI-compatible : it uses the native Messages API (`POST /v1/messages`, `x-api-key` header, top-level `system`, `content` block list). The `anthropic` provider implements that directly:

```bash
AI_ASSISTANT_ENABLED=True
AI_ASSISTANT_PROVIDER=anthropic
AI_ASSISTANT_API_KEY=your-anthropic-api-key
AI_ASSISTANT_MODEL=claude-opus-4-8
# AI_ASSISTANT_BASE_URL=https://api.anthropic.com/v1   # default
```

`AI_ASSISTANT_MODEL` must be a Claude model id (e.g. `claude-opus-4-8`, `claude-haiku-4-5`); the global default `mistral-small-latest` is not valid here, so set it explicitly. Routing uses **forced tool use** (a single `plan` tool whose `input_schema` is the routing schema, with `tool_choice` pinned to it) - the reliable structured-output path on Claude. No `temperature` or `thinking` is sent, since both are rejected on the current Opus family.

**Semantic search is not available with this provider**: Anthropic has no embeddings endpoint, so `embed()` raises a clear error. To use semantic search, keep `AI_ASSISTANT_SEMANTIC_ENABLED=False`, or index with another provider (Mistral / OpenAI / Ollama).

### Self-hosted alternative (Ollama)

For a no-egress deployment, point the assistant at your own Ollama instance:

```bash
AI_ASSISTANT_PROVIDER=ollama
AI_ASSISTANT_OLLAMA_URL=http://host.docker.internal:11434
AI_ASSISTANT_MODEL=qwen3:4b
```

`qwen3:1.7b` runs CPU-only (~2-4 GB RAM at 8k context) but its French phrasing slips occasionally; clean phrasing starts around the 4B class, which needs GPU-backed inference. The records shown as cards are always exact regardless of the model; only the summary sentence wording varies.

## Data egress

With the **Mistral**, **OpenAI** or **Claude** provider, data leaves the platform on two calls per question:

- **Planning call**: the user's question plus the catalog tool signatures (no record data yet).
- **Summary call**: the question plus the compact fields of the matching records (titles, statuses, dates), after `engine._strip_identifiers` recursively removes `id` / `*_id` keys and UUID-shaped values. Internal identifiers are never sent.

Mistral is EU-hosted; OpenAI, Anthropic and other third-party gateways are hosted under their own terms (and possibly outside the EU - check the provider before enabling). The feature is **off by default** and must be enabled deliberately (`AI_ASSISTANT_ENABLED`), which is the opt-in: enabling it acknowledges that question text and the above record fields are sent to the configured third-party provider under its data-processing terms. The API key is read from the environment and never logged or surfaced in error messages. For a deployment that must keep all data on-premises, use the Ollama provider above (no egress), or point the `openai` provider at a self-hosted OpenAI-compatible gateway. With semantic search enabled (not available with the `anthropic` provider), requirement text is additionally sent to the embedding model at index-build time and the query text at search time.

## Semantic search

Lexical search (`list_requirements` `search`) is substring-based and language-sensitive: a French topic question (e.g. "séparation des tâches") does not match an English control title ("Segregation of duties"). Feedback surfaced exactly this recall gap. Semantic search closes it with embeddings.

How it works (opt-in via `AI_ASSISTANT_SEMANTIC_ENABLED`):

- **Index**: the rebuild (`assistant.semantic.rebuild_index`, also exposed as `manage.py rebuild_semantic_index`) embeds each requirement (number + name + description + guidance) via the provider's embedding model (`AI_ASSISTANT_EMBED_MODEL`, default `mistral-embed`) and stores the vector in `assistant.SemanticIndex`. The embedding is a plain JSON list of floats, so the column is portable across PostgreSQL and the SQLite test DB - no `pgvector` extension or Docker image change. It is idempotent (a `content_hash` skips unchanged rows) and prunes embeddings of deleted requirements.
- **Query**: the catalog gains `semantic_search_requirements(query, limit)`. The planner is taught (via a routing example) to pick it for conceptual / topic questions. The handler embeds the query and ranks stored requirement vectors by cosine similarity **in Python** - the corpus (hundreds to low thousands of requirements) is small enough that brute force is instant, so no vector index is needed. It returns real requirements, so the rest of the pipeline (cards, summary, permissions) is unchanged.

The tool requires `compliance.requirement.read` and is only offered to the planner when the flag is on (otherwise it is absent from the routing prompt and the plan schema, though it stays in `TOOL_CATALOG` for server-side execution/validation). If the corpus ever grows to a scale where brute-force cosine is too slow, `SemanticIndex` can be backed by `pgvector` without changing the tool contract.

### Keeping the index fresh

The index drifts as requirements are created, edited or deleted, so it is refreshed automatically through several complementary mechanisms (all no-ops when the feature is off). Embedding calls a third-party provider, so they are kept **off the request path**: a requirement save never triggers an inline embed.

- **On delete (immediate)**: a `post_delete` signal on `Requirement` (`assistant/signals.py`, wired from `AssistantConfig.ready()`) prunes the requirement's `SemanticIndex` row. This is a network-free DB delete, safe even when semantic search is disabled.
- **On startup**: when a server process boots (uvicorn / `runserver`) with the feature on, `AssistantConfig.ready()` launches a guarded background thread that runs the rebuild once (skipped for management commands like `migrate`/`test`, so the work never blocks boot and a slow provider can't wedge startup).
- **On demand (admin)**: the Company settings page (in-app Administration, gated by `system.config.update`) shows index status (indexed / total requirements, last updated, embedding model) and an **"Update the index now"** button that triggers a background rebuild (`assistant:rebuild-semantic-index`). The card warns when the active provider has no embeddings (e.g. `anthropic`).
- **Scheduled (recommended backstop)**: run `manage.py rebuild_semantic_index` from cron (see [installation.md](../../installation.md)). It is the reliable, self-healing mechanism - it catches anything the others missed (e.g. an edit that no rebuild has run for yet, or an embed that failed transiently).

A cache lock (`assistant.semantic.rebuild_index_async`) dedupes overlapping triggers (startup + button + a double click), and the startup/admin rebuilds run in daemon threads that close their own DB connections. New and edited requirements become searchable at the next rebuild (startup, daily cron, or the admin button) - lexical search covers them immediately in the meantime.

## Future work

- Extend semantic search to other entities (risks, objectives, assets) beyond requirements.
- Immediate re-embed on requirement *save* (currently new/edited requirements are picked up at the next rebuild - startup, daily cron, or the admin button - rather than inline, to keep provider calls off the request path).
- Optional query audit log (persistent entity, would then follow the lifecycle/workflow conventions).
- Streaming the summary sentence into the palette.
