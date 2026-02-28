from django.db import models
from django.utils.translation import gettext_lazy as _


# ── DIC Levels ──────────────────────────────────────────────

class DICLevel(models.IntegerChoices):
    NEGLIGIBLE = 0, _("Negligible")
    LOW = 1, _("Low")
    MEDIUM = 2, _("Medium")
    HIGH = 3, _("High")
    CRITICAL = 4, _("Critical")


# ── Essential Asset ─────────────────────────────────────────

class EssentialAssetType(models.TextChoices):
    BUSINESS_PROCESS = "business_process", _("Business process")
    INFORMATION = "information", _("Information")


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
    CORE_PROCESS = "core_process", _("Core business process")
    SUPPORT_PROCESS = "support_process", _("Support process")
    MANAGEMENT_PROCESS = "management_process", _("Management process")
    # Information
    STRATEGIC_DATA = "strategic_data", _("Strategic data")
    OPERATIONAL_DATA = "operational_data", _("Operational data")
    PERSONAL_DATA = "personal_data", _("Personal data")
    FINANCIAL_DATA = "financial_data", _("Financial data")
    TECHNICAL_DATA = "technical_data", _("Technical data")
    LEGAL_DATA = "legal_data", _("Legal data")
    RESEARCH_DATA = "research_data", _("Research data")
    COMMERCIAL_DATA = "commercial_data", _("Commercial data")


class DataClassification(models.TextChoices):
    PUBLIC = "public", _("Public")
    INTERNAL = "internal", _("Internal")
    CONFIDENTIAL = "confidential", _("Confidential")
    RESTRICTED = "restricted", _("Restricted")
    SECRET = "secret", _("Secret")


class EssentialAssetStatus(models.TextChoices):
    IDENTIFIED = "identified", _("Identified")
    ACTIVE = "active", _("Active")
    UNDER_REVIEW = "under_review", _("Under review")
    DECOMMISSIONED = "decommissioned", _("Decommissioned")


# ── Support Asset ───────────────────────────────────────────

class SupportAssetType(models.TextChoices):
    HARDWARE = "hardware", _("Hardware")
    SOFTWARE = "software", _("Software")
    NETWORK = "network", _("Network")
    PERSON = "person", _("Person")
    SITE = "site", _("Site")
    SERVICE = "service", _("Service")
    PAPER = "paper", _("Paper")


class SupportAssetCategory(models.TextChoices):
    # Hardware
    SERVER = "server", _("Server")
    WORKSTATION = "workstation", _("Workstation")
    LAPTOP = "laptop", _("Laptop")
    MOBILE_DEVICE = "mobile_device", _("Mobile device")
    NETWORK_EQUIPMENT = "network_equipment", _("Network equipment")
    STORAGE = "storage", _("Storage")
    PERIPHERAL = "peripheral", _("Peripheral")
    IOT_DEVICE = "iot_device", _("IoT device")
    REMOVABLE_MEDIA = "removable_media", _("Removable media")
    OTHER_HARDWARE = "other_hardware", _("Other hardware")
    # Software
    OPERATING_SYSTEM = "operating_system", _("Operating system")
    DATABASE = "database", _("Database")
    APPLICATION = "application", _("Application")
    MIDDLEWARE = "middleware", _("Middleware")
    SECURITY_TOOL = "security_tool", _("Security tool")
    DEVELOPMENT_TOOL = "development_tool", _("Development tool")
    SAAS_APPLICATION = "saas_application", _("SaaS application")
    OTHER_SOFTWARE = "other_software", _("Other software")
    # Network
    LAN = "lan", _("Local area network (LAN)")
    WAN = "wan", _("Wide area network (WAN)")
    WIFI = "wifi", _("Wi-Fi")
    VPN = "vpn", _("VPN")
    INTERNET_LINK = "internet_link", _("Internet link")
    FIREWALL_ZONE = "firewall_zone", _("Firewall zone")
    DMZ = "dmz", _("DMZ")
    OTHER_NETWORK = "other_network", _("Other network")
    # Person
    INTERNAL_STAFF = "internal_staff", _("Internal staff")
    CONTRACTOR = "contractor", _("Contractor")
    EXTERNAL_PROVIDER = "external_provider", _("External provider")
    ADMINISTRATOR = "administrator", _("Administrator")
    DEVELOPER = "developer", _("Developer")
    OTHER_PERSON = "other_person", _("Other person")
    # Site
    DATACENTER = "datacenter", _("Datacenter")
    OFFICE = "office", _("Office")
    REMOTE_SITE = "remote_site", _("Remote site")
    CLOUD_REGION = "cloud_region", _("Cloud region")
    OTHER_SITE = "other_site", _("Other site")
    # Service
    CLOUD_SERVICE = "cloud_service", _("Cloud service")
    HOSTING_SERVICE = "hosting_service", _("Hosting service")
    MANAGED_SERVICE = "managed_service", _("Managed service")
    TELECOM_SERVICE = "telecom_service", _("Telecom service")
    OUTSOURCED_SERVICE = "outsourced_service", _("Outsourced service")
    OTHER_SERVICE = "other_service", _("Other service")
    # Paper
    ARCHIVE = "archive", _("Archive")
    PRINTED_DOCUMENT = "printed_document", _("Printed document")
    FORM = "form", _("Form")
    OTHER_PAPER = "other_paper", _("Other paper")


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
    INTERNAL = "internal", _("Internal")
    EXPOSED = "exposed", _("Exposed")
    INTERNET_FACING = "internet_facing", _("Internet-facing")
    DMZ = "dmz", _("DMZ")


class Environment(models.TextChoices):
    PRODUCTION = "production", _("Production")
    STAGING = "staging", _("Staging")
    DEVELOPMENT = "development", _("Development")
    TEST = "test", _("Test")
    DISASTER_RECOVERY = "disaster_recovery", _("Disaster recovery")


class SupportAssetStatus(models.TextChoices):
    IN_STOCK = "in_stock", _("In stock")
    DEPLOYED = "deployed", _("Deployed")
    ACTIVE = "active", _("Active")
    UNDER_MAINTENANCE = "under_maintenance", _("Under maintenance")
    DECOMMISSIONED = "decommissioned", _("Decommissioned")
    DISPOSED = "disposed", _("Disposed")


# ── Asset Dependency ────────────────────────────────────────

class DependencyType(models.TextChoices):
    RUNS_ON = "runs_on", _("Runs on")
    STORED_IN = "stored_in", _("Stored in")
    TRANSMITTED_BY = "transmitted_by", _("Transmitted by")
    MANAGED_BY = "managed_by", _("Managed by")
    HOSTED_AT = "hosted_at", _("Hosted at")
    PROTECTED_BY = "protected_by", _("Protected by")
    OTHER = "other", _("Other")


class RedundancyLevel(models.TextChoices):
    NONE = "none", _("None")
    PARTIAL = "partial", _("Partial")
    FULL = "full", _("Full")


# ── Asset Group ─────────────────────────────────────────────

class AssetGroupStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
