# Assistant module (Ask Cairn)

Optional natural-language question mode embedded in the command palette (Ctrl+K). An LLM routes the user's question to a curated allowlist of read-only MCP tools executed in-process with the requesting user; the answer displays the real matching records as clickable cards plus a short AI-labeled summary sentence.

The backend is a **pluggable provider** (`assistant/providers/`): [Mistral AI](https://mistral.ai/) (a third-party, EU-hosted API) by default, with a self-hosted [Ollama](https://ollama.com/) provider still selectable for those who run their own local LLM. With Mistral, the question and the compact record fields used for routing leave the platform (see [Data egress](#data-egress)); with Ollama, data never leaves the host.

Django app: `assistant/`. **No persistent entities, no migrations, no lifecycle workflow**: the feature is stateless (a future query audit log would be a separate decision).

## Pipeline

```
Question (palette or API)
  -> AssistantEngine.ask()
       1 planning call: provider chat completion, JSON-Schema-constrained
       output (Mistral response_format / Ollama format; tool names restricted
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

Key code: `assistant/engine.py` (loop), `assistant/catalog.py` (allowlist), `assistant/providers/` (`base.py` error taxonomy + `get_client()` factory, `mistral.py`, `ollama.py`), `assistant/prompts.py` (model-facing English prompts).

## Settings

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `AI_ASSISTANT_ENABLED` | `False` | Feature flag; when off the palette behaves exactly as before |
| `AI_ASSISTANT_PROVIDER` | `mistral` | Backend selector: `mistral` (third-party API) or `ollama` (self-hosted) |
| `AI_ASSISTANT_API_KEY` | `""` | Mistral API key (required when the provider is `mistral`) |
| `AI_ASSISTANT_BASE_URL` | `https://api.mistral.ai/v1` | OpenAI-compatible API base URL (Mistral provider) |
| `AI_ASSISTANT_MODEL` | `mistral-small-latest` | Chat model; a Mistral model id, or an Ollama model when `provider=ollama` |
| `AI_ASSISTANT_MAX_TOKENS` | `1024` | Completion length cap (Mistral provider) |
| `AI_ASSISTANT_CONNECT_TIMEOUT` | `2` | Seconds; fast fail when the backend is unreachable |
| `AI_ASSISTANT_TIMEOUT` | `30` | Seconds per LLM call |
| `AI_ASSISTANT_MAX_TOOL_ROUNDS` | `3` | Hard cap on plan steps (also enforced in the plan JSON Schema) |
| `AI_ASSISTANT_MAX_RECORDS_PER_TOOL` | `5` | Limit clamp applied to every tool call |
| `AI_ASSISTANT_OLLAMA_URL` | `http://ollama:11434` | Ollama provider only: base URL of the local service |
| `AI_ASSISTANT_NUM_CTX` | `8192` | Ollama provider only: context window |
| `AI_ASSISTANT_ROUTING_THINK` | `False` | Ollama provider only: chain-of-thought during planning (thinking models) |

## Tool allowlist

Hard-coded in `assistant/catalog.py` (23 tools, strictly `list_*` / `get_*`). The routing JSON Schema constrains the tool name to this set at decoding time; the engine re-validates server-side. Permissions are those of the underlying MCP tools (nothing re-declared):

| Tool | Permission |
| ---- | ---------- |
| `list_management_reviews`, `get_management_review`, `list_management_review_decisions`, `list_isms_changes` | `reports.management_review.read` |
| `list_risks`, `get_risk` | `risks.risk.read` |
| `list_risk_treatment_plans` | `risks.treatment.read` |
| `list_risk_acceptances` | `risks.acceptance.read` |
| `list_action_plans`, `get_action_plan` | `compliance.action_plan.read` |
| `list_compliance_assessments` | `compliance.assessment.read` |
| `list_frameworks`, `get_framework_compliance_summary` | `compliance.framework.read` |
| `list_requirements`, `get_requirement` | `compliance.requirement.read` |
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
| REST API | `POST /api/v1/assistant/ask/` | Session / JWT / OAuth; body `{"q": "...", "language": "fr"}`; 200 with `{summary, language, degraded, results, refused_tools}`; 503 + code (`assistant_disabled`, `assistant_unreachable`, `model_missing`, `model_error`); 400 on invalid `q` |
| MCP | `ask_assistant` tool | Same outcome shape; error envelope when unavailable |

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

### Self-hosted alternative (Ollama)

For a no-egress deployment, point the assistant at your own Ollama instance:

```bash
AI_ASSISTANT_PROVIDER=ollama
AI_ASSISTANT_OLLAMA_URL=http://host.docker.internal:11434
AI_ASSISTANT_MODEL=qwen3:4b
```

`qwen3:1.7b` runs CPU-only (~2-4 GB RAM at 8k context) but its French phrasing slips occasionally; clean phrasing starts around the 4B class, which needs GPU-backed inference. The records shown as cards are always exact regardless of the model; only the summary sentence wording varies.

## Data egress

With the **Mistral** provider, data leaves the platform on two calls per question:

- **Planning call**: the user's question plus the catalog tool signatures (no record data yet).
- **Summary call**: the question plus the compact fields of the matching records (titles, statuses, dates), after `engine._strip_identifiers` recursively removes `id` / `*_id` keys and UUID-shaped values. Internal identifiers are never sent.

Mistral is EU-hosted. The feature is **off by default** and must be enabled deliberately (`AI_ASSISTANT_ENABLED`), which is the opt-in: enabling it acknowledges that question text and the above record fields are sent to the third-party provider under its data-processing terms. The API key is read from the environment and never logged or surfaced in error messages. For a deployment that must keep all data on-premises, use the Ollama provider above (no egress).

## Future work

- Semantic search over record contents (embeddings, pgvector) for fuzzy "find things about X" questions.
- Optional query audit log (persistent entity, would then follow the lifecycle/workflow conventions).
- Streaming the summary sentence into the palette.
