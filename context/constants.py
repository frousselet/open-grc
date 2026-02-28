from django.db import models
from django.utils.translation import gettext_lazy as _


class Status(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")


class IssueType(models.TextChoices):
    INTERNAL = "internal", _("Internal")
    EXTERNAL = "external", _("External")


INTERNAL_CATEGORIES = [
    "strategic",
    "organizational",
    "human_resources",
    "technical",
    "financial",
    "cultural",
]

EXTERNAL_CATEGORIES = [
    "political",
    "economic",
    "social",
    "technological",
    "legal",
    "environmental",
    "competitive",
    "regulatory",
]


class IssueCategory(models.TextChoices):
    # Internal
    STRATEGIC = "strategic", _("Strategic")
    ORGANIZATIONAL = "organizational", _("Organizational")
    HUMAN_RESOURCES = "human_resources", _("Human resources")
    TECHNICAL = "technical", _("Technical")
    FINANCIAL = "financial", _("Financial")
    CULTURAL = "cultural", _("Cultural")
    # External
    POLITICAL = "political", _("Political")
    ECONOMIC = "economic", _("Economic")
    SOCIAL = "social", _("Social")
    TECHNOLOGICAL = "technological", _("Technological")
    LEGAL = "legal", _("Legal")
    ENVIRONMENTAL = "environmental", _("Environmental")
    COMPETITIVE = "competitive", _("Competitive")
    REGULATORY = "regulatory", _("Regulatory")


class ImpactLevel(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class Trend(models.TextChoices):
    IMPROVING = "improving", _("Improving")
    STABLE = "stable", _("Stable")
    DEGRADING = "degrading", _("Degrading")


class IssueStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    ACTIVE = "active", _("Active")
    MONITORED = "monitored", _("Monitored")
    CLOSED = "closed", _("Closed")


class StakeholderCategory(models.TextChoices):
    EXECUTIVE_MANAGEMENT = "executive_management", _("Executive management")
    EMPLOYEES = "employees", _("Employees")
    CUSTOMERS = "customers", _("Customers")
    SUPPLIERS = "suppliers", _("Suppliers")
    PARTNERS = "partners", _("Partners")
    REGULATORS = "regulators", _("Regulators")
    SHAREHOLDERS = "shareholders", _("Shareholders")
    INSURERS = "insurers", _("Insurers")
    PUBLIC = "public", _("General public")
    COMPETITORS = "competitors", _("Competitors")
    UNIONS = "unions", _("Unions")
    AUDITORS = "auditors", _("Auditors")
    OTHER = "other", _("Other")


class InfluenceLevel(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class ExpectationType(models.TextChoices):
    REQUIREMENT = "requirement", _("Requirement")
    EXPECTATION = "expectation", _("Expectation")
    NEED = "need", _("Need")


class Priority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class StakeholderStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class ObjectiveCategory(models.TextChoices):
    CONFIDENTIALITY = "confidentiality", _("Confidentiality")
    INTEGRITY = "integrity", _("Integrity")
    AVAILABILITY = "availability", _("Availability")
    COMPLIANCE = "compliance", _("Compliance")
    OPERATIONAL = "operational", _("Operational")
    STRATEGIC = "strategic", _("Strategic")


class ObjectiveType(models.TextChoices):
    SECURITY = "security", _("Security")
    COMPLIANCE = "compliance", _("Compliance")
    BUSINESS = "business", _("Business")
    OTHER = "other", _("Other")


class MeasurementFrequency(models.TextChoices):
    MONTHLY = "monthly", _("Monthly")
    QUARTERLY = "quarterly", _("Quarterly")
    SEMI_ANNUAL = "semi_annual", _("Semi-annual")
    ANNUAL = "annual", _("Annual")


class ObjectiveStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ACHIEVED = "achieved", _("Achieved")
    NOT_ACHIEVED = "not_achieved", _("Not achieved")
    CANCELLED = "cancelled", _("Cancelled")


class SwotStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    VALIDATED = "validated", _("Validated")
    ARCHIVED = "archived", _("Archived")


class SwotQuadrant(models.TextChoices):
    STRENGTH = "strength", _("Strength")
    WEAKNESS = "weakness", _("Weakness")
    OPPORTUNITY = "opportunity", _("Opportunity")
    THREAT = "threat", _("Threat")


class RoleType(models.TextChoices):
    GOVERNANCE = "governance", _("Governance")
    OPERATIONAL = "operational", _("Operational")
    SUPPORT = "support", _("Support")
    CONTROL = "control", _("Control")


class RoleStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class RaciType(models.TextChoices):
    RESPONSIBLE = "responsible", _("Responsible (R)")
    ACCOUNTABLE = "accountable", _("Accountable (A)")
    CONSULTED = "consulted", _("Consulted (C)")
    INFORMED = "informed", _("Informed (I)")


class ActivityType(models.TextChoices):
    CORE_BUSINESS = "core_business", _("Core business")
    SUPPORT = "support", _("Support")
    MANAGEMENT = "management", _("Management")


class Criticality(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class ActivityStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    PLANNED = "planned", _("Planned")


class SiteType(models.TextChoices):
    HEADQUARTERS = "siege", _("Headquarters")
    OFFICE = "bureau", _("Office")
    FACTORY = "usine", _("Factory")
    WAREHOUSE = "entrepot", _("Warehouse")
    DATACENTER = "datacenter", _("Datacenter")
    REMOTE = "site_distant", _("Remote site")
    OTHER = "autre", _("Other")
