"""Bounded natural-language question engine.

Pipeline: the routing model picks read-only tools from the curated catalog
(max ``AI_ASSISTANT_MAX_TOOL_ROUNDS`` rounds), each tool executes in-process
through the MCP registry with the session user (existing ``@require_perm``
decorators and scope filters apply, nothing is bypassed), then one final
model call produces a short summary sentence from the collected data.
"""

import json
import logging
from dataclasses import dataclass, field

from django.conf import settings

from assistant.catalog import TOOL_CATALOG, routing_schema
from assistant.ollama import (
    AssistantDisabled,
    MalformedModelOutput,
    OllamaClient,
    OllamaUnreachable,
)
from assistant.prompts import routing_prompt, summary_prompt

logger = logging.getLogger(__name__)

# Cap on the serialized tool result re-injected into the model context.
COMPACT_RESULT_MAX_CHARS = 2000

PERMISSION_DENIED = "permission_denied"
TOOL_ERROR = "tool_error"


@dataclass
class ToolRun:
    tool: str
    label: str
    icon: str
    arguments: dict
    records: list = field(default_factory=list)
    cards: list = field(default_factory=list)
    data: object = None
    error: str = None

    def compact_json(self):
        spec = TOOL_CATALOG[self.tool]
        if self.error:
            payload = {"error": self.error}
        elif self.records:
            payload = [spec.compact_record(r) for r in self.records]
        else:
            payload = self.data if self.data is not None else []
        text = json.dumps(payload, default=str, ensure_ascii=False)
        return text[:COMPACT_RESULT_MAX_CHARS]


@dataclass
class AskOutcome:
    question: str
    language: str
    summary: str = None
    degraded: bool = False
    tool_runs: list = field(default_factory=list)
    refused_tools: list = field(default_factory=list)

    @property
    def has_cards(self):
        return any(run.cards for run in self.tool_runs)

    @property
    def permission_denied(self):
        return any(run.error == PERMISSION_DENIED for run in self.tool_runs)

    def as_dict(self):
        return {
            "question": self.question,
            "language": self.language,
            "summary": self.summary,
            "degraded": self.degraded,
            "refused_tools": list(self.refused_tools),
            "results": [
                {
                    "tool": run.tool,
                    "label": run.label,
                    "error": run.error,
                    "records": run.cards,
                }
                for run in self.tool_runs
            ],
        }


def _system(content):
    return {"role": "system", "content": content}


def _user(content):
    return {"role": "user", "content": content}


def _assistant(content):
    return {"role": "assistant", "content": content}


def _extract_records(raw):
    """Normalize a tool result to a list of record dicts.

    Generic list handlers return ``{"total", "items", ...}``, the management
    review tools return a bare list, get handlers return a single dict, and
    aggregate tools (e.g. compliance summaries) return a plain dict.
    """
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        items = raw.get("items")
        if isinstance(items, list):
            return [r for r in items if isinstance(r, dict)]
        if raw.get("id"):
            return [raw]
    return []


class AssistantEngine:
    def __init__(self, user, language="en", client=None):
        self.user = user
        self.language = language or "en"
        self.client = client or OllamaClient()

    def ask(self, question):
        if not settings.AI_ASSISTANT_ENABLED:
            raise AssistantDisabled()
        outcome = AskOutcome(question=question, language=self.language)
        messages = [_system(routing_prompt()), _user(question)]
        for _round in range(settings.AI_ASSISTANT_MAX_TOOL_ROUNDS):
            decision = self.client.chat_json(messages, routing_schema())
            tool_name = decision.get("tool")
            if decision.get("done") or not tool_name:
                break
            spec = TOOL_CATALOG.get(tool_name)
            if spec is None:
                # Unreachable through constrained decoding; kept as a guard.
                outcome.refused_tools.append(str(tool_name))
                break
            args = self._sanitize_arguments(spec, decision.get("arguments"))
            run = self._execute(spec, args)
            outcome.tool_runs.append(run)
            messages.append(_assistant(json.dumps(decision, ensure_ascii=False)))
            messages.append(_user(
                f"Result of {spec.name}: {run.compact_json()}\n"
                'If this answers the question, respond {"done": true}. '
                "Otherwise call the next tool."
            ))
        self._summarize(outcome)
        return outcome

    def _sanitize_arguments(self, spec, arguments):
        args = {}
        for key, value in (arguments or {}).items():
            if key not in spec.allowed_args:
                continue
            if isinstance(value, (dict, list)) or value in (None, ""):
                continue
            args[key] = value
        max_records = settings.AI_ASSISTANT_MAX_RECORDS_PER_TOOL
        if "limit" in spec.allowed_args:
            try:
                requested = int(args.get("limit", max_records))
            except (TypeError, ValueError):
                requested = max_records
            args["limit"] = max(1, min(requested, max_records))
        return args

    def _execute(self, spec, args):
        from mcp.api.views_mcp import get_mcp_server

        run = ToolRun(tool=spec.name, label=str(spec.label), icon=spec.icon, arguments=args)
        tool_def = get_mcp_server().get_tool(spec.name)
        if tool_def is None:
            logger.error("Assistant tool %s missing from the MCP registry", spec.name)
            run.error = TOOL_ERROR
            return run
        try:
            raw = tool_def["handler"](self.user, args)
        except Exception:
            logger.exception("Assistant tool %s failed", spec.name)
            run.error = TOOL_ERROR
            return run
        if isinstance(raw, dict) and raw.get("isError"):
            message = ""
            try:
                message = json.loads(raw["content"][0]["text"]).get("error", "")
            except (KeyError, IndexError, TypeError, ValueError):
                pass
            run.error = (
                PERMISSION_DENIED if str(message).startswith("Permission denied") else TOOL_ERROR
            )
            return run
        run.data = raw
        run.records = _extract_records(raw)[: settings.AI_ASSISTANT_MAX_RECORDS_PER_TOOL]
        run.cards = [spec.build_card(record) for record in run.records]
        return run

    def _summarize(self, outcome):
        successful = [run for run in outcome.tool_runs if not run.error]
        if not successful:
            return
        data = {}
        for run in successful:
            text = run.compact_json() or "[]"
            try:
                data[run.tool] = json.loads(text)
            except ValueError:
                # Truncated payload: pass the raw text through.
                data[run.tool] = text
        if outcome.permission_denied:
            data["note"] = "Some data was not accessible to this user."
        messages = [
            _system(summary_prompt(outcome.language)),
            _user(
                f"Question: {outcome.question}\n"
                f"Data: {json.dumps(data, default=str, ensure_ascii=False)}"
            ),
        ]
        try:
            outcome.summary = self.client.chat_text(messages) or None
        except (OllamaUnreachable, MalformedModelOutput):
            logger.warning("Assistant summary generation failed", exc_info=True)
            outcome.degraded = True
