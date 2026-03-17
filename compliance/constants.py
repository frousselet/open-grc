from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


# ── Framework ──────────────────────────────────────────────

class FrameworkType(models.TextChoices):
    STANDARD = "standard", _("Standard")
    LAW = "law", _("Law")
    REGULATION = "regulation", _("Regulation")
    CONTRACT = "contract", _("Contract")
    INTERNAL_POLICY = "internal_policy", _("Internal policy")
    INDUSTRY_FRAMEWORK = "industry_framework", _("Industry framework")
    OTHER = "other", _("Other")


class FrameworkCategory(models.TextChoices):
    INFORMATION_SECURITY = "information_security", _("Information security")
    PRIVACY = "privacy", _("Data protection")
    RISK_MANAGEMENT = "risk_management", _("Risk management")
    BUSINESS_CONTINUITY = "business_continuity", _("Business continuity")
    CLOUD_SECURITY = "cloud_security", _("Cloud security")
    SECTOR_SPECIFIC = "sector_specific", _("Sector-specific regulations")
    IT_GOVERNANCE = "it_governance", _("IT governance")
    QUALITY = "quality", _("Quality")
    CONTRACTUAL = "contractual", _("Contractual requirements")
    INTERNAL = "internal", _("Internal policies")
    OTHER = "other", _("Other")


class FrameworkStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    UNDER_REVIEW = "under_review", _("Under review")
    DEPRECATED = "deprecated", _("Deprecated")
    ARCHIVED = "archived", _("Archived")


# ── Requirement ────────────────────────────────────────────

class RequirementType(models.TextChoices):
    MANDATORY = "mandatory", _("Mandatory")
    RECOMMENDED = "recommended", _("Recommended")
    OPTIONAL = "optional", _("Optional")


class RequirementCategory(models.TextChoices):
    ORGANIZATIONAL = "organizational", _("Organizational")
    TECHNICAL = "technical", _("Technical")
    PHYSICAL = "physical", _("Physical")
    LEGAL = "legal", _("Legal")
    HUMAN = "human", _("Human")
    OTHER = "other", _("Other")


class ComplianceStatus(models.TextChoices):
    NOT_ASSESSED = "not_assessed", _("Not assessed")
    EVALUATED = "evaluated", _("Evaluation planned")
    MAJOR_NON_CONFORMITY = "major_non_conformity", _("Major non-conformity")
    MINOR_NON_CONFORMITY = "minor_non_conformity", _("Minor non-conformity")
    OBSERVATION = "observation", pgettext_lazy("compliance", "Observation")
    IMPROVEMENT_OPPORTUNITY = "improvement_opportunity", _("Improvement opportunity")
    COMPLIANT = "compliant", _("Compliant")
    STRENGTH = "strength", pgettext_lazy("compliance", "Strength")
    NOT_APPLICABLE = "not_applicable", _("Not applicable")


class RequirementStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    DEPRECATED = "deprecated", _("Deprecated")
    SUPERSEDED = "superseded", _("Superseded")


class Priority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


# ── Assessment ─────────────────────────────────────────────

class AssessmentStatus(models.TextChoices):
    DRAFT = "draft", _("Audit draft")
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CLOSED = "closed", pgettext_lazy("assessment", "Closed")
    CANCELLED = "cancelled", pgettext_lazy("assessment", "Cancelled")

# Valid forward-only status transitions
ASSESSMENT_STATUS_TRANSITIONS = {
    AssessmentStatus.DRAFT: [AssessmentStatus.PLANNED, AssessmentStatus.CANCELLED],
    AssessmentStatus.PLANNED: [AssessmentStatus.IN_PROGRESS, AssessmentStatus.CANCELLED],
    AssessmentStatus.IN_PROGRESS: [AssessmentStatus.COMPLETED],
    AssessmentStatus.COMPLETED: [AssessmentStatus.CLOSED],
    AssessmentStatus.CLOSED: [],
    AssessmentStatus.CANCELLED: [],
}

# Statuses where the assessment metadata cannot be edited
ASSESSMENT_LOCKED_STATUSES = {
    AssessmentStatus.IN_PROGRESS,
    AssessmentStatus.COMPLETED,
    AssessmentStatus.CLOSED,
    AssessmentStatus.CANCELLED,
}

# Statuses where findings and results cannot be edited (only IN_PROGRESS allows editing)
ASSESSMENT_FROZEN_STATUSES = {
    AssessmentStatus.COMPLETED,
    AssessmentStatus.CLOSED,
    AssessmentStatus.CANCELLED,
}

# Statuses that allow toggling results
# DRAFT/PLANNED: NOT_ASSESSED ↔ EVALUATED
# IN_PROGRESS: EVALUATED ↔ COMPLIANT (NOT_ASSESSED frozen)
ASSESSMENT_TOGGLEABLE_STATUSES = {
    AssessmentStatus.DRAFT,
    AssessmentStatus.PLANNED,
    AssessmentStatus.IN_PROGRESS,
}

# Statuses that allow full editing of findings and result details
ASSESSMENT_EDITABLE_STATUSES = {
    AssessmentStatus.IN_PROGRESS,
}


# ── Mapping ────────────────────────────────────────────────

class MappingType(models.TextChoices):
    EQUIVALENT = "equivalent", _("Equivalent")
    PARTIAL_OVERLAP = "partial_overlap", _("Partial overlap")
    INCLUDES = "includes", _("Includes")
    INCLUDED_BY = "included_by", _("Included by")
    RELATED = "related", _("Related")


class CoverageLevel(models.TextChoices):
    FULL = "full", _("Full")
    PARTIAL = "partial", _("Partial")
    MINIMAL = "minimal", _("Minimal")


# ── Action Plan ────────────────────────────────────────────

class ActionPlanStatus(models.TextChoices):
    NEW = "new", pgettext_lazy("action_plan", "New")
    TO_DEFINE = "to_define", pgettext_lazy("action_plan", "To define")
    TO_VALIDATE = "to_validate", pgettext_lazy("action_plan", "To validate")
    TO_IMPLEMENT = "to_implement", pgettext_lazy("action_plan", "To implement")
    IMPLEMENTATION_TO_VALIDATE = "implementation_to_validate", pgettext_lazy(
        "action_plan", "Implementation to validate"
    )
    VALIDATED = "validated", pgettext_lazy("action_plan", "Validated")
    CLOSED = "closed", pgettext_lazy("action_plan", "Closed")
    CANCELLED = "cancelled", pgettext_lazy("action_plan", "Cancelled")


# Valid status transitions (forward + refusal)
ACTION_PLAN_TRANSITIONS = {
    ActionPlanStatus.NEW: [ActionPlanStatus.TO_DEFINE],
    ActionPlanStatus.TO_DEFINE: [ActionPlanStatus.TO_VALIDATE],
    ActionPlanStatus.TO_VALIDATE: [ActionPlanStatus.TO_IMPLEMENT, ActionPlanStatus.TO_DEFINE],
    ActionPlanStatus.TO_IMPLEMENT: [ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE],
    ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE: [
        ActionPlanStatus.VALIDATED,
        ActionPlanStatus.TO_IMPLEMENT,
    ],
    ActionPlanStatus.VALIDATED: [ActionPlanStatus.CLOSED],
    ActionPlanStatus.CLOSED: [],
    ActionPlanStatus.CANCELLED: [],
}

# Backward transitions (refusal) — require a mandatory comment
ACTION_PLAN_REFUSAL_TRANSITIONS = {
    ActionPlanStatus.TO_VALIDATE: ActionPlanStatus.TO_DEFINE,
    ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE: ActionPlanStatus.TO_IMPLEMENT,
}

# Permission required per (from_status, to_status) transition
ACTION_PLAN_TRANSITION_PERMISSIONS = {
    (ActionPlanStatus.NEW, ActionPlanStatus.TO_DEFINE): "compliance.action_plan.update",
    (ActionPlanStatus.TO_DEFINE, ActionPlanStatus.TO_VALIDATE): "compliance.action_plan.update",
    (ActionPlanStatus.TO_VALIDATE, ActionPlanStatus.TO_IMPLEMENT): "compliance.action_plan.validate",
    (ActionPlanStatus.TO_VALIDATE, ActionPlanStatus.TO_DEFINE): "compliance.action_plan.validate",
    (ActionPlanStatus.TO_IMPLEMENT, ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE): "compliance.action_plan.implement",
    (ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE, ActionPlanStatus.VALIDATED): "compliance.action_plan.validate",
    (ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE, ActionPlanStatus.TO_IMPLEMENT): "compliance.action_plan.validate",
    (ActionPlanStatus.VALIDATED, ActionPlanStatus.CLOSED): "compliance.action_plan.close",
}

# Statuses from which cancellation is allowed (all except terminal states)
ACTION_PLAN_CANCELLABLE_STATUSES = {
    ActionPlanStatus.NEW,
    ActionPlanStatus.TO_DEFINE,
    ActionPlanStatus.TO_VALIDATE,
    ActionPlanStatus.TO_IMPLEMENT,
    ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE,
    ActionPlanStatus.VALIDATED,
}

# Bootstrap color class per status (for badges and kanban columns)
ACTION_PLAN_STATUS_COLORS = {
    ActionPlanStatus.NEW: "secondary",
    ActionPlanStatus.TO_DEFINE: "info",
    ActionPlanStatus.TO_VALIDATE: "warning",
    ActionPlanStatus.TO_IMPLEMENT: "primary",
    ActionPlanStatus.IMPLEMENTATION_TO_VALIDATE: "warning",
    ActionPlanStatus.VALIDATED: "success",
    ActionPlanStatus.CLOSED: "dark",
    ActionPlanStatus.CANCELLED: "danger",
}


# ── Finding ────────────────────────────────────────────────

class FindingType(models.TextChoices):
    MAJOR_NON_CONFORMITY = "major_nc", _("Major non-conformity")
    MINOR_NON_CONFORMITY = "minor_nc", _("Minor non-conformity")
    OBSERVATION = "observation", pgettext_lazy("finding", "Observation")
    IMPROVEMENT_OPPORTUNITY = "improvement", _("Improvement opportunity")
    STRENGTH = "strength", pgettext_lazy("finding", "Strength")


FINDING_REFERENCE_PREFIXES = {
    FindingType.MAJOR_NON_CONFORMITY: "NCMAJ",
    FindingType.MINOR_NON_CONFORMITY: "NCMIN",
    FindingType.OBSERVATION: "OBS",
    FindingType.IMPROVEMENT_OPPORTUNITY: "OA",
    FindingType.STRENGTH: "STR",
}

FINDING_TYPE_COMPLIANCE_LEVEL = {
    FindingType.MAJOR_NON_CONFORMITY: 0,
    FindingType.MINOR_NON_CONFORMITY: 30,
    FindingType.OBSERVATION: 50,
    FindingType.IMPROVEMENT_OPPORTUNITY: 70,
    FindingType.STRENGTH: 100,
}

# Severity order for worst-finding-wins calculation (lower index = more severe)
FINDING_SEVERITY_ORDER = [
    FindingType.MAJOR_NON_CONFORMITY,
    FindingType.MINOR_NON_CONFORMITY,
    FindingType.OBSERVATION,
    FindingType.IMPROVEMENT_OPPORTUNITY,
    FindingType.STRENGTH,
]


# ── Compliance level defaults (status → percentage) ───────

COMPLIANCE_LEVEL_DEFAULTS = {
    ComplianceStatus.NOT_ASSESSED: 0,
    ComplianceStatus.EVALUATED: 50,
    ComplianceStatus.MAJOR_NON_CONFORMITY: 0,
    ComplianceStatus.MINOR_NON_CONFORMITY: 30,
    ComplianceStatus.OBSERVATION: 50,
    ComplianceStatus.IMPROVEMENT_OPPORTUNITY: 70,
    ComplianceStatus.COMPLIANT: 100,
    ComplianceStatus.STRENGTH: 100,
    ComplianceStatus.NOT_APPLICABLE: 100,
}


# Statuses that represent non-conformities (gaps/findings are expected)
NON_CONFORMITY_STATUSES = {
    ComplianceStatus.MAJOR_NON_CONFORMITY,
    ComplianceStatus.MINOR_NON_CONFORMITY,
}

# Statuses that represent observations/improvements (no gaps expected, but finding is)
FINDING_STATUSES = {
    ComplianceStatus.MAJOR_NON_CONFORMITY,
    ComplianceStatus.MINOR_NON_CONFORMITY,
    ComplianceStatus.OBSERVATION,
    ComplianceStatus.IMPROVEMENT_OPPORTUNITY,
}

# Statuses where "finding" field makes no sense (positive or N/A)
NO_FINDING_STATUSES = {
    ComplianceStatus.NOT_ASSESSED,
    ComplianceStatus.EVALUATED,
    ComplianceStatus.COMPLIANT,
    ComplianceStatus.STRENGTH,
    ComplianceStatus.NOT_APPLICABLE,
}
