from django.db import models
from django.utils.translation import gettext_lazy as _


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
    NON_COMPLIANT = "non_compliant", _("Non-compliant")
    PARTIALLY_COMPLIANT = "partially_compliant", _("Partially compliant")
    COMPLIANT = "compliant", _("Compliant")
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
    DRAFT = "draft", _("Draft")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    VALIDATED = "validated", _("Validated")
    ARCHIVED = "archived", _("Archived")


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
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    OVERDUE = "overdue", _("Overdue")


# ── Compliance level defaults (status → percentage) ───────

COMPLIANCE_LEVEL_DEFAULTS = {
    ComplianceStatus.NOT_ASSESSED: 0,
    ComplianceStatus.NON_COMPLIANT: 0,
    ComplianceStatus.PARTIALLY_COMPLIANT: 50,
    ComplianceStatus.COMPLIANT: 100,
    # NOT_APPLICABLE is excluded from calculation
}
