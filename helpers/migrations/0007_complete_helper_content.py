from django.db import migrations

# ── English content ─────────────────────────────────────────────────
HELP_CONTENT_EN = [
    # ── Context — detail pages ──────────────────────────────────────
    {
        "key": "context.scope_detail",
        "title": "Scope details",
        "body": (
            "This page presents all information about the selected scope: "
            "description, geographical and organisational boundaries, exclusions, "
            "approval status and version history. You can edit the scope or go back "
            "to the list from the action buttons."
        ),
    },
    {
        "key": "context.issue_detail",
        "title": "Issue details",
        "body": (
            "This page presents the selected issue with its type (internal / external), "
            "impact level and detailed description. Related stakeholders, objectives "
            "and SWOT items are shown in the corresponding tabs."
        ),
    },
    {
        "key": "context.stakeholder_detail",
        "title": "Stakeholder details",
        "body": (
            "This page presents the selected stakeholder with their influence/interest "
            "matrix position, category and documented expectations. Related issues "
            "and requirements are accessible from the tabs."
        ),
    },
    {
        "key": "context.objective_detail",
        "title": "Objective details",
        "body": (
            "This page presents the selected objective with its progress, responsible "
            "party, target date and linked issues. Child objectives and measurement "
            "history are accessible from the tabs."
        ),
    },
    {
        "key": "context.swot_detail",
        "title": "SWOT item details",
        "body": (
            "This page presents the selected SWOT item (Strength, Weakness, "
            "Opportunity or Threat) with its impact ranking and links to related "
            "issues and objectives."
        ),
    },
    {
        "key": "context.role_detail",
        "title": "Role details",
        "body": (
            "This page presents the selected role with its type (strategic, "
            "operational, technical), RACI responsibilities and assigned users. "
            "Mandatory roles without assignees are flagged with a warning."
        ),
    },
    {
        "key": "context.activity_detail",
        "title": "Activity details",
        "body": (
            "This page presents the selected activity or process with its type, "
            "criticality, owner and linked essential assets. The history tab "
            "provides a full audit trail of changes."
        ),
    },
    {
        "key": "context.site_detail",
        "title": "Site details",
        "body": (
            "This page presents the selected site with its address, type, status "
            "and criticality. The tabs show linked support assets, suppliers and "
            "the full change history."
        ),
    },
    # ── Context — new list pages ────────────────────────────────────
    {
        "key": "context.tag_list",
        "title": "Tags",
        "body": (
            "Tags are colour-coded labels that can be attached to various objects "
            "across the platform (sites, scopes, etc.) to facilitate filtering and "
            "categorisation. Each tag has a unique name and a customisable colour."
        ),
    },
    {
        "key": "context.indicator_list",
        "title": "Indicators",
        "body": (
            "Indicators measure the performance and effectiveness of the management "
            "system. They can be organisational (governance-level) or technical "
            "(operational-level). Each indicator has a target value, critical "
            "thresholds and a review frequency. Predefined indicators are computed "
            "automatically from platform data (compliance rate, risk treatment rate, "
            "objective progress, etc.)."
        ),
    },
    {
        "key": "context.indicator_detail",
        "title": "Indicator details",
        "body": (
            "This page presents the selected indicator with its current value, "
            "expected level and critical thresholds. The tabs show the measurement "
            "history, threshold configuration and change log."
        ),
    },
    # ── Assets — detail pages ───────────────────────────────────────
    {
        "key": "assets.essential_asset_detail",
        "title": "Essential asset details",
        "body": (
            "This page presents the selected essential asset with its CIA valuation "
            "(Confidentiality, Integrity, Availability), classification and linked "
            "support assets through dependency relationships."
        ),
    },
    {
        "key": "assets.support_asset_detail",
        "title": "Support asset details",
        "body": (
            "This page presents the selected support asset with its type, lifecycle "
            "status, inherited CIA levels, linked essential assets and supplier "
            "dependencies. End-of-life dates are highlighted when approaching."
        ),
    },
    {
        "key": "assets.group_detail",
        "title": "Asset group details",
        "body": (
            "This page presents the selected asset group with its type (logical, "
            "geographical, functional, technological) and the list of support "
            "assets it contains."
        ),
    },
    {
        "key": "assets.site_detail",
        "title": "Site details (assets)",
        "body": (
            "This page presents the selected site from an asset management "
            "perspective, showing the support assets hosted on the site, supplier "
            "relationships and the associated dependencies."
        ),
    },
    # ── Assets — new list pages ─────────────────────────────────────
    {
        "key": "assets.supplier_list",
        "title": "Suppliers",
        "body": (
            "Suppliers are the external organisations that provide, host, maintain "
            "or operate support assets. Each supplier is characterised by its "
            "criticality, contract dates, status (active, under evaluation, "
            "suspended, archived) and compliance with imposed requirements."
        ),
    },
    {
        "key": "assets.supplier_detail",
        "title": "Supplier details",
        "body": (
            "This page presents the selected supplier with contract information, "
            "contact details, criticality and compliance summary. The tabs show "
            "imposed requirements, linked support assets and the change history."
        ),
    },
    {
        "key": "assets.supplier_type_list",
        "title": "Supplier types",
        "body": (
            "Supplier types let you categorise suppliers (cloud provider, integrator, "
            "outsourcer, etc.) and define template requirements that are automatically "
            "applied to every supplier of that type."
        ),
    },
    {
        "key": "assets.supplier_type_detail",
        "title": "Supplier type details",
        "body": (
            "This page presents the selected supplier type with its description "
            "and the list of template requirements that will be automatically "
            "imposed on suppliers assigned to this type."
        ),
    },
    {
        "key": "assets.supplier_dependency_list",
        "title": "Supplier dependencies",
        "body": (
            "Supplier dependencies link support assets to the suppliers responsible "
            "for them (hosting, maintenance, operation, etc.). Each dependency "
            "records its type, criticality and whether it constitutes a single "
            "point of failure (SPOF)."
        ),
    },
    {
        "key": "assets.supplier_requirement_detail",
        "title": "Supplier requirement details",
        "body": (
            "This page presents the selected requirement imposed on a supplier, "
            "with its compliance status, evidence and review history. Requirements "
            "can originate from a supplier type template or be created manually."
        ),
    },
    {
        "key": "assets.site_supplier_dependency_list",
        "title": "Site–supplier dependencies",
        "body": (
            "Site–supplier dependencies document the relationships between "
            "geographical sites and their suppliers, indicating which supplier "
            "provides services to which site."
        ),
    },
    {
        "key": "assets.site_asset_dependency_list",
        "title": "Site–asset dependencies",
        "body": (
            "Site–asset dependencies document which support assets are hosted "
            "or operated at each geographical site. They help assess the impact "
            "of physical and environmental threats on the information system."
        ),
    },
    # ── Compliance — detail pages ───────────────────────────────────
    {
        "key": "compliance.framework_detail",
        "title": "Framework details",
        "body": (
            "This page presents the selected framework with its full hierarchical "
            "structure of sections and requirements. The tabs provide access to "
            "the requirement tree, linked assessments, scope applicability and "
            "change history."
        ),
    },
    {
        "key": "compliance.requirement_detail",
        "title": "Requirement details",
        "body": (
            "This page presents the selected requirement with its section, "
            "applicability level and description. The tabs show linked "
            "assessment results, cross-framework mappings and action plans."
        ),
    },
    {
        "key": "compliance.assessment_detail",
        "title": "Assessment details",
        "body": (
            "This page presents the selected compliance assessment with its "
            "scope, framework, overall compliance score and per-requirement "
            "results. You can review gaps and launch action plans directly "
            "from this view."
        ),
    },
    {
        "key": "compliance.mapping_detail",
        "title": "Mapping details",
        "body": (
            "This page presents the selected cross-framework mapping with its "
            "source and target requirements, mapping type and rationale."
        ),
    },
    {
        "key": "compliance.action_plan_detail",
        "title": "Action plan details",
        "body": (
            "This page presents the selected action plan with its linked "
            "assessment, requirement, owner, priority, target dates and "
            "progress. The history tab tracks all status changes."
        ),
    },
    # ── Accounts — detail pages ─────────────────────────────────────
    {
        "key": "accounts.user_detail",
        "title": "User details",
        "body": (
            "This page presents the selected user's profile, group memberships, "
            "effective permissions and recent access log. Administrators can "
            "edit the account or manage group assignments from this view."
        ),
    },
    {
        "key": "accounts.group_detail",
        "title": "Group details",
        "body": (
            "This page presents the selected permission group with its assigned "
            "permissions and member users. System groups are read-only; custom "
            "groups can be edited to adjust permissions."
        ),
    },
    # ── Risks — detail pages ────────────────────────────────────────
    {
        "key": "risks.risk_detail",
        "title": "Risk details",
        "body": (
            "This page presents the selected risk with its source, consequences, "
            "likelihood and impact evaluation at three levels (inherent, current, "
            "residual). The tabs show affected assets, treatment decisions and "
            "the full audit trail."
        ),
    },
    {
        "key": "risks.assessment_detail",
        "title": "Risk assessment details",
        "body": (
            "This page presents the selected risk assessment with its scope, "
            "methodology, risk matrix and the list of evaluated risks. The "
            "workflow section shows the assessment progress through its stages."
        ),
    },
    {
        "key": "risks.criteria_detail",
        "title": "Risk criteria details",
        "body": (
            "This page presents the selected risk criteria set with its "
            "likelihood scale, impact scale, risk matrix and acceptability "
            "thresholds. These criteria ensure consistency across risk "
            "assessments."
        ),
    },
    {
        "key": "risks.treatment_plan_detail",
        "title": "Treatment plan details",
        "body": (
            "This page presents the selected treatment plan with its strategy "
            "(reduce, transfer, avoid, accept), linked risks, responsible party, "
            "target dates and implementation progress."
        ),
    },
    {
        "key": "risks.acceptance_detail",
        "title": "Risk acceptance details",
        "body": (
            "This page presents the selected risk acceptance with its "
            "justification, validity period, signatory and the accepted "
            "residual risk level. Expired acceptances are flagged automatically."
        ),
    },
    {
        "key": "risks.threat_detail",
        "title": "Threat details",
        "body": (
            "This page presents the selected threat with its classification "
            "(type and origin), description and the list of risk scenarios "
            "in which it appears."
        ),
    },
    {
        "key": "risks.vulnerability_detail",
        "title": "Vulnerability details",
        "body": (
            "This page presents the selected vulnerability with its severity, "
            "ease of exploitation, affected assets and linked risk scenarios. "
            "The history tab provides a full audit trail."
        ),
    },
    {
        "key": "risks.iso27005_risk_detail",
        "title": "ISO 27005 analysis details",
        "body": (
            "This page presents the selected ISO 27005 risk scenario, showing "
            "the cross-reference between support assets, threats and "
            "vulnerabilities, with the resulting risk level and proposed "
            "treatment measures."
        ),
    },
    # ── Core ────────────────────────────────────────────────────────
    {
        "key": "core.versioning_config_list",
        "title": "Versioning & approval configuration",
        "body": (
            "This page lets you configure the versioning and approval behaviour "
            "for each item type. You can define which field changes trigger a "
            "version increment and approval reset (major fields), and enable or "
            "disable the approval workflow entirely per item type."
        ),
    },
]

# ── French content ──────────────────────────────────────────────────
HELP_CONTENT_FR = [
    # ── Context — pages détail ──────────────────────────────────────
    {
        "key": "context.scope_detail",
        "title": "Détail du périmètre",
        "body": (
            "Cette page présente l'ensemble des informations du périmètre "
            "sélectionné : description, limites géographiques et organisationnelles, "
            "exclusions, statut d'approbation et historique des versions. Vous "
            "pouvez modifier le périmètre ou revenir à la liste depuis les boutons "
            "d'action."
        ),
    },
    {
        "key": "context.issue_detail",
        "title": "Détail de l'enjeu",
        "body": (
            "Cette page présente l'enjeu sélectionné avec son type (interne / "
            "externe), son niveau d'impact et sa description détaillée. Les parties "
            "intéressées, objectifs et éléments SWOT associés sont accessibles "
            "depuis les onglets correspondants."
        ),
    },
    {
        "key": "context.stakeholder_detail",
        "title": "Détail de la partie intéressée",
        "body": (
            "Cette page présente la partie intéressée sélectionnée avec sa "
            "position dans la matrice influence/intérêt, sa catégorie et ses "
            "attentes documentées. Les enjeux et exigences associés sont "
            "accessibles depuis les onglets."
        ),
    },
    {
        "key": "context.objective_detail",
        "title": "Détail de l'objectif",
        "body": (
            "Cette page présente l'objectif sélectionné avec son avancement, "
            "son responsable, sa date cible et ses enjeux associés. Les "
            "sous-objectifs et l'historique des mesures sont accessibles "
            "depuis les onglets."
        ),
    },
    {
        "key": "context.swot_detail",
        "title": "Détail de l'élément SWOT",
        "body": (
            "Cette page présente l'élément SWOT sélectionné (Force, Faiblesse, "
            "Opportunité ou Menace) avec son classement par impact et ses liens "
            "vers les enjeux et objectifs associés."
        ),
    },
    {
        "key": "context.role_detail",
        "title": "Détail du rôle",
        "body": (
            "Cette page présente le rôle sélectionné avec son type (stratégique, "
            "opérationnel, technique), ses responsabilités RACI et les utilisateurs "
            "assignés. Les rôles obligatoires sans titulaire sont signalés par un "
            "avertissement."
        ),
    },
    {
        "key": "context.activity_detail",
        "title": "Détail de l'activité",
        "body": (
            "Cette page présente l'activité ou le processus sélectionné avec son "
            "type, sa criticité, son responsable et les biens essentiels associés. "
            "L'onglet historique fournit une piste d'audit complète des "
            "modifications."
        ),
    },
    {
        "key": "context.site_detail",
        "title": "Détail du site",
        "body": (
            "Cette page présente le site sélectionné avec son adresse, son type, "
            "son statut et sa criticité. Les onglets affichent les biens supports "
            "hébergés, les fournisseurs et l'historique complet des modifications."
        ),
    },
    # ── Context — nouvelles pages liste ─────────────────────────────
    {
        "key": "context.tag_list",
        "title": "Étiquettes",
        "body": (
            "Les étiquettes sont des libellés colorés pouvant être attachés à "
            "divers objets de la plateforme (sites, périmètres, etc.) pour "
            "faciliter le filtrage et la catégorisation. Chaque étiquette possède "
            "un nom unique et une couleur personnalisable."
        ),
    },
    {
        "key": "context.indicator_list",
        "title": "Indicateurs",
        "body": (
            "Les indicateurs mesurent la performance et l'efficacité du système "
            "de management. Ils peuvent être organisationnels (niveau gouvernance) "
            "ou techniques (niveau opérationnel). Chaque indicateur dispose d'une "
            "valeur cible, de seuils critiques et d'une fréquence de revue. Les "
            "indicateurs prédéfinis sont calculés automatiquement à partir des "
            "données de la plateforme (taux de conformité, taux de traitement "
            "des risques, avancement des objectifs, etc.)."
        ),
    },
    {
        "key": "context.indicator_detail",
        "title": "Détail de l'indicateur",
        "body": (
            "Cette page présente l'indicateur sélectionné avec sa valeur actuelle, "
            "son niveau attendu et ses seuils critiques. Les onglets affichent "
            "l'historique des mesures, la configuration des seuils et le journal "
            "des modifications."
        ),
    },
    # ── Assets — pages détail ───────────────────────────────────────
    {
        "key": "assets.essential_asset_detail",
        "title": "Détail du bien essentiel",
        "body": (
            "Cette page présente le bien essentiel sélectionné avec sa valorisation "
            "DIC (Disponibilité, Intégrité, Confidentialité), sa classification "
            "et les biens supports associés via les relations de dépendance."
        ),
    },
    {
        "key": "assets.support_asset_detail",
        "title": "Détail du bien support",
        "body": (
            "Cette page présente le bien support sélectionné avec son type, son "
            "statut de cycle de vie, ses niveaux DIC hérités, les biens essentiels "
            "associés et les dépendances fournisseurs. Les dates de fin de vie "
            "sont mises en évidence à l'approche de l'échéance."
        ),
    },
    {
        "key": "assets.group_detail",
        "title": "Détail du groupe d'actifs",
        "body": (
            "Cette page présente le groupe d'actifs sélectionné avec son type "
            "(logique, géographique, fonctionnel, technologique) et la liste "
            "des biens supports qu'il contient."
        ),
    },
    {
        "key": "assets.site_detail",
        "title": "Détail du site (actifs)",
        "body": (
            "Cette page présente le site sélectionné du point de vue de la "
            "gestion des actifs, montrant les biens supports hébergés, les "
            "relations fournisseurs et les dépendances associées."
        ),
    },
    # ── Assets — nouvelles pages liste ──────────────────────────────
    {
        "key": "assets.supplier_list",
        "title": "Fournisseurs",
        "body": (
            "Les fournisseurs sont les organisations externes qui fournissent, "
            "hébergent, maintiennent ou opèrent les biens supports. Chaque "
            "fournisseur est caractérisé par sa criticité, ses dates de contrat, "
            "son statut (actif, en évaluation, suspendu, archivé) et sa conformité "
            "aux exigences imposées."
        ),
    },
    {
        "key": "assets.supplier_detail",
        "title": "Détail du fournisseur",
        "body": (
            "Cette page présente le fournisseur sélectionné avec les informations "
            "contractuelles, les coordonnées, la criticité et le résumé de "
            "conformité. Les onglets affichent les exigences imposées, les biens "
            "supports associés et l'historique des modifications."
        ),
    },
    {
        "key": "assets.supplier_type_list",
        "title": "Types de fournisseurs",
        "body": (
            "Les types de fournisseurs permettent de catégoriser les fournisseurs "
            "(hébergeur cloud, intégrateur, infogérant, etc.) et de définir des "
            "exigences types automatiquement appliquées à chaque fournisseur "
            "de cette catégorie."
        ),
    },
    {
        "key": "assets.supplier_type_detail",
        "title": "Détail du type de fournisseur",
        "body": (
            "Cette page présente le type de fournisseur sélectionné avec sa "
            "description et la liste des exigences types qui seront automatiquement "
            "imposées aux fournisseurs rattachés à ce type."
        ),
    },
    {
        "key": "assets.supplier_dependency_list",
        "title": "Dépendances fournisseurs",
        "body": (
            "Les dépendances fournisseurs lient les biens supports aux fournisseurs "
            "qui en sont responsables (hébergement, maintenance, exploitation, etc.). "
            "Chaque dépendance enregistre son type, sa criticité et si elle "
            "constitue un point unique de défaillance (SPOF)."
        ),
    },
    {
        "key": "assets.supplier_requirement_detail",
        "title": "Détail de l'exigence fournisseur",
        "body": (
            "Cette page présente l'exigence imposée au fournisseur sélectionné, "
            "avec son statut de conformité, les preuves et l'historique des revues. "
            "Les exigences peuvent provenir d'un type de fournisseur ou être "
            "créées manuellement."
        ),
    },
    {
        "key": "assets.site_supplier_dependency_list",
        "title": "Dépendances site–fournisseur",
        "body": (
            "Les dépendances site–fournisseur documentent les relations entre "
            "les sites géographiques et leurs fournisseurs, indiquant quel "
            "fournisseur fournit des services à quel site."
        ),
    },
    {
        "key": "assets.site_asset_dependency_list",
        "title": "Dépendances site–actif",
        "body": (
            "Les dépendances site–actif documentent quels biens supports sont "
            "hébergés ou exploités sur chaque site géographique. Elles permettent "
            "d'évaluer l'impact des menaces physiques et environnementales sur "
            "le système d'information."
        ),
    },
    # ── Compliance — pages détail ───────────────────────────────────
    {
        "key": "compliance.framework_detail",
        "title": "Détail du référentiel",
        "body": (
            "Cette page présente le référentiel sélectionné avec sa structure "
            "hiérarchique complète de sections et d'exigences. Les onglets "
            "permettent d'accéder à l'arborescence des exigences, aux "
            "évaluations liées, à l'applicabilité par périmètre et à "
            "l'historique des modifications."
        ),
    },
    {
        "key": "compliance.requirement_detail",
        "title": "Détail de l'exigence",
        "body": (
            "Cette page présente l'exigence sélectionnée avec sa section, "
            "son niveau d'applicabilité et sa description. Les onglets "
            "affichent les résultats d'évaluation, les mappings "
            "inter-référentiels et les plans d'action associés."
        ),
    },
    {
        "key": "compliance.assessment_detail",
        "title": "Détail de l'évaluation",
        "body": (
            "Cette page présente l'évaluation de conformité sélectionnée avec "
            "son périmètre, son référentiel, son score global de conformité "
            "et les résultats par exigence. Vous pouvez consulter les écarts "
            "et lancer des plans d'action directement depuis cette vue."
        ),
    },
    {
        "key": "compliance.mapping_detail",
        "title": "Détail du mapping",
        "body": (
            "Cette page présente le mapping inter-référentiel sélectionné avec "
            "ses exigences source et cible, le type de correspondance et la "
            "justification."
        ),
    },
    {
        "key": "compliance.action_plan_detail",
        "title": "Détail du plan d'action",
        "body": (
            "Cette page présente le plan d'action sélectionné avec son "
            "évaluation et exigence associées, son responsable, sa priorité, "
            "ses dates cibles et son avancement. L'onglet historique retrace "
            "tous les changements de statut."
        ),
    },
    # ── Accounts — pages détail ─────────────────────────────────────
    {
        "key": "accounts.user_detail",
        "title": "Détail de l'utilisateur",
        "body": (
            "Cette page présente le profil de l'utilisateur sélectionné, ses "
            "appartenances aux groupes, ses permissions effectives et son "
            "journal d'accès récent. Les administrateurs peuvent modifier le "
            "compte ou gérer les affectations de groupes depuis cette vue."
        ),
    },
    {
        "key": "accounts.group_detail",
        "title": "Détail du groupe",
        "body": (
            "Cette page présente le groupe de permissions sélectionné avec "
            "les permissions assignées et les utilisateurs membres. Les groupes "
            "système sont en lecture seule ; les groupes personnalisés peuvent "
            "être modifiés pour ajuster les permissions."
        ),
    },
    # ── Risks — pages détail ────────────────────────────────────────
    {
        "key": "risks.risk_detail",
        "title": "Détail du risque",
        "body": (
            "Cette page présente le risque sélectionné avec sa source, ses "
            "conséquences, son évaluation de vraisemblance et d'impact à trois "
            "niveaux (brut, courant, résiduel). Les onglets montrent les actifs "
            "affectés, les décisions de traitement et la piste d'audit complète."
        ),
    },
    {
        "key": "risks.assessment_detail",
        "title": "Détail de l'appréciation des risques",
        "body": (
            "Cette page présente l'appréciation des risques sélectionnée avec "
            "son périmètre, sa méthodologie, sa matrice de risque et la liste "
            "des risques évalués. La section workflow montre la progression "
            "de l'appréciation à travers ses étapes."
        ),
    },
    {
        "key": "risks.criteria_detail",
        "title": "Détail des critères de risque",
        "body": (
            "Cette page présente le jeu de critères de risque sélectionné avec "
            "son échelle de vraisemblance, son échelle d'impact, sa matrice de "
            "risque et ses seuils d'acceptabilité. Ces critères garantissent la "
            "cohérence des appréciations des risques."
        ),
    },
    {
        "key": "risks.treatment_plan_detail",
        "title": "Détail du plan de traitement",
        "body": (
            "Cette page présente le plan de traitement sélectionné avec sa "
            "stratégie (réduire, transférer, éviter, accepter), les risques "
            "associés, le responsable, les dates cibles et l'avancement de "
            "la mise en œuvre."
        ),
    },
    {
        "key": "risks.acceptance_detail",
        "title": "Détail de l'acceptation de risque",
        "body": (
            "Cette page présente l'acceptation de risque sélectionnée avec sa "
            "justification, sa période de validité, son signataire et le niveau "
            "de risque résiduel accepté. Les acceptations expirées sont signalées "
            "automatiquement."
        ),
    },
    {
        "key": "risks.threat_detail",
        "title": "Détail de la menace",
        "body": (
            "Cette page présente la menace sélectionnée avec sa classification "
            "(type et origine), sa description et la liste des scénarios de "
            "risque dans lesquels elle apparaît."
        ),
    },
    {
        "key": "risks.vulnerability_detail",
        "title": "Détail de la vulnérabilité",
        "body": (
            "Cette page présente la vulnérabilité sélectionnée avec sa sévérité, "
            "sa facilité d'exploitation, les actifs affectés et les scénarios de "
            "risque associés. L'onglet historique fournit une piste d'audit "
            "complète."
        ),
    },
    {
        "key": "risks.iso27005_risk_detail",
        "title": "Détail de l'analyse ISO 27005",
        "body": (
            "Cette page présente le scénario de risque ISO 27005 sélectionné, "
            "montrant le croisement entre biens supports, menaces et "
            "vulnérabilités, avec le niveau de risque résultant et les mesures "
            "de traitement proposées."
        ),
    },
    # ── Core ────────────────────────────────────────────────────────
    {
        "key": "core.versioning_config_list",
        "title": "Configuration du versionnement et de l'approbation",
        "body": (
            "Cette page permet de configurer le comportement de versionnement "
            "et d'approbation pour chaque type d'objet. Vous pouvez définir "
            "quels champs déclenchent un incrément de version et une "
            "réinitialisation de l'approbation (champs majeurs), et activer ou "
            "désactiver le workflow d'approbation par type d'objet."
        ),
    },
    # ── Fix: assets.dashboard FR title ──────────────────────────────
    {
        "key": "assets.dashboard",
        "title": "Gestion des actifs",
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
]


def populate_help_content(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for item in HELP_CONTENT_EN:
        HelpContent.objects.update_or_create(
            key=item["key"],
            language="en",
            defaults={"title": item["title"], "body": item["body"]},
        )
    for item in HELP_CONTENT_FR:
        HelpContent.objects.update_or_create(
            key=item["key"],
            language="fr",
            defaults={"title": item["title"], "body": item["body"]},
        )


def reverse(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    en_keys = [item["key"] for item in HELP_CONTENT_EN]
    fr_keys = [item["key"] for item in HELP_CONTENT_FR]
    HelpContent.objects.filter(key__in=en_keys, language="en").delete()
    # Only delete FR entries that are NEW (not the assets.dashboard fix)
    new_fr_keys = [k for k in fr_keys if k != "assets.dashboard"]
    HelpContent.objects.filter(key__in=new_fr_keys, language="fr").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0006_natural_sort_key_function"),
    ]

    operations = [
        migrations.RunPython(populate_help_content, reverse),
    ]
