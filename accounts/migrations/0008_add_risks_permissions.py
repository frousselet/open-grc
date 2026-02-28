"""
Data migration: add risks module permissions and assign them to system groups.
"""

from django.db import migrations


RISKS_PERMISSIONS = [
    # assessment
    ("risks.assessment.create", "Gestion des risques — Appréciations des risques — Créer", "risks", "assessment", "create"),
    ("risks.assessment.read", "Gestion des risques — Appréciations des risques — Lire", "risks", "assessment", "read"),
    ("risks.assessment.update", "Gestion des risques — Appréciations des risques — Modifier", "risks", "assessment", "update"),
    ("risks.assessment.delete", "Gestion des risques — Appréciations des risques — Supprimer", "risks", "assessment", "delete"),
    ("risks.assessment.approve", "Gestion des risques — Appréciations des risques — Approuver", "risks", "assessment", "approve"),
    # criteria
    ("risks.criteria.create", "Gestion des risques — Critères de risque — Créer", "risks", "criteria", "create"),
    ("risks.criteria.read", "Gestion des risques — Critères de risque — Lire", "risks", "criteria", "read"),
    ("risks.criteria.update", "Gestion des risques — Critères de risque — Modifier", "risks", "criteria", "update"),
    ("risks.criteria.delete", "Gestion des risques — Critères de risque — Supprimer", "risks", "criteria", "delete"),
    # risk
    ("risks.risk.create", "Gestion des risques — Registre des risques — Créer", "risks", "risk", "create"),
    ("risks.risk.read", "Gestion des risques — Registre des risques — Lire", "risks", "risk", "read"),
    ("risks.risk.update", "Gestion des risques — Registre des risques — Modifier", "risks", "risk", "update"),
    ("risks.risk.delete", "Gestion des risques — Registre des risques — Supprimer", "risks", "risk", "delete"),
    ("risks.risk.approve", "Gestion des risques — Registre des risques — Approuver", "risks", "risk", "approve"),
    # treatment
    ("risks.treatment.create", "Gestion des risques — Plans de traitement — Créer", "risks", "treatment", "create"),
    ("risks.treatment.read", "Gestion des risques — Plans de traitement — Lire", "risks", "treatment", "read"),
    ("risks.treatment.update", "Gestion des risques — Plans de traitement — Modifier", "risks", "treatment", "update"),
    ("risks.treatment.delete", "Gestion des risques — Plans de traitement — Supprimer", "risks", "treatment", "delete"),
    ("risks.treatment.approve", "Gestion des risques — Plans de traitement — Approuver", "risks", "treatment", "approve"),
    # acceptance
    ("risks.acceptance.create", "Gestion des risques — Acceptations de risque — Créer", "risks", "acceptance", "create"),
    ("risks.acceptance.read", "Gestion des risques — Acceptations de risque — Lire", "risks", "acceptance", "read"),
    ("risks.acceptance.update", "Gestion des risques — Acceptations de risque — Modifier", "risks", "acceptance", "update"),
    ("risks.acceptance.delete", "Gestion des risques — Acceptations de risque — Supprimer", "risks", "acceptance", "delete"),
    # threat
    ("risks.threat.create", "Gestion des risques — Menaces — Créer", "risks", "threat", "create"),
    ("risks.threat.read", "Gestion des risques — Menaces — Lire", "risks", "threat", "read"),
    ("risks.threat.update", "Gestion des risques — Menaces — Modifier", "risks", "threat", "update"),
    ("risks.threat.delete", "Gestion des risques — Menaces — Supprimer", "risks", "threat", "delete"),
    # vulnerability
    ("risks.vulnerability.create", "Gestion des risques — Vulnérabilités — Créer", "risks", "vulnerability", "create"),
    ("risks.vulnerability.read", "Gestion des risques — Vulnérabilités — Lire", "risks", "vulnerability", "read"),
    ("risks.vulnerability.update", "Gestion des risques — Vulnérabilités — Modifier", "risks", "vulnerability", "update"),
    ("risks.vulnerability.delete", "Gestion des risques — Vulnérabilités — Supprimer", "risks", "vulnerability", "delete"),
    # iso27005
    ("risks.iso27005.create", "Gestion des risques — Analyses ISO 27005 — Créer", "risks", "iso27005", "create"),
    ("risks.iso27005.read", "Gestion des risques — Analyses ISO 27005 — Lire", "risks", "iso27005", "read"),
    ("risks.iso27005.update", "Gestion des risques — Analyses ISO 27005 — Modifier", "risks", "iso27005", "update"),
    ("risks.iso27005.delete", "Gestion des risques — Analyses ISO 27005 — Supprimer", "risks", "iso27005", "delete"),
    # export
    ("risks.export.read", "Gestion des risques — Export des risques — Lire", "risks", "export", "read"),
    # audit_trail
    ("risks.audit_trail.read", "Gestion des risques — Journal d'audit des risques — Lire", "risks", "audit_trail", "read"),
]

# Groups filter follows SYSTEM_GROUPS logic from accounts/constants.py
GROUP_FILTERS = {
    "Super Administrateur": lambda codename: True,
    "Administrateur": lambda codename: True,
    "RSSI / DPO": lambda codename: (
        codename.endswith(".read")
        or codename.endswith(".create")
        or codename.endswith(".update")
        or codename.endswith(".approve")
    ),
    "Auditeur": lambda codename: codename.endswith(".read"),
    "Contributeur": lambda codename: (
        codename.endswith(".read")
        or codename.endswith(".create")
        or codename.endswith(".update")
    ),
    "Lecteur": lambda codename: codename.endswith(".read"),
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    all_perms = []
    for codename, name, module, feature, action in RISKS_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                "name": name,
                "module": module,
                "feature": feature,
                "action": action,
                "is_system": True,
            },
        )
        all_perms.append(perm)

    for group_name, filter_fn in GROUP_FILTERS.items():
        try:
            group = Group.objects.get(name=group_name)
            matching = [p for p in all_perms if filter_fn(p.codename)]
            group.permissions.add(*matching)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [c for c, _, _, _, _ in RISKS_PERMISSIONS]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_add_site_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
