from django.db import models


# ── Framework ──────────────────────────────────────────────

class FrameworkType(models.TextChoices):
    STANDARD = "standard", "Norme"
    LAW = "law", "Loi"
    REGULATION = "regulation", "Règlement"
    CONTRACT = "contract", "Contrat"
    INTERNAL_POLICY = "internal_policy", "Politique interne"
    INDUSTRY_FRAMEWORK = "industry_framework", "Référentiel sectoriel"
    OTHER = "other", "Autre"


class FrameworkCategory(models.TextChoices):
    INFORMATION_SECURITY = "information_security", "Sécurité de l'information"
    PRIVACY = "privacy", "Protection des données"
    RISK_MANAGEMENT = "risk_management", "Gestion des risques"
    BUSINESS_CONTINUITY = "business_continuity", "Continuité d'activité"
    CLOUD_SECURITY = "cloud_security", "Sécurité cloud"
    SECTOR_SPECIFIC = "sector_specific", "Réglementations sectorielles"
    IT_GOVERNANCE = "it_governance", "Gouvernance IT"
    QUALITY = "quality", "Qualité"
    CONTRACTUAL = "contractual", "Exigences contractuelles"
    INTERNAL = "internal", "Politiques internes"
    OTHER = "other", "Autre"


class FrameworkStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    ACTIVE = "active", "Actif"
    UNDER_REVIEW = "under_review", "En cours de revue"
    DEPRECATED = "deprecated", "Obsolète"
    ARCHIVED = "archived", "Archivé"


# ── Requirement ────────────────────────────────────────────

class RequirementType(models.TextChoices):
    MANDATORY = "mandatory", "Obligatoire"
    RECOMMENDED = "recommended", "Recommandé"
    OPTIONAL = "optional", "Optionnel"


class RequirementCategory(models.TextChoices):
    ORGANIZATIONAL = "organizational", "Organisationnel"
    TECHNICAL = "technical", "Technique"
    PHYSICAL = "physical", "Physique"
    LEGAL = "legal", "Juridique"
    HUMAN = "human", "Humain"
    OTHER = "other", "Autre"


class ComplianceStatus(models.TextChoices):
    NOT_ASSESSED = "not_assessed", "Non évalué"
    NON_COMPLIANT = "non_compliant", "Non conforme"
    PARTIALLY_COMPLIANT = "partially_compliant", "Partiellement conforme"
    COMPLIANT = "compliant", "Conforme"
    NOT_APPLICABLE = "not_applicable", "Non applicable"


class RequirementStatus(models.TextChoices):
    ACTIVE = "active", "Actif"
    DEPRECATED = "deprecated", "Obsolète"
    SUPERSEDED = "superseded", "Remplacé"


class Priority(models.TextChoices):
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"
    CRITICAL = "critical", "Critique"


# ── Assessment ─────────────────────────────────────────────

class AssessmentStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminé"
    VALIDATED = "validated", "Validé"
    ARCHIVED = "archived", "Archivé"


# ── Mapping ────────────────────────────────────────────────

class MappingType(models.TextChoices):
    EQUIVALENT = "equivalent", "Équivalent"
    PARTIAL_OVERLAP = "partial_overlap", "Recouvrement partiel"
    INCLUDES = "includes", "Inclut"
    INCLUDED_BY = "included_by", "Inclus par"
    RELATED = "related", "Lié"


class CoverageLevel(models.TextChoices):
    FULL = "full", "Complète"
    PARTIAL = "partial", "Partielle"
    MINIMAL = "minimal", "Minimale"


# ── Action Plan ────────────────────────────────────────────

class ActionPlanStatus(models.TextChoices):
    PLANNED = "planned", "Planifié"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminé"
    CANCELLED = "cancelled", "Annulé"
    OVERDUE = "overdue", "En retard"


# ── Compliance level defaults (status → percentage) ───────

COMPLIANCE_LEVEL_DEFAULTS = {
    ComplianceStatus.NOT_ASSESSED: 0,
    ComplianceStatus.NON_COMPLIANT: 0,
    ComplianceStatus.PARTIALLY_COMPLIANT: 50,
    ComplianceStatus.COMPLIANT: 100,
    # NOT_APPLICABLE is excluded from calculation
}
