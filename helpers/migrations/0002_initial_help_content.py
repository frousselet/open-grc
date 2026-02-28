from django.db import migrations


HELP_CONTENT_FR = [
    {
        "key": "context.dashboard",
        "title": "Gouvernance",
        "body": (
            "Ce module constitue le socle fondateur du dispositif GRC. "
            "Il permet de formaliser le périmètre du système de management "
            "(domaine d'application), d'identifier les enjeux internes et externes, "
            "de recenser les parties intéressées et leurs attentes, de définir les "
            "objectifs, de réaliser des analyses SWOT, d'attribuer les rôles et "
            "responsabilités, et de cartographier les activités métier. "
            "Conforme aux chapitres 4 et 5 de la structure harmonisée ISO "
            "(applicable à l'ISO 27001, 9001, 14001, 22301, 45001, etc.)."
        ),
    },
    {
        "key": "context.scope_list",
        "title": "Périmètres (Scope)",
        "body": (
            "Le périmètre définit le domaine d'application du système de management "
            "(structure harmonisée ISO §4.3). Il précise les limites organisationnelles, "
            "géographiques et techniques couvertes, ainsi que les exclusions justifiées. "
            "Un seul périmètre peut être actif à un instant donné ; les versions "
            "précédentes sont automatiquement archivées."
        ),
    },
    {
        "key": "context.issue_list",
        "title": "Enjeux (Issues)",
        "body": (
            "Les enjeux sont les facteurs internes et externes pouvant influencer "
            "la capacité de l'organisme à atteindre les résultats attendus de son "
            "système de management (structure harmonisée ISO §4.1). Les enjeux internes "
            "couvrent la stratégie, l'organisation, les RH, la technique et la culture. "
            "Les enjeux externes couvrent les aspects politiques, économiques, sociaux, "
            "technologiques, juridiques et environnementaux."
        ),
    },
    {
        "key": "context.stakeholder_list",
        "title": "Parties intéressées (Stakeholders)",
        "body": (
            "Les parties intéressées sont les personnes ou organismes pouvant affecter, "
            "être affectés ou se sentir affectés par les décisions de l'organisme "
            "(structure harmonisée ISO §4.2). Pour chaque partie intéressée, on évalue "
            "son niveau d'influence et d'intérêt, et on recense ses attentes et "
            "exigences vis-à-vis du système de management."
        ),
    },
    {
        "key": "context.objective_list",
        "title": "Objectifs",
        "body": (
            "Les objectifs du système de management doivent être mesurables et "
            "cohérents avec la politique de l'organisme (structure harmonisée ISO §6.2). "
            "Chaque objectif est rattaché à un périmètre, assigné à un responsable, "
            "et suivi via un pourcentage d'avancement. Les objectifs peuvent être "
            "hiérarchisés (parent/enfant) et liés aux enjeux et parties intéressées."
        ),
    },
    {
        "key": "context.swot_list",
        "title": "Analyses SWOT",
        "body": (
            "L'analyse SWOT permet d'identifier les Forces (Strengths), "
            "Faiblesses (Weaknesses), Opportunités (Opportunities) et Menaces (Threats) "
            "du dispositif GRC. Chaque élément est classé par impact et peut être lié "
            "aux enjeux et objectifs identifiés. L'analyse SWOT fournit une vision "
            "synthétique pour orienter la stratégie de l'organisme."
        ),
    },
    {
        "key": "context.role_list",
        "title": "Rôles et responsabilités",
        "body": (
            "Les rôles définissent les fonctions et responsabilités au sein du système "
            "de management de l'organisme (structure harmonisée ISO §5.3). Chaque rôle "
            "peut être de type stratégique, opérationnel ou technique, et ses "
            "responsabilités sont formalisées via la matrice RACI. Les rôles "
            "obligatoires non assignés sont signalés en alerte."
        ),
    },
    {
        "key": "context.activity_list",
        "title": "Activités et processus",
        "body": (
            "Les activités et processus représentent les fonctions métier et techniques "
            "de l'organisme qui entrent dans le périmètre du système de management. "
            "Chaque activité est caractérisée par son type (métier, support, management), "
            "sa criticité et son responsable. Elles servent de base à l'identification "
            "des actifs et à l'analyse des risques et opportunités."
        ),
    },
    {
        "key": "assets.dashboard",
        "title": "Risques",
        "body": (
            "Le module de gestion des actifs permet d'inventorier les biens essentiels "
            "(processus, informations) et les biens supports (matériel, logiciel, réseau, "
            "sites, personnes) de l'organisme. Les niveaux de valorisation DIC "
            "(Disponibilité, Intégrité, Confidentialité) sont hérités automatiquement "
            "des biens essentiels vers les biens supports via les relations de "
            "dépendance. Ce module s'inscrit dans la démarche d'identification des "
            "actifs requise par les référentiels applicables (ISO 27001, EBIOS RM, etc.)."
        ),
    },
    {
        "key": "assets.essential_asset_list",
        "title": "Biens essentiels",
        "body": (
            "Les biens essentiels sont les processus métier et informations qui ont "
            "de la valeur pour l'organisme et qui nécessitent une protection. "
            "Chaque bien essentiel est évalué selon les critères DIC (Disponibilité, "
            "Intégrité, Confidentialité) sur une échelle de 0 à 4. Ces niveaux sont "
            "propagés aux biens supports associés via les relations de dépendance."
        ),
    },
    {
        "key": "assets.support_asset_list",
        "title": "Biens supports",
        "body": (
            "Les biens supports sont les composants du système d'information sur "
            "lesquels reposent les biens essentiels : matériel, logiciel, réseau, "
            "personnes, sites et services. Leurs niveaux DIC sont hérités "
            "automatiquement des biens essentiels auxquels ils sont liés (algorithme MAX). "
            "Les biens en fin de vie ou orphelins (sans bien essentiel associé) sont "
            "signalés en alerte."
        ),
    },
    {
        "key": "assets.dependency_list",
        "title": "Relations de dépendance",
        "body": (
            "Les relations de dépendance lient les biens essentiels aux biens supports "
            "qui les portent. Chaque dépendance est caractérisée par son type "
            "(hébergement, traitement, accès, transport), sa criticité et son niveau "
            "de redondance. Les points uniques de défaillance (SPOF) — biens supports "
            "critiques sans redondance — sont automatiquement détectés et signalés."
        ),
    },
    {
        "key": "assets.group_list",
        "title": "Groupes d'actifs",
        "body": (
            "Les groupes d'actifs permettent de regrouper des biens supports partageant "
            "des caractéristiques communes (même localisation, même fonction, même "
            "technologie) afin de simplifier la gestion et l'analyse des risques. "
            "Un groupe peut être de type logique, géographique, fonctionnel ou "
            "technologique."
        ),
    },
    {
        "key": "accounts.user_list",
        "title": "Utilisateurs",
        "body": (
            "La gestion des utilisateurs permet de créer, modifier et désactiver les "
            "comptes utilisateurs de la plateforme. Chaque utilisateur est identifié "
            "par son adresse email et peut être assigné à un ou plusieurs groupes "
            "déterminant ses droits d'accès."
        ),
    },
    {
        "key": "accounts.group_list",
        "title": "Groupes de permissions",
        "body": (
            "Les groupes permettent d'attribuer des ensembles de permissions aux "
            "utilisateurs. Les groupes système sont créés à l'installation et ne "
            "peuvent pas être modifiés. Des groupes personnalisés peuvent être créés "
            "pour répondre aux besoins spécifiques de l'organisme."
        ),
    },
    {
        "key": "accounts.permission_list",
        "title": "Permissions",
        "body": (
            "Les permissions contrôlent l'accès granulaire aux fonctionnalités de la "
            "plateforme. Chaque permission suit le format module.feature.action et "
            "est attribuée exclusivement via les groupes."
        ),
    },
    {
        "key": "accounts.access_log_list",
        "title": "Journal des accès",
        "body": (
            "Le journal des accès enregistre tous les événements d'authentification : "
            "connexions réussies et échouées, déconnexions, verrouillages de compte "
            "et changements de mot de passe. Il permet la traçabilité et la détection "
            "d'anomalies de sécurité."
        ),
    },
]


def populate_help_content(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for item in HELP_CONTENT_FR:
        HelpContent.objects.update_or_create(
            key=item["key"],
            language="fr",
            defaults={"title": item["title"], "body": item["body"]},
        )


def reverse(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    keys = [item["key"] for item in HELP_CONTENT_FR]
    HelpContent.objects.filter(key__in=keys, language="fr").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_help_content, reverse),
    ]
