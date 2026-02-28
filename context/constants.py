from django.db import models


class Status(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    ACTIVE = "active", "Actif"
    ARCHIVED = "archived", "Archivé"


class IssueType(models.TextChoices):
    INTERNAL = "internal", "Interne"
    EXTERNAL = "external", "Externe"


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
    STRATEGIC = "strategic", "Stratégique"
    ORGANIZATIONAL = "organizational", "Organisationnel"
    HUMAN_RESOURCES = "human_resources", "Ressources humaines"
    TECHNICAL = "technical", "Technique"
    FINANCIAL = "financial", "Financier"
    CULTURAL = "cultural", "Culturel"
    # External
    POLITICAL = "political", "Politique"
    ECONOMIC = "economic", "Économique"
    SOCIAL = "social", "Social"
    TECHNOLOGICAL = "technological", "Technologique"
    LEGAL = "legal", "Juridique"
    ENVIRONMENTAL = "environmental", "Environnemental"
    COMPETITIVE = "competitive", "Concurrentiel"
    REGULATORY = "regulatory", "Réglementaire"


class ImpactLevel(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"
    CRITICAL = "critical", "Critique"


class Trend(models.TextChoices):
    IMPROVING = "improving", "En amélioration"
    STABLE = "stable", "Stable"
    DEGRADING = "degrading", "En dégradation"


class IssueStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identifié"
    ACTIVE = "active", "Actif"
    MONITORED = "monitored", "Surveillé"
    CLOSED = "closed", "Clôturé"


class StakeholderCategory(models.TextChoices):
    EXECUTIVE_MANAGEMENT = "executive_management", "Direction générale"
    EMPLOYEES = "employees", "Employés"
    CUSTOMERS = "customers", "Clients"
    SUPPLIERS = "suppliers", "Fournisseurs"
    PARTNERS = "partners", "Partenaires"
    REGULATORS = "regulators", "Régulateurs"
    SHAREHOLDERS = "shareholders", "Actionnaires"
    INSURERS = "insurers", "Assureurs"
    PUBLIC = "public", "Grand public"
    COMPETITORS = "competitors", "Concurrents"
    UNIONS = "unions", "Syndicats"
    AUDITORS = "auditors", "Auditeurs"
    OTHER = "other", "Autre"


class InfluenceLevel(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"


class ExpectationType(models.TextChoices):
    REQUIREMENT = "requirement", "Exigence"
    EXPECTATION = "expectation", "Attente"
    NEED = "need", "Besoin"


class Priority(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"
    CRITICAL = "critical", "Critique"


class StakeholderStatus(models.TextChoices):
    ACTIVE = "active", "Actif"
    INACTIVE = "inactive", "Inactif"


class ObjectiveCategory(models.TextChoices):
    CONFIDENTIALITY = "confidentiality", "Confidentialité"
    INTEGRITY = "integrity", "Intégrité"
    AVAILABILITY = "availability", "Disponibilité"
    COMPLIANCE = "compliance", "Conformité"
    OPERATIONAL = "operational", "Opérationnel"
    STRATEGIC = "strategic", "Stratégique"


class ObjectiveType(models.TextChoices):
    SECURITY = "security", "Sécurité"
    COMPLIANCE = "compliance", "Conformité"
    BUSINESS = "business", "Métier"
    OTHER = "other", "Autre"


class MeasurementFrequency(models.TextChoices):
    MONTHLY = "monthly", "Mensuel"
    QUARTERLY = "quarterly", "Trimestriel"
    SEMI_ANNUAL = "semi_annual", "Semestriel"
    ANNUAL = "annual", "Annuel"


class ObjectiveStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    ACTIVE = "active", "Actif"
    ACHIEVED = "achieved", "Atteint"
    NOT_ACHIEVED = "not_achieved", "Non atteint"
    CANCELLED = "cancelled", "Annulé"


class SwotStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    VALIDATED = "validated", "Validé"
    ARCHIVED = "archived", "Archivé"


class SwotQuadrant(models.TextChoices):
    STRENGTH = "strength", "Force"
    WEAKNESS = "weakness", "Faiblesse"
    OPPORTUNITY = "opportunity", "Opportunité"
    THREAT = "threat", "Menace"


class RoleType(models.TextChoices):
    GOVERNANCE = "governance", "Gouvernance"
    OPERATIONAL = "operational", "Opérationnel"
    SUPPORT = "support", "Support"
    CONTROL = "control", "Contrôle"


class RoleStatus(models.TextChoices):
    ACTIVE = "active", "Actif"
    INACTIVE = "inactive", "Inactif"


class RaciType(models.TextChoices):
    RESPONSIBLE = "responsible", "Responsable (R)"
    ACCOUNTABLE = "accountable", "Approbateur (A)"
    CONSULTED = "consulted", "Consulté (C)"
    INFORMED = "informed", "Informé (I)"


class ActivityType(models.TextChoices):
    CORE_BUSINESS = "core_business", "Cœur de métier"
    SUPPORT = "support", "Support"
    MANAGEMENT = "management", "Management"


class Criticality(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"
    CRITICAL = "critical", "Critique"


class ActivityStatus(models.TextChoices):
    ACTIVE = "active", "Actif"
    INACTIVE = "inactive", "Inactif"
    PLANNED = "planned", "Planifié"


class SiteType(models.TextChoices):
    HEADQUARTERS = "siege", "Siège"
    OFFICE = "bureau", "Bureau"
    FACTORY = "usine", "Usine"
    WAREHOUSE = "entrepot", "Entrepôt"
    DATACENTER = "datacenter", "Datacenter"
    REMOTE = "site_distant", "Site distant"
    OTHER = "autre", "Autre"
