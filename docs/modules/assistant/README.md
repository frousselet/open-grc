# Assistant module (Ask Cairn)

Optional natural-language question mode embedded in the command palette (Ctrl+K). A very small local LLM, served by an [Ollama](https://ollama.com/) sidecar, routes the user's question to a curated allowlist of read-only MCP tools executed in-process with the requesting user; the answer displays the real matching records as clickable cards plus a short AI-labeled summary sentence. Data never leaves the host.

Django app: `assistant/`. **No persistent entities, no migrations, no lifecycle workflow**: the feature is stateless (a future query audit log would be a separate decision).

## Pipeline

```
Question (palette or API)
  -> AssistantEngine.ask()
       routing loop, max AI_ASSISTANT_MAX_TOOL_ROUNDS rounds:
         Ollama /api/chat, grammar-constrained JSON output
         (format = JSON Schema; tool name restricted by enum to the catalog)
         -> server-side sanitization (allowlist re-check, argument
            whitelist, limit clamp)
         -> in-process execution through McpServer.get_tool() with the
            session user: existing @require_perm decorators and scope
            filters apply, nothing is bypassed
       -> one final summary call (plain text, user's language, data-only)
  -> rendered partial: AI summary + record cards with links + disclaimer
```

Key code: `assistant/engine.py` (loop), `assistant/catalog.py` (allowlist), `assistant/ollama.py` (client + error taxonomy), `assistant/prompts.py` (model-facing English prompts).

## Settings

| Setting | Env var | Default | Purpose |
| ------- | ------- | ------- | ------- |
| `AI_ASSISTANT_ENABLED` | `AI_ASSISTANT_ENABLED` | `False` | Feature flag; when off the palette behaves exactly as before |
| `AI_ASSISTANT_OLLAMA_URL` | `AI_ASSISTANT_OLLAMA_URL` | `http://ollama:11434` | Base URL of the Ollama service |
| `AI_ASSISTANT_MODEL` | `AI_ASSISTANT_MODEL` | `qwen3:1.7b` | Any Ollama chat model; pull it once on the sidecar |
| `AI_ASSISTANT_CONNECT_TIMEOUT` | same | `2` | Seconds; fast fail when the sidecar is absent |
| `AI_ASSISTANT_TIMEOUT` | same | `30` | Seconds per LLM call (CPU inference, cold load included) |
| `AI_ASSISTANT_MAX_TOOL_ROUNDS` | same | `2` | Hard cap on tool-routing rounds |
| `AI_ASSISTANT_MAX_RECORDS_PER_TOOL` | same | `5` | Limit clamp applied to every tool call |
| `AI_ASSISTANT_NUM_CTX` | same | `8192` | Ollama context window |

## Tool allowlist

Hard-coded in `assistant/catalog.py` (21 tools, strictly `list_*` / `get_*`). The routing JSON Schema constrains the tool name to this set at decoding time; the engine re-validates server-side. Permissions are those of the underlying MCP tools (nothing re-declared):

| Tool | Permission |
| ---- | ---------- |
| `list_management_reviews`, `get_management_review`, `list_management_review_decisions`, `list_isms_changes` | `reports.management_review.read` |
| `list_risks`, `get_risk` | `risks.risk.read` |
| `list_risk_treatment_plans` | `risks.treatment.read` |
| `list_risk_acceptances` | `risks.acceptance.read` |
| `list_action_plans`, `get_action_plan` | `compliance.action_plan.read` |
| `list_compliance_assessments` | `compliance.assessment.read` |
| `list_frameworks`, `get_framework_compliance_summary` | `compliance.framework.read` |
| `list_indicators`, `list_indicator_measurements` | `context.indicator.read` |
| `list_issues` | `context.issue.read` |
| `list_objectives` | `context.objective.read` |
| `list_scopes` | `context.scope.read` |
| `list_suppliers` | `assets.supplier.read` |
| `list_essential_assets` | `assets.essential_asset.read` |
| `list_support_assets` | `assets.support_asset.read` |

## Business rules

- **RG-AI-01 - Read-only surface**: the assistant can only reach tools in the catalog, all read-only. A model response naming any other tool is refused server-side (and is already impossible to decode through the constrained schema). Worst case is a useless answer, never a write or an unauthorized read.
- **RG-AI-02 - Bounded loop**: at most `AI_ASSISTANT_MAX_TOOL_ROUNDS` tool calls plus one summary call per question.
- **RG-AI-03 - AI output is labeled and escaped**: the summary sentence carries the AI badge and disclaimer, renders through Django autoescaping, and the cards are built server-side from ORM records; the model never produces URLs or markup.
- **RG-AI-04 - Permissions enforced by the platform**: every data access runs the regular MCP handler with the calling user; `@require_perm` denials surface as a neutral "some results were hidden" notice, never as data.
- **RG-AI-05 - Graceful degradation**: assistant disabled, Ollama unreachable or model not pulled produce friendly i18n states in the palette; normal search is never affected. A summary-stage failure keeps the record cards (degraded mode).

## Prompt-injection posture

Record contents are user-authored data already visible to the requesting user. They re-enter the model only at the summary stage and can at most steer the wording of one sentence, which is rendered escaped and labeled as AI. Tools are read-only; there is no write or markup escalation path.

## Interfaces

| Surface | Path | Notes |
| ------- | ---- | ----- |
| Palette partial | `POST /api/assistant/ask/` (`assistant:ask`) | Session auth, returns the HTML partial, always 200 with error states inside |
| REST API | `POST /api/v1/assistant/ask/` | Session / JWT / OAuth; body `{"q": "...", "language": "fr"}`; 200 with `{summary, language, degraded, results, refused_tools}`; 503 + code (`assistant_disabled`, `assistant_unreachable`, `model_missing`, `model_error`); 400 on invalid `q` |
| MCP | `ask_assistant` tool | Same outcome shape; error envelope when unavailable |

## Operations

```bash
docker compose --profile ai up -d
docker compose exec ollama ollama pull qwen3:1.7b
# .env: AI_ASSISTANT_ENABLED=True, then restart web
```

Sizing: `qwen3:1.7b` needs roughly 2-4 GB of RAM at an 8k context, CPU-only. The first question after a model (re)load takes 10-20 extra seconds; warm questions take roughly 5-20 s for two tool rounds plus the summary. Any other Ollama model can be substituted via `AI_ASSISTANT_MODEL` without code changes.

## Future work

- Semantic search over record contents (embeddings, pgvector) for fuzzy "find things about X" questions.
- Optional query audit log (persistent entity, would then follow the lifecycle/workflow conventions).
- Streaming the summary sentence into the palette.
