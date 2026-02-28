from django.db import models
from django.utils.translation import gettext_lazy as _


class Methodology(models.TextChoices):
    ISO27005 = "iso27005", _("ISO 27005")
    EBIOS_RM = "ebios_rm", _("EBIOS RM")


class AssessmentStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    VALIDATED = "validated", _("Validated")
    ARCHIVED = "archived", _("Archived")


class CriteriaStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")


class ScaleType(models.TextChoices):
    LIKELIHOOD = "likelihood", _("Likelihood")
    IMPACT = "impact", _("Impact")


class RiskSourceType(models.TextChoices):
    ISO27005_ANALYSIS = "iso27005_analysis", _("ISO 27005 analysis")
    EBIOS_STRATEGIC = "ebios_strategic", _("EBIOS strategic scenario")
    EBIOS_OPERATIONAL = "ebios_operational", _("EBIOS operational scenario")
    INCIDENT = "incident", _("Incident")
    AUDIT = "audit", _("Audit")
    COMPLIANCE = "compliance", _("Compliance")
    MANUAL = "manual", _("Manual entry")


class TreatmentDecision(models.TextChoices):
    ACCEPT = "accept", _("Accept")
    MITIGATE = "mitigate", _("Mitigate")
    TRANSFER = "transfer", _("Transfer")
    AVOID = "avoid", _("Avoid")
    NOT_DECIDED = "not_decided", _("Not decided")


class RiskPriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class RiskStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    ANALYZED = "analyzed", _("Analyzed")
    EVALUATED = "evaluated", _("Evaluated")
    TREATMENT_PLANNED = "treatment_planned", _("Treatment planned")
    TREATMENT_IN_PROGRESS = "treatment_in_progress", _("Treatment in progress")
    TREATED = "treated", _("Treated")
    ACCEPTED = "accepted", _("Accepted")
    CLOSED = "closed", _("Closed")
    MONITORING = "monitoring", _("Monitoring")


class TreatmentType(models.TextChoices):
    MITIGATE = "mitigate", _("Mitigate")
    TRANSFER = "transfer", _("Transfer")
    AVOID = "avoid", _("Avoid")


class TreatmentPlanStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    OVERDUE = "overdue", _("Overdue")


class ActionStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class AcceptanceStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    EXPIRED = "expired", _("Expired")
    REVOKED = "revoked", _("Revoked")
    RENEWED = "renewed", _("Renewed")


class ThreatType(models.TextChoices):
    DELIBERATE = "deliberate", _("Deliberate")
    ACCIDENTAL = "accidental", _("Accidental")
    ENVIRONMENTAL = "environmental", _("Environmental")
    OTHER = "other", _("Other")


class ThreatOrigin(models.TextChoices):
    HUMAN_INTERNAL = "human_internal", _("Human internal")
    HUMAN_EXTERNAL = "human_external", _("Human external")
    NATURAL = "natural", _("Natural")
    TECHNICAL = "technical", _("Technical")
    OTHER = "other", _("Other")


class ThreatCategory(models.TextChoices):
    MALWARE = "malware", _("Malware")
    SOCIAL_ENGINEERING = "social_engineering", _("Social engineering")
    UNAUTHORIZED_ACCESS = "unauthorized_access", _("Unauthorized access")
    DENIAL_OF_SERVICE = "denial_of_service", _("Denial of service")
    DATA_BREACH = "data_breach", _("Data breach")
    PHYSICAL_ATTACK = "physical_attack", _("Physical attack")
    ESPIONAGE = "espionage", _("Espionage")
    FRAUD = "fraud", _("Fraud")
    SABOTAGE = "sabotage", _("Sabotage")
    HUMAN_ERROR = "human_error", _("Human error")
    SYSTEM_FAILURE = "system_failure", _("System failure")
    NETWORK_FAILURE = "network_failure", _("Network failure")
    POWER_FAILURE = "power_failure", _("Power failure")
    NATURAL_DISASTER = "natural_disaster", _("Natural disaster")
    FIRE = "fire", _("Fire")
    WATER_DAMAGE = "water_damage", _("Water damage")
    THEFT = "theft", _("Theft")
    VANDALISM = "vandalism", _("Vandalism")
    SUPPLY_CHAIN = "supply_chain", _("Supply chain")
    INSIDER_THREAT = "insider_threat", _("Insider threat")
    RANSOMWARE = "ransomware", _("Ransomware")
    APT = "apt", _("Advanced persistent threat (APT)")


class ThreatStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class VulnerabilityCategory(models.TextChoices):
    CONFIGURATION_WEAKNESS = "configuration_weakness", _("Configuration weakness")
    MISSING_PATCH = "missing_patch", _("Missing patch")
    DESIGN_FLAW = "design_flaw", _("Design flaw")
    CODING_ERROR = "coding_error", _("Coding error")
    WEAK_AUTHENTICATION = "weak_authentication", _("Weak authentication")
    INSUFFICIENT_LOGGING = "insufficient_logging", _("Insufficient logging")
    LACK_OF_ENCRYPTION = "lack_of_encryption", _("Lack of encryption")
    PHYSICAL_VULNERABILITY = "physical_vulnerability", _("Physical vulnerability")
    ORGANIZATIONAL_WEAKNESS = "organizational_weakness", _("Organizational weakness")
    HUMAN_FACTOR = "human_factor", _("Human factor")
    OBSOLESCENCE = "obsolescence", _("Obsolescence")
    INSUFFICIENT_BACKUP = "insufficient_backup", _("Insufficient backup")
    NETWORK_EXPOSURE = "network_exposure", _("Network exposure")
    THIRD_PARTY_DEPENDENCY = "third_party_dependency", _("Third-party dependency")


class Severity(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class VulnerabilityStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    CONFIRMED = "confirmed", _("Confirmed")
    MITIGATED = "mitigated", _("Mitigated")
    ACCEPTED = "accepted", _("Accepted")
    CLOSED = "closed", _("Closed")


# ── Default 5×5 risk matrix scales (ISO 27005) ──────────────

DEFAULT_LIKELIHOOD_SCALES = [
    (1, _("Very unlikely")),
    (2, _("Unlikely")),
    (3, _("Possible")),
    (4, _("Likely")),
    (5, _("Very likely")),
]

DEFAULT_IMPACT_SCALES = [
    (1, _("Negligible")),
    (2, _("Minor")),
    (3, _("Moderate")),
    (4, _("Major")),
    (5, _("Severe")),
]

DEFAULT_RISK_LEVELS = {
    1: {"name": _("Low"), "color": "#4caf50"},
    2: {"name": _("Moderate-Low"), "color": "#8bc34a"},
    3: {"name": _("Moderate"), "color": "#ffc107"},
    4: {"name": _("Moderate-High"), "color": "#ff9800"},
    5: {"name": _("High"), "color": "#e53935"},
}

# Symmetric matrix: risk_level = f(L + I - 1), so cell (L,I) == cell (I,L)
DEFAULT_RISK_MATRIX = {
    (5, 1): 3, (5, 2): 4, (5, 3): 4, (5, 4): 5, (5, 5): 5,
    (4, 1): 3, (4, 2): 3, (4, 3): 4, (4, 4): 4, (4, 5): 5,
    (3, 1): 2, (3, 2): 3, (3, 3): 3, (3, 4): 4, (3, 5): 4,
    (2, 1): 2, (2, 2): 2, (2, 3): 3, (2, 4): 3, (2, 5): 4,
    (1, 1): 1, (1, 2): 2, (1, 3): 2, (1, 4): 3, (1, 5): 3,
}
