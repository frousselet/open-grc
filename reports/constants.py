from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class ReportType(models.TextChoices):
    SOA = "soa", _("Statement of Applicability")
    AUDIT_REPORT = "audit_report", _("Audit report")
    MANAGEMENT_REVIEW_PPTX = "management_review_pptx", _("Management review - Presentation")
    MANAGEMENT_REVIEW_DOCX = "management_review_docx", _("Management review - Minutes")
    RISK_REGISTER = "risk_register", _("Risk register")


class ReportStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    GENERATING = "generating", _("Generating")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")


# ── Management review ─────────────────────────────────────

class ManagementReviewStatus(models.TextChoices):
    PLANNED = "planned", pgettext_lazy("management review status", "Planned")
    IN_PREPARATION = "in_preparation", _("In preparation")
    HELD = "held", _("Held")
    CLOSED = "closed", pgettext_lazy("management review status", "Closed")
    CANCELLED = "cancelled", pgettext_lazy("management review status", "Cancelled")


# Valid status transitions (excluding cancellation which is allowed from
# any non-terminal status).
MANAGEMENT_REVIEW_TRANSITIONS = {
    ManagementReviewStatus.PLANNED: [ManagementReviewStatus.IN_PREPARATION],
    ManagementReviewStatus.IN_PREPARATION: [ManagementReviewStatus.HELD],
    ManagementReviewStatus.HELD: [ManagementReviewStatus.CLOSED],
    ManagementReviewStatus.CLOSED: [],
    ManagementReviewStatus.CANCELLED: [],
}

MANAGEMENT_REVIEW_CANCELLABLE_STATUSES = [
    ManagementReviewStatus.PLANNED,
    ManagementReviewStatus.IN_PREPARATION,
    ManagementReviewStatus.HELD,
]


class ManagementReviewFrequency(models.TextChoices):
    QUARTERLY = "quarterly", _("Quarterly")
    SEMIANNUAL = "semiannual", _("Semi-annual")
    ANNUAL = "annual", _("Annual")
    EXCEPTIONAL = "exceptional", _("Exceptional")


class ParticipantRole(models.TextChoices):
    FACILITATOR = "facilitator", _("Facilitator")
    DECISION_MAKER = "decision_maker", _("Decision maker")
    CONTRIBUTOR = "contributor", _("Contributor")
    OBSERVER = "observer", _("Observer")


# ── Decisions ─────────────────────────────────────────────

class DecisionCategory(models.TextChoices):
    IMPROVEMENT = "improvement", _("Continual improvement")
    ISMS_CHANGE = "isms_change", _("ISMS change")
    RESOURCE_ALLOCATION = "resource_allocation", _("Resource allocation")
    RISK_ACCEPTANCE = "risk_acceptance", _("Risk acceptance")
    OBJECTIVE_ADJUSTMENT = "objective_adjustment", _("Objective adjustment")
    POLICY_UPDATE = "policy_update", _("Policy update")
    OTHER = "other", pgettext_lazy("decision category", "Other")


class DecisionInputClause(models.TextChoices):
    """ISO 27001:2022 clause 9.3.2 input that a decision addresses."""
    A_PREVIOUS_ACTIONS = "a", _("9.3.2.a - Previous review actions")
    B_ISSUES = "b", _("9.3.2.b - Internal and external issues")
    C_STAKEHOLDERS = "c", _("9.3.2.c - Needs and expectations of interested parties")
    D1_NONCONFORMITIES = "d1", _("9.3.2.d.1 - Non-conformities and corrective actions")
    D2_MEASUREMENT = "d2", _("9.3.2.d.2 - Monitoring and measurement results")
    D3_AUDITS = "d3", _("9.3.2.d.3 - Audit results")
    D4_OBJECTIVES = "d4", _("9.3.2.d.4 - Achievement of security objectives")
    E_FEEDBACK = "e", _("9.3.2.e - Feedback from interested parties")
    F_RISKS = "f", _("9.3.2.f - Risk assessment and treatment")
    G_IMPROVEMENT = "g", _("9.3.2.g - Opportunities for improvement")


class DecisionPriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class DecisionStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    IN_PROGRESS = "in_progress", _("In progress")
    IMPLEMENTED = "implemented", _("Implemented")
    CANCELLED = "cancelled", pgettext_lazy("decision status", "Cancelled")


# ── ISMS changes ──────────────────────────────────────────

class IsmsChangeType(models.TextChoices):
    SCOPE = "scope", _("ISMS scope")
    POLICY = "policy", pgettext_lazy("isms change type", "Policy")
    CONTROL = "control", _("Security control")
    ORGANIZATION = "organization", _("Organization")
    RESOURCE = "resource", _("Resources")
    PROCESS = "process", pgettext_lazy("isms change type", "Process")
    OTHER = "other", pgettext_lazy("isms change type", "Other")


class IsmsChangeStatus(models.TextChoices):
    PROPOSED = "proposed", _("Proposed")
    APPROVED = "approved", pgettext_lazy("isms change status", "Approved")
    IN_PROGRESS = "in_progress", pgettext_lazy("isms change status", "In progress")
    IMPLEMENTED = "implemented", pgettext_lazy("isms change status", "Implemented")
    REJECTED = "rejected", _("Rejected")
