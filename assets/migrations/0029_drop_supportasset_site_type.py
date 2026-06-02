# Generated manually on 2026-06-02

"""Drop the `site` type from SupportAsset and convert existing rows to Site (closes #30 part 1).

Until now a physical location could be modelled two ways: as a Site in
the context module (with parent_site hierarchy, address, status) or as
a SupportAsset[type=site] in the asset inventory. The redundancy
showed up in the QA report (#30) where the same Bron datacenter was
saved twice during population.

Decision: keep Site as the canonical model for physical locations, and
remove the site type from SupportAsset. The conversion is automated:

1. For each SupportAsset whose type is "site":
   a. Create a Site with the support asset's name, the mapped type
      (datacenter -> datacenter, office -> office, remote_site ->
      remote, cloud_region -> datacenter, other_site -> other),
      location -> address, description copied across.
   b. Remove the support asset from every AssetGroup. Groups now
      only contain real support assets, not sites.
   c. Delete the SupportAsset row. AssetDependency rows that pointed
      at it cascade-delete; their original semantics ("depends on a
      site") were conceptually fuzzy anyway, and the operator should
      re-establish proper SiteAssetDependency rows pointing at the
      new Site if needed.

2. Alter the SupportAsset.type / SupportAsset.category choices to
   reflect the new enum (no more `site`, no more site sub-categories).
   AssetGroup.type follows the same enum so it gets the same alter.

Reverse is intentionally not provided: a converted Site cannot
faithfully reconstruct its original SupportAsset (owner, DIC, etc.
were not carried over because Site does not track them). Run a
schema-only revert and restore the data from a backup if needed.
"""

from django.db import migrations, models


SUPPORT_ASSET_TYPE_CHOICES = [
    ("hardware", "Hardware"),
    ("software", "Software"),
    ("network", "Network"),
    ("person", "Person"),
    ("service", "Service"),
    ("paper", "Paper"),
]

SUPPORT_ASSET_CATEGORY_CHOICES = [
    ("server", "Server"),
    ("workstation", "Workstation"),
    ("laptop", "Laptop"),
    ("mobile_device", "Mobile device"),
    ("network_equipment", "Network equipment"),
    ("storage", "Storage"),
    ("peripheral", "Peripheral"),
    ("iot_device", "IoT device"),
    ("removable_media", "Removable media"),
    ("other_hardware", "Other hardware"),
    ("operating_system", "Operating system"),
    ("database", "Database"),
    ("application", "Application"),
    ("middleware", "Middleware"),
    ("security_tool", "Security tool"),
    ("development_tool", "Development tool"),
    ("saas_application", "SaaS application"),
    ("other_software", "Other software"),
    ("lan", "Local area network (LAN)"),
    ("wan", "Wide area network (WAN)"),
    ("wifi", "Wi-Fi"),
    ("vpn", "VPN"),
    ("internet_link", "Internet link"),
    ("firewall_zone", "Firewall zone"),
    ("dmz", "DMZ"),
    ("other_network", "Other network"),
    ("internal_staff", "Internal staff"),
    ("contractor", "Contractor"),
    ("external_provider", "External provider"),
    ("administrator", "Administrator"),
    ("developer", "Developer"),
    ("other_person", "Other person"),
    ("cloud_service", "Cloud service"),
    ("hosting_service", "Hosting service"),
    ("managed_service", "Managed service"),
    ("telecom_service", "Telecom service"),
    ("outsourced_service", "Outsourced service"),
    ("other_service", "Other service"),
    ("archive", "Archive"),
    ("printed_document", "Printed document"),
    ("form", "Form"),
    ("other_paper", "Other paper"),
]

# Map old SupportAsset[type=site] category -> Site.type (English values
# from context.0027). cloud_region has no direct Site equivalent so we
# bucket it under datacenter; the operator can refine later.
CATEGORY_TO_SITE_TYPE = {
    "datacenter": "datacenter",
    "office": "office",
    "remote_site": "remote",
    "cloud_region": "datacenter",
    "other_site": "other",
}


def _next_site_reference_index(Site):
    """Compute the next SITE-N suffix from existing references."""
    prefix = "SITE-"
    prefix_len = len(prefix)
    max_num = 0
    for ref in Site.objects.filter(reference__startswith=prefix).values_list(
        "reference", flat=True
    ):
        try:
            max_num = max(max_num, int(ref[prefix_len:]))
        except (ValueError, IndexError):
            continue
    return max_num + 1


def convert_site_support_assets(apps, schema_editor):
    SupportAsset = apps.get_model("assets", "SupportAsset")
    AssetGroup = apps.get_model("assets", "AssetGroup")
    Site = apps.get_model("context", "Site")

    site_assets = SupportAsset.objects.filter(type="site")
    next_index = _next_site_reference_index(Site)
    for asset in site_assets:
        Site.objects.create(
            reference=f"SITE-{next_index}",
            name=asset.name,
            type=CATEGORY_TO_SITE_TYPE.get(asset.category, "other"),
            address=asset.location or "",
            description=asset.description or "",
            status="active",
        )
        next_index += 1
        # Remove from every asset group: groups hold real assets only.
        for group in AssetGroup.objects.filter(members=asset):
            group.members.remove(asset)
    # Cascade-delete the converted rows. AssetDependency rows that
    # pointed at them go with them.
    site_assets.delete()


def unconvert(apps, schema_editor):
    raise RuntimeError(
        "context.0028 + assets.0029 are not reversible. "
        "Restore from a database backup if you need the pre-migration state."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0028_supportasset_supplier_fk"),
        ("context", "0028_site_scopes"),
    ]

    operations = [
        migrations.RunPython(convert_site_support_assets, unconvert),
        migrations.AlterField(
            model_name="assetgroup",
            name="type",
            field=models.CharField(
                choices=SUPPORT_ASSET_TYPE_CHOICES, max_length=20, verbose_name="Type"
            ),
        ),
        migrations.AlterField(
            model_name="historicalassetgroup",
            name="type",
            field=models.CharField(
                choices=SUPPORT_ASSET_TYPE_CHOICES, max_length=20, verbose_name="Type"
            ),
        ),
        migrations.AlterField(
            model_name="supportasset",
            name="type",
            field=models.CharField(
                choices=SUPPORT_ASSET_TYPE_CHOICES, max_length=20, verbose_name="Type"
            ),
        ),
        migrations.AlterField(
            model_name="historicalsupportasset",
            name="type",
            field=models.CharField(
                choices=SUPPORT_ASSET_TYPE_CHOICES, max_length=20, verbose_name="Type"
            ),
        ),
        migrations.AlterField(
            model_name="supportasset",
            name="category",
            field=models.CharField(
                choices=SUPPORT_ASSET_CATEGORY_CHOICES, max_length=30, verbose_name="Category"
            ),
        ),
        migrations.AlterField(
            model_name="historicalsupportasset",
            name="category",
            field=models.CharField(
                choices=SUPPORT_ASSET_CATEGORY_CHOICES, max_length=30, verbose_name="Category"
            ),
        ),
    ]
