from django.db import migrations


HELP_CONTENT_FR = [
    # ── Home ──────────────────────────────────────────────────
    {
        "key": "home",
        "title": "Tableau de bord général",
        "body": (
            "Le tableau de bord offre une vue synthétique de l'ensemble du dispositif "
            "GRC : gouvernance, gestion des actifs, conformité et risques. Les indicateurs "
            "clés (KPI) et graphiques permettent de suivre en temps réel l'état d'avancement "
            "des différents modules et d'identifier rapidement les points d'attention."
        ),
    },
    # ── Context (manquant) ────────────────────────────────────
    {
        "key": "context.site_list",
        "title": "Sites",
        "body": (
            "Les sites représentent les implantations géographiques de l'organisme "
            "(sièges, agences, datacenters, sites industriels, etc.). Chaque site est "
            "caractérisé par son adresse, son type et sa criticité. Les sites servent "
            "de référence pour la localisation des biens supports et l'analyse "
            "des risques liés aux menaces physiques et environnementales."
        ),
    },
    # ── Accounts (manquant) ───────────────────────────────────
    {
        "key": "accounts.action_log_list",
        "title": "Journal des actions",
        "body": (
            "Le journal des actions trace l'ensemble des opérations effectuées par les "
            "utilisateurs sur la plateforme : créations, modifications, suppressions et "
            "approbations d'objets. Il permet d'assurer la traçabilité complète des "
            "changements et de répondre aux exigences d'audit."
        ),
    },
    # ── Compliance ────────────────────────────────────────────
    {
        "key": "compliance.dashboard",
        "title": "Conformité",
        "body": (
            "Le module de conformité permet de gérer les référentiels réglementaires et "
            "normatifs applicables à l'organisme, d'évaluer le niveau de conformité par "
            "rapport à chaque exigence, et de piloter les plans d'action de mise en "
            "conformité. Il couvre l'ensemble du cycle : import des référentiels, "
            "évaluation, cartographie des écarts et suivi des remédiations."
        ),
    },
    {
        "key": "compliance.framework_list",
        "title": "Référentiels",
        "body": (
            "Les référentiels regroupent les normes, réglementations et cadres de bonnes "
            "pratiques applicables à l'organisme (ISO 27001, RGPD, NIS 2, etc.). Chaque "
            "référentiel est structuré en sections hiérarchiques contenant des exigences. "
            "Les référentiels peuvent être importés depuis des fichiers JSON ou Excel, "
            "et leur applicabilité peut être ajustée selon le périmètre."
        ),
    },
    {
        "key": "compliance.requirement_list",
        "title": "Exigences",
        "body": (
            "Les exigences sont les obligations individuelles issues des référentiels "
            "applicables. Chaque exigence est rattachée à une section d'un référentiel "
            "et peut être de type obligatoire, recommandé ou optionnel. Les exigences "
            "servent de base aux évaluations de conformité et aux plans d'action."
        ),
    },
    {
        "key": "compliance.assessment_list",
        "title": "Évaluations de conformité",
        "body": (
            "Les évaluations de conformité permettent de mesurer le niveau de conformité "
            "de l'organisme par rapport à un référentiel donné, dans un périmètre défini. "
            "Chaque évaluation produit des résultats par exigence (conforme, partiellement "
            "conforme, non conforme, non applicable) et identifie les écarts à combler."
        ),
    },
    {
        "key": "compliance.mapping_list",
        "title": "Mappings inter-référentiels",
        "body": (
            "Les mappings inter-référentiels établissent des correspondances entre les "
            "exigences de différents référentiels. Ils permettent d'identifier les "
            "recouvrements, d'optimiser les efforts de mise en conformité et de démontrer "
            "comment la satisfaction d'une exigence contribue à la conformité d'autres "
            "référentiels (ex : ISO 27001 → RGPD, NIS 2 → ISO 27001)."
        ),
    },
    {
        "key": "compliance.action_plan_list",
        "title": "Plans d'action de conformité",
        "body": (
            "Les plans d'action de conformité formalisent les actions correctives et "
            "préventives nécessaires pour combler les écarts identifiés lors des "
            "évaluations. Chaque plan d'action est rattaché à une évaluation et une "
            "exigence, avec un responsable, une priorité, des dates cibles et un "
            "suivi de l'avancement."
        ),
    },
    {
        "key": "compliance.framework_import",
        "title": "Import de référentiel",
        "body": (
            "L'import permet de charger un référentiel complet avec toute son arborescence "
            "(sections et exigences) depuis un fichier JSON ou Excel. Le fichier est "
            "analysé et un aperçu est présenté avant confirmation. Il est possible "
            "d'importer dans un référentiel existant pour y ajouter de nouvelles "
            "sections et exigences."
        ),
    },
    # ── Risks ─────────────────────────────────────────────────
    {
        "key": "risks.dashboard",
        "title": "Gestion des risques",
        "body": (
            "Le module de gestion des risques couvre l'ensemble du processus "
            "d'appréciation et de traitement des risques conformément à l'ISO 27005 "
            "et à l'ISO 31000. Il permet d'identifier, analyser et évaluer les risques, "
            "de définir des plans de traitement, et de suivre les acceptations de "
            "risques résiduels. Les tableaux de bord offrent une vision consolidée "
            "du niveau de risque de l'organisme."
        ),
    },
    {
        "key": "risks.risk_list",
        "title": "Registre des risques",
        "body": (
            "Le registre des risques centralise l'ensemble des risques identifiés "
            "pour l'organisme. Chaque risque est caractérisé par sa source, ses "
            "conséquences, sa vraisemblance et son impact, permettant de calculer "
            "un niveau de risque brut et résiduel. Les risques peuvent être liés "
            "aux actifs, menaces et vulnérabilités identifiés."
        ),
    },
    {
        "key": "risks.assessment_list",
        "title": "Appréciations des risques",
        "body": (
            "Les appréciations des risques formalisent le processus d'identification, "
            "d'analyse et d'évaluation des risques dans un périmètre donné. Chaque "
            "appréciation suit une méthodologie définie (ISO 27005, EBIOS RM, etc.) "
            "et produit une liste de risques évalués avec leurs niveaux."
        ),
    },
    {
        "key": "risks.criteria_list",
        "title": "Critères de risque",
        "body": (
            "Les critères de risque définissent les échelles et seuils utilisés pour "
            "l'évaluation des risques : échelle de vraisemblance, échelle d'impact, "
            "matrice de risque et seuils d'acceptabilité. Ils garantissent la cohérence "
            "et la reproductibilité des appréciations des risques."
        ),
    },
    {
        "key": "risks.treatment_plan_list",
        "title": "Plans de traitement",
        "body": (
            "Les plans de traitement définissent les mesures à mettre en œuvre pour "
            "ramener les risques à un niveau acceptable. Les options de traitement "
            "incluent la réduction (mise en place de contrôles), le transfert "
            "(assurance, sous-traitance), l'évitement (suppression de l'activité) "
            "et l'acceptation (risque résiduel validé)."
        ),
    },
    {
        "key": "risks.acceptance_list",
        "title": "Acceptations de risque",
        "body": (
            "Les acceptations de risque formalisent la décision de la direction "
            "d'accepter un risque résiduel après traitement. Chaque acceptation "
            "est documentée avec sa justification, sa date de validité et le "
            "signataire responsable. Les acceptations expirées ou à renouveler "
            "sont signalées automatiquement."
        ),
    },
    {
        "key": "risks.threat_list",
        "title": "Menaces",
        "body": (
            "Les menaces représentent les causes potentielles d'incidents pouvant "
            "porter atteinte aux actifs de l'organisme. Elles sont classées par "
            "type (naturelle, humaine, technique, environnementale) et par origine "
            "(accidentelle, délibérée). Le catalogue de menaces sert de base à "
            "l'identification des scénarios de risque."
        ),
    },
    {
        "key": "risks.vulnerability_list",
        "title": "Vulnérabilités",
        "body": (
            "Les vulnérabilités sont les faiblesses des actifs ou des mesures de "
            "sécurité pouvant être exploitées par des menaces. Elles sont caractérisées "
            "par leur sévérité, leur facilité d'exploitation et les actifs concernés. "
            "Le suivi des vulnérabilités permet de prioriser les actions correctives "
            "et de réduire la surface d'attaque."
        ),
    },
    {
        "key": "risks.iso27005_risk_list",
        "title": "Analyses ISO 27005",
        "body": (
            "Les analyses ISO 27005 permettent de conduire une appréciation des risques "
            "selon la méthodologie définie par la norme ISO/IEC 27005. Chaque analyse "
            "croise les biens supports, les menaces et les vulnérabilités pour identifier "
            "les scénarios de risque, évaluer leur niveau et proposer des mesures de "
            "traitement adaptées."
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
        ("helpers", "0002_initial_help_content"),
    ]

    operations = [
        migrations.RunPython(populate_help_content, reverse),
    ]
