from django.db import models


# ── DIC Levels ──────────────────────────────────────────────

class DICLevel(models.IntegerChoices):
    NEGLIGIBLE = 0, "Négligeable"
    LOW = 1, "Faible"
    MEDIUM = 2, "Moyen"
    HIGH = 3, "Élevé"
    CRITICAL = 4, "Critique"


# ── Essential Asset ─────────────────────────────────────────

class EssentialAssetType(models.TextChoices):
    BUSINESS_PROCESS = "business_process", "Processus métier"
    INFORMATION = "information", "Information"


PROCESS_CATEGORIES = [
    "core_process",
    "support_process",
    "management_process",
]

INFORMATION_CATEGORIES = [
    "strategic_data",
    "operational_data",
    "personal_data",
    "financial_data",
    "technical_data",
    "legal_data",
    "research_data",
    "commercial_data",
]


class EssentialAssetCategory(models.TextChoices):
    # Process
    CORE_PROCESS = "core_process", "Processus cœur de métier"
    SUPPORT_PROCESS = "support_process", "Processus support"
    MANAGEMENT_PROCESS = "management_process", "Processus de management"
    # Information
    STRATEGIC_DATA = "strategic_data", "Données stratégiques"
    OPERATIONAL_DATA = "operational_data", "Données opérationnelles"
    PERSONAL_DATA = "personal_data", "Données personnelles"
    FINANCIAL_DATA = "financial_data", "Données financières"
    TECHNICAL_DATA = "technical_data", "Données techniques"
    LEGAL_DATA = "legal_data", "Données juridiques"
    RESEARCH_DATA = "research_data", "Données de recherche"
    COMMERCIAL_DATA = "commercial_data", "Données commerciales"


class DataClassification(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Interne"
    CONFIDENTIAL = "confidential", "Confidentiel"
    RESTRICTED = "restricted", "Restreint"
    SECRET = "secret", "Secret"


class EssentialAssetStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identifié"
    ACTIVE = "active", "Actif"
    UNDER_REVIEW = "under_review", "En cours de revue"
    DECOMMISSIONED = "decommissioned", "Décommissionné"


# ── Support Asset ───────────────────────────────────────────

class SupportAssetType(models.TextChoices):
    HARDWARE = "hardware", "Matériel"
    SOFTWARE = "software", "Logiciel"
    NETWORK = "network", "Réseau"
    PERSON = "person", "Personne"
    SITE = "site", "Site"
    SERVICE = "service", "Service"
    PAPER = "paper", "Papier"


class SupportAssetCategory(models.TextChoices):
    # Hardware
    SERVER = "server", "Serveur"
    WORKSTATION = "workstation", "Poste de travail"
    LAPTOP = "laptop", "Ordinateur portable"
    MOBILE_DEVICE = "mobile_device", "Appareil mobile"
    NETWORK_EQUIPMENT = "network_equipment", "Équipement réseau"
    STORAGE = "storage", "Stockage"
    PERIPHERAL = "peripheral", "Périphérique"
    IOT_DEVICE = "iot_device", "Objet connecté (IoT)"
    REMOVABLE_MEDIA = "removable_media", "Support amovible"
    OTHER_HARDWARE = "other_hardware", "Autre matériel"
    # Software
    OPERATING_SYSTEM = "operating_system", "Système d'exploitation"
    DATABASE = "database", "Base de données"
    APPLICATION = "application", "Application"
    MIDDLEWARE = "middleware", "Middleware"
    SECURITY_TOOL = "security_tool", "Outil de sécurité"
    DEVELOPMENT_TOOL = "development_tool", "Outil de développement"
    SAAS_APPLICATION = "saas_application", "Application SaaS"
    OTHER_SOFTWARE = "other_software", "Autre logiciel"
    # Network
    LAN = "lan", "Réseau local (LAN)"
    WAN = "wan", "Réseau étendu (WAN)"
    WIFI = "wifi", "Wi-Fi"
    VPN = "vpn", "VPN"
    INTERNET_LINK = "internet_link", "Lien Internet"
    FIREWALL_ZONE = "firewall_zone", "Zone pare-feu"
    DMZ = "dmz", "DMZ"
    OTHER_NETWORK = "other_network", "Autre réseau"
    # Person
    INTERNAL_STAFF = "internal_staff", "Personnel interne"
    CONTRACTOR = "contractor", "Prestataire"
    EXTERNAL_PROVIDER = "external_provider", "Fournisseur externe"
    ADMINISTRATOR = "administrator", "Administrateur"
    DEVELOPER = "developer", "Développeur"
    OTHER_PERSON = "other_person", "Autre personne"
    # Site
    DATACENTER = "datacenter", "Centre de données"
    OFFICE = "office", "Bureau"
    REMOTE_SITE = "remote_site", "Site distant"
    CLOUD_REGION = "cloud_region", "Région cloud"
    OTHER_SITE = "other_site", "Autre site"
    # Service
    CLOUD_SERVICE = "cloud_service", "Service cloud"
    HOSTING_SERVICE = "hosting_service", "Service d'hébergement"
    MANAGED_SERVICE = "managed_service", "Service managé"
    TELECOM_SERVICE = "telecom_service", "Service télécom"
    OUTSOURCED_SERVICE = "outsourced_service", "Service externalisé"
    OTHER_SERVICE = "other_service", "Autre service"
    # Paper
    ARCHIVE = "archive", "Archive"
    PRINTED_DOCUMENT = "printed_document", "Document imprimé"
    FORM = "form", "Formulaire"
    OTHER_PAPER = "other_paper", "Autre papier"


# Mapping type → valid categories
SUPPORT_ASSET_CATEGORY_MAP = {
    "hardware": [
        "server", "workstation", "laptop", "mobile_device", "network_equipment",
        "storage", "peripheral", "iot_device", "removable_media", "other_hardware",
    ],
    "software": [
        "operating_system", "database", "application", "middleware",
        "security_tool", "development_tool", "saas_application", "other_software",
    ],
    "network": [
        "lan", "wan", "wifi", "vpn", "internet_link",
        "firewall_zone", "dmz", "other_network",
    ],
    "person": [
        "internal_staff", "contractor", "external_provider",
        "administrator", "developer", "other_person",
    ],
    "site": ["datacenter", "office", "remote_site", "cloud_region", "other_site"],
    "service": [
        "cloud_service", "hosting_service", "managed_service",
        "telecom_service", "outsourced_service", "other_service",
    ],
    "paper": ["archive", "printed_document", "form", "other_paper"],
}


class ExposureLevel(models.TextChoices):
    INTERNAL = "internal", "Interne"
    EXPOSED = "exposed", "Exposé"
    INTERNET_FACING = "internet_facing", "Exposé Internet"
    DMZ = "dmz", "DMZ"


class Environment(models.TextChoices):
    PRODUCTION = "production", "Production"
    STAGING = "staging", "Pré-production"
    DEVELOPMENT = "development", "Développement"
    TEST = "test", "Test"
    DISASTER_RECOVERY = "disaster_recovery", "Reprise d'activité"


class SupportAssetStatus(models.TextChoices):
    IN_STOCK = "in_stock", "En stock"
    DEPLOYED = "deployed", "Déployé"
    ACTIVE = "active", "Actif"
    UNDER_MAINTENANCE = "under_maintenance", "En maintenance"
    DECOMMISSIONED = "decommissioned", "Décommissionné"
    DISPOSED = "disposed", "Éliminé"


# ── Asset Dependency ────────────────────────────────────────

class DependencyType(models.TextChoices):
    RUNS_ON = "runs_on", "Fonctionne sur"
    STORED_IN = "stored_in", "Stocké dans"
    TRANSMITTED_BY = "transmitted_by", "Transmis par"
    MANAGED_BY = "managed_by", "Géré par"
    HOSTED_AT = "hosted_at", "Hébergé à"
    PROTECTED_BY = "protected_by", "Protégé par"
    OTHER = "other", "Autre"


class RedundancyLevel(models.TextChoices):
    NONE = "none", "Aucune"
    PARTIAL = "partial", "Partielle"
    FULL = "full", "Complète"


# ── Asset Group ─────────────────────────────────────────────

class AssetGroupStatus(models.TextChoices):
    ACTIVE = "active", "Actif"
    INACTIVE = "inactive", "Inactif"
