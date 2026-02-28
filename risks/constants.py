from django.db import models


class Methodology(models.TextChoices):
    ISO27005 = "iso27005", "ISO 27005"
    EBIOS_RM = "ebios_rm", "EBIOS RM"


class AssessmentStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminée"
    VALIDATED = "validated", "Validée"
    ARCHIVED = "archived", "Archivée"


class CriteriaStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    ACTIVE = "active", "Actif"
    ARCHIVED = "archived", "Archivé"


class ScaleType(models.TextChoices):
    LIKELIHOOD = "likelihood", "Vraisemblance"
    IMPACT = "impact", "Impact"


class RiskSourceType(models.TextChoices):
    ISO27005_ANALYSIS = "iso27005_analysis", "Analyse ISO 27005"
    EBIOS_STRATEGIC = "ebios_strategic", "Scénario stratégique EBIOS"
    EBIOS_OPERATIONAL = "ebios_operational", "Scénario opérationnel EBIOS"
    INCIDENT = "incident", "Incident"
    AUDIT = "audit", "Audit"
    COMPLIANCE = "compliance", "Conformité"
    MANUAL = "manual", "Saisie manuelle"


class TreatmentDecision(models.TextChoices):
    ACCEPT = "accept", "Accepter"
    MITIGATE = "mitigate", "Réduire"
    TRANSFER = "transfer", "Transférer"
    AVOID = "avoid", "Éviter"
    NOT_DECIDED = "not_decided", "Non décidé"


class RiskPriority(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"
    CRITICAL = "critical", "Critique"


class RiskStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identifié"
    ANALYZED = "analyzed", "Analysé"
    EVALUATED = "evaluated", "Évalué"
    TREATMENT_PLANNED = "treatment_planned", "Traitement planifié"
    TREATMENT_IN_PROGRESS = "treatment_in_progress", "Traitement en cours"
    TREATED = "treated", "Traité"
    ACCEPTED = "accepted", "Accepté"
    CLOSED = "closed", "Clôturé"
    MONITORING = "monitoring", "En surveillance"


class TreatmentType(models.TextChoices):
    MITIGATE = "mitigate", "Réduire"
    TRANSFER = "transfer", "Transférer"
    AVOID = "avoid", "Éviter"


class TreatmentPlanStatus(models.TextChoices):
    PLANNED = "planned", "Planifié"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminé"
    CANCELLED = "cancelled", "Annulé"
    OVERDUE = "overdue", "En retard"


class ActionStatus(models.TextChoices):
    PLANNED = "planned", "Planifiée"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminée"
    CANCELLED = "cancelled", "Annulée"


class AcceptanceStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expirée"
    REVOKED = "revoked", "Révoquée"
    RENEWED = "renewed", "Renouvelée"


class ThreatType(models.TextChoices):
    DELIBERATE = "deliberate", "Délibérée"
    ACCIDENTAL = "accidental", "Accidentelle"
    ENVIRONMENTAL = "environmental", "Environnementale"
    OTHER = "other", "Autre"


class ThreatOrigin(models.TextChoices):
    HUMAN_INTERNAL = "human_internal", "Humaine interne"
    HUMAN_EXTERNAL = "human_external", "Humaine externe"
    NATURAL = "natural", "Naturelle"
    TECHNICAL = "technical", "Technique"
    OTHER = "other", "Autre"


class ThreatCategory(models.TextChoices):
    MALWARE = "malware", "Logiciel malveillant"
    SOCIAL_ENGINEERING = "social_engineering", "Ingénierie sociale"
    UNAUTHORIZED_ACCESS = "unauthorized_access", "Accès non autorisé"
    DENIAL_OF_SERVICE = "denial_of_service", "Déni de service"
    DATA_BREACH = "data_breach", "Fuite de données"
    PHYSICAL_ATTACK = "physical_attack", "Attaque physique"
    ESPIONAGE = "espionage", "Espionnage"
    FRAUD = "fraud", "Fraude"
    SABOTAGE = "sabotage", "Sabotage"
    HUMAN_ERROR = "human_error", "Erreur humaine"
    SYSTEM_FAILURE = "system_failure", "Défaillance système"
    NETWORK_FAILURE = "network_failure", "Défaillance réseau"
    POWER_FAILURE = "power_failure", "Coupure d'alimentation"
    NATURAL_DISASTER = "natural_disaster", "Catastrophe naturelle"
    FIRE = "fire", "Incendie"
    WATER_DAMAGE = "water_damage", "Dégât des eaux"
    THEFT = "theft", "Vol"
    VANDALISM = "vandalism", "Vandalisme"
    SUPPLY_CHAIN = "supply_chain", "Chaîne d'approvisionnement"
    INSIDER_THREAT = "insider_threat", "Menace interne"
    RANSOMWARE = "ransomware", "Rançongiciel"
    APT = "apt", "Menace persistante avancée (APT)"


class ThreatStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class VulnerabilityCategory(models.TextChoices):
    CONFIGURATION_WEAKNESS = "configuration_weakness", "Faiblesse de configuration"
    MISSING_PATCH = "missing_patch", "Correctif manquant"
    DESIGN_FLAW = "design_flaw", "Défaut de conception"
    CODING_ERROR = "coding_error", "Erreur de codage"
    WEAK_AUTHENTICATION = "weak_authentication", "Authentification faible"
    INSUFFICIENT_LOGGING = "insufficient_logging", "Journalisation insuffisante"
    LACK_OF_ENCRYPTION = "lack_of_encryption", "Absence de chiffrement"
    PHYSICAL_VULNERABILITY = "physical_vulnerability", "Vulnérabilité physique"
    ORGANIZATIONAL_WEAKNESS = "organizational_weakness", "Faiblesse organisationnelle"
    HUMAN_FACTOR = "human_factor", "Facteur humain"
    OBSOLESCENCE = "obsolescence", "Obsolescence"
    INSUFFICIENT_BACKUP = "insufficient_backup", "Sauvegarde insuffisante"
    NETWORK_EXPOSURE = "network_exposure", "Exposition réseau"
    THIRD_PARTY_DEPENDENCY = "third_party_dependency", "Dépendance tierce"


class Severity(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"
    CRITICAL = "critical", "Critique"


class VulnerabilityStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identifiée"
    CONFIRMED = "confirmed", "Confirmée"
    MITIGATED = "mitigated", "Atténuée"
    ACCEPTED = "accepted", "Acceptée"
    CLOSED = "closed", "Clôturée"


# ── Default 5×5 risk matrix scales (ISO 27005) ──────────────

DEFAULT_LIKELIHOOD_SCALES = [
    (1, "Très improbable"),
    (2, "Improbable"),
    (3, "Possible"),
    (4, "Probable"),
    (5, "Très probable"),
]

DEFAULT_IMPACT_SCALES = [
    (1, "Négligeable"),
    (2, "Mineur"),
    (3, "Modéré"),
    (4, "Significatif"),
    (5, "Sévère"),
]

DEFAULT_RISK_LEVELS = {
    1: {"name": "Faible", "color": "#4caf50"},
    2: {"name": "Modéré-Faible", "color": "#8bc34a"},
    3: {"name": "Modéré", "color": "#ffc107"},
    4: {"name": "Modéré-Élevé", "color": "#ff9800"},
    5: {"name": "Élevé", "color": "#e53935"},
}

# Symmetric matrix: risk_level = f(L + I - 1), so cell (L,I) == cell (I,L)
DEFAULT_RISK_MATRIX = {
    (5, 1): 3, (5, 2): 4, (5, 3): 4, (5, 4): 5, (5, 5): 5,
    (4, 1): 3, (4, 2): 3, (4, 3): 4, (4, 4): 4, (4, 5): 5,
    (3, 1): 2, (3, 2): 3, (3, 3): 3, (3, 4): 4, (3, 5): 4,
    (2, 1): 2, (2, 2): 2, (2, 3): 3, (2, 4): 3, (2, 5): 4,
    (1, 1): 1, (1, 2): 2, (1, 3): 2, (1, 4): 3, (1, 5): 3,
}
