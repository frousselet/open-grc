"""Curated allowlist of read-only MCP tools the assistant may invoke.

The catalog is hard-coded on purpose: even if the MCP registry grows or
changes, the assistant can never reach a tool that is not listed here, and
every listed tool is strictly read-only (``list_*`` / ``get_*``). Permission
checks are NOT re-declared here; they are enforced by the ``@require_perm``
decorators already wrapping each MCP tool handler.
"""

from dataclasses import dataclass

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

READ_ONLY_PREFIXES = ("list_", "get_")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    label: object  # lazy translation
    icon: str
    signature: str  # one-line description injected in the routing prompt
    allowed_args: frozenset
    title_fields: tuple = ("reference", "name")
    subtitle_field: str = "status"
    # Extra record fields kept when feeding results back to the model.
    summary_fields: tuple = ()
    # Detail route reversed with the record id, or None when no page exists.
    detail_route: str = None
    # Record key holding the pk used for the URL (defaults to "id"; lets
    # child records without a detail page link to their parent object).
    url_pk_field: str = "id"

    def record_url(self, record):
        if not self.detail_route:
            return ""
        pk = record.get(self.url_pk_field)
        if not pk:
            return ""
        try:
            return reverse(self.detail_route, kwargs={"pk": pk})
        except Exception:
            return ""

    def record_title(self, record):
        parts = [str(record.get(f) or "").strip() for f in self.title_fields]
        return " ".join(p for p in parts if p)

    def record_subtitle(self, record):
        if not self.subtitle_field:
            return ""
        value = record.get(self.subtitle_field)
        return str(value).replace("_", " ") if value else ""

    def build_card(self, record):
        return {
            "title": self.record_title(record) or str(record.get("id", "")),
            "subtitle": self.record_subtitle(record),
            "url": self.record_url(record),
            "icon": self.icon,
        }

    def compact_record(self, record):
        """Reduce a record to the fields the model needs for the next round."""
        keep = ("id",) + self.title_fields
        if self.subtitle_field:
            keep += (self.subtitle_field,)
        keep += self.summary_fields
        return {k: record[k] for k in keep if record.get(k) not in (None, "")}


def _spec(name, label, icon, signature, args, **kwargs):
    return ToolSpec(
        name=name,
        label=label,
        icon=icon,
        signature=signature,
        allowed_args=frozenset(args),
        **kwargs,
    )


_SPECS = [
    # Management review (ISO 27001:2022 clause 9.3)
    _spec(
        "list_management_reviews",
        _("Management reviews"),
        "bi-clipboard-data",
        "list_management_reviews(status: planned|in_preparation|held|closed|cancelled, scope_id, limit):"
        " management reviews, newest first",
        ("status", "scope_id", "limit", "offset"),
        title_fields=("reference", "title"),
        summary_fields=("held_date", "planned_date"),
        detail_route="reports:management-review-detail",
    ),
    _spec(
        "get_management_review",
        _("Management reviews"),
        "bi-clipboard-data",
        "get_management_review(id): one management review with decision and change counts",
        ("id",),
        title_fields=("reference", "title"),
        summary_fields=("held_date", "summary"),
        detail_route="reports:management-review-detail",
    ),
    _spec(
        "list_management_review_decisions",
        _("Decisions"),
        "bi-check2-square",
        "list_management_review_decisions(review_id, status: pending|ongoing|completed|cancelled, limit):"
        " decisions recorded during a management review",
        ("review_id", "status", "limit", "offset"),
        title_fields=("reference", "title"),
        summary_fields=("due_date", "priority", "category"),
        detail_route="reports:decision-detail",
    ),
    _spec(
        "list_isms_changes",
        _("ISMS changes"),
        "bi-arrow-repeat",
        "list_isms_changes(review_id, limit): ISMS changes decided during management reviews",
        ("review_id", "limit", "offset"),
        title_fields=("reference", "title"),
        summary_fields=("change_type", "target_date"),
        detail_route="reports:management-review-detail",
        url_pk_field="review",
    ),
    # Risks
    _spec(
        "list_risks",
        _("Risks"),
        "bi-radioactive",
        "list_risks(search, status: identified|analyzed|evaluated|treatment_planned|treatment_in_progress"
        "|treated|accepted|closed|monitoring, priority, limit): risk register entries",
        ("search", "status", "priority", "assessment_id", "limit", "offset"),
        summary_fields=("current_risk_level", "treatment_decision"),
        detail_route="risks:risk-detail",
    ),
    _spec(
        "get_risk",
        _("Risks"),
        "bi-radioactive",
        "get_risk(id): one risk with its likelihood, impact and treatment details",
        ("id",),
        summary_fields=("current_risk_level", "treatment_decision"),
        detail_route="risks:risk-detail",
    ),
    _spec(
        "list_risk_treatment_plans",
        _("Treatment Plans"),
        "bi-bandaid",
        "list_risk_treatment_plans(search, status: planned|in_progress|completed|cancelled|overdue,"
        " risk_id, limit): risk treatment plans",
        ("search", "status", "risk_id", "limit", "offset"),
        summary_fields=("treatment_type",),
        detail_route="risks:treatment-plan-detail",
    ),
    _spec(
        "list_risk_acceptances",
        _("Risk acceptances"),
        "bi-check-circle",
        "list_risk_acceptances(risk_id, status: active|expired|revoked|renewed, limit): risk acceptances",
        ("risk_id", "status", "limit", "offset"),
        title_fields=("reference",),
        summary_fields=("valid_until",),
        detail_route="risks:acceptance-detail",
    ),
    # Compliance
    _spec(
        "list_action_plans",
        _("Action Plans"),
        "bi-card-checklist",
        "list_action_plans(search, status, priority: low|medium|high|critical, limit):"
        " compliance action plans",
        ("search", "status", "priority", "limit", "offset"),
        summary_fields=("target_date",),
        detail_route="compliance:action-plan-detail",
    ),
    _spec(
        "get_action_plan",
        _("Action Plans"),
        "bi-card-checklist",
        "get_action_plan(id): one action plan with its remediation details",
        ("id",),
        summary_fields=("target_date",),
        detail_route="compliance:action-plan-detail",
    ),
    _spec(
        "list_compliance_assessments",
        _("Compliance Assessments"),
        "bi-clipboard-check",
        "list_compliance_assessments(search, status, limit): compliance assessments (audits)",
        ("search", "status", "limit", "offset"),
        summary_fields=("overall_compliance_level",),
        detail_route="compliance:assessment-detail",
    ),
    _spec(
        "list_frameworks",
        _("Frameworks"),
        "bi-journal-check",
        "list_frameworks(search, status, limit): compliance frameworks and standards",
        ("search", "status", "type", "category", "limit", "offset"),
        detail_route="compliance:framework-detail",
    ),
    _spec(
        "list_requirements",
        _("Requirements"),
        "bi-list-check",
        "list_requirements(search, framework_id, compliance_status, type, priority, limit):"
        " framework requirements / controls (e.g. ISO 27001 Annex A 'A.5.3'); search matches"
        " the reference, number, name and text",
        ("search", "framework_id", "section_id", "compliance_status", "type", "category",
         "priority", "status", "limit", "offset"),
        title_fields=("reference", "name"),
        subtitle_field="compliance_status",
        summary_fields=("description", "guidance"),
        detail_route="compliance:requirement-detail",
    ),
    _spec(
        "get_requirement",
        _("Requirements"),
        "bi-list-check",
        "get_requirement(id): one requirement / control with its full text, guidance and"
        " compliance status",
        ("id",),
        title_fields=("reference", "name"),
        subtitle_field="compliance_status",
        summary_fields=("description", "guidance"),
        detail_route="compliance:requirement-detail",
    ),
    _spec(
        "get_framework_compliance_summary",
        _("Frameworks"),
        "bi-journal-check",
        "get_framework_compliance_summary(id): compliance rate and status distribution for one framework",
        ("id",),
    ),
    # Context
    _spec(
        "list_indicators",
        _("Indicators"),
        "bi-speedometer2",
        "list_indicators(search, status, indicator_type, limit): performance and security indicators",
        ("search", "status", "indicator_type", "limit", "offset"),
        detail_route="context:indicator-detail",
    ),
    _spec(
        "list_indicator_measurements",
        _("Measurements"),
        "bi-graph-up",
        "list_indicator_measurements(indicator_id, limit): measurements recorded for one indicator",
        ("indicator_id", "limit", "offset"),
        title_fields=("value",),
        subtitle_field="recorded_at",
        detail_route="context:indicator-detail",
        url_pk_field="indicator_id",
    ),
    _spec(
        "list_issues",
        _("Issues"),
        "bi-exclamation-diamond",
        "list_issues(search, type: internal|external, status, limit): internal and external issues",
        ("search", "type", "category", "status", "limit", "offset"),
        detail_route="context:issue-detail",
    ),
    _spec(
        "list_objectives",
        _("Objectives"),
        "bi-flag",
        "list_objectives(search, status, limit): information security objectives",
        ("search", "category", "type", "status", "limit", "offset"),
        detail_route="context:objective-detail",
    ),
    _spec(
        "list_scopes",
        _("Scopes"),
        "bi-bullseye",
        "list_scopes(search, limit): organizational scopes / perimeters",
        ("search", "workflow_state", "limit", "offset"),
        subtitle_field="workflow_state",
        detail_route="context:scope-detail",
    ),
    # Assets
    _spec(
        "list_suppliers",
        _("Suppliers"),
        "bi-truck",
        "list_suppliers(search, criticality, status, limit): suppliers and service providers",
        ("search", "type", "criticality", "status", "limit", "offset"),
        summary_fields=("criticality",),
        detail_route="assets:supplier-detail",
    ),
    _spec(
        "list_essential_assets",
        _("Essential Assets"),
        "bi-gem",
        "list_essential_assets(search, type: business_process|information, status, limit):"
        " essential assets (processes, information)",
        ("search", "type", "category", "status", "limit", "offset"),
        detail_route="assets:essential-asset-detail",
    ),
    _spec(
        "list_support_assets",
        _("Support Assets"),
        "bi-hdd-network",
        "list_support_assets(search, type: hardware|software|network|person|service|paper, status,"
        " limit): support assets (IT infrastructure)",
        ("search", "type", "category", "status", "environment", "limit", "offset"),
        detail_route="assets:support-asset-detail",
    ),
]

TOOL_CATALOG = {spec.name: spec for spec in _SPECS}


def plan_schema(max_steps):
    """JSON Schema constraining the model's one-shot execution plan.

    The ``enum`` on the tool name makes any tool outside the catalog
    impossible to decode; the engine still re-validates server-side.
    """
    return {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "maxItems": max_steps,
                "items": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "enum": sorted(TOOL_CATALOG)},
                        "arguments": {"type": "object"},
                    },
                    "required": ["tool"],
                },
            },
        },
        "required": ["steps"],
    }


def catalog_signatures():
    return "\n".join(spec.signature for spec in _SPECS)
