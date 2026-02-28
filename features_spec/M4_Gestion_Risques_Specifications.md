# Module 4 — Gestion des Risques

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 27 février 2026
**Statut :** Draft

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **Gestion des Risques** permet de conduire l'appréciation et le traitement des risques liés à la sécurité de l'information selon deux méthodologies complémentaires :

- **ISO 27005:2022** — Approche systématique d'appréciation des risques basée sur l'identification des menaces, vulnérabilités et conséquences sur les actifs, avec évaluation quantitative ou qualitative de la vraisemblance et de l'impact.
- **EBIOS RM** (Expression des Besoins et Identification des Objectifs de Sécurité — Risk Manager) — Approche structurée en 5 ateliers, orientée vers l'identification des sources de risque, la construction de scénarios stratégiques et opérationnels, et le traitement itératif des risques.

Le module est conçu avec un **socle commun** (critères de risque, registre, traitement) et deux **sous-modules méthodologiques** qui partagent les entités transversales. Une appréciation des risques peut être conduite selon l'une ou l'autre méthodologie, et les résultats convergent vers un registre de risques unifié.

### 1.2 Périmètre fonctionnel

Le module se décompose en trois parties :

**A. Socle commun :**
1. Contexte de l'appréciation des risques (périmètre, critères, échelles)
2. Registre des risques (vue consolidée)
3. Traitement des risques (plans, options, suivi)
4. Cartographie et reporting

**B. Sous-module ISO 27005 :**
1. Identification des risques (menaces, vulnérabilités, conséquences)
2. Analyse des risques (vraisemblance, impact, niveau de risque)
3. Évaluation des risques (comparaison aux critères d'acceptation)

**C. Sous-module EBIOS RM :**
1. Atelier 1 — Socle de sécurité (cadrage, périmètre métier et technique, écarts)
2. Atelier 2 — Sources de risque (SR, objectifs visés OV, couples SR/OV)
3. Atelier 3 — Scénarios stratégiques (parties prenantes, chemins d'attaque, scénarios)
4. Atelier 4 — Scénarios opérationnels (modes opératoires, scénarios techniques)
5. Atelier 5 — Traitement du risque (stratégie, PACS, risques résiduels)

### 1.3 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Contexte et Organisation | Le périmètre (Scope), les enjeux et les parties intéressées alimentent le contexte d'appréciation des risques. Les activités métier sont les objets de l'atelier 1 EBIOS RM. |
| Gestion des actifs | Les biens essentiels portent les besoins de sécurité (DIC) et définissent les valeurs métier impactées. Les biens supports sont les cibles des vulnérabilités et des scénarios opérationnels. |
| Conformité | Les non-conformités peuvent générer des risques. Les exigences de conformité peuvent être liées à des risques identifiés. |
| Mesures | Les mesures de sécurité réduisent le niveau de risque. Le traitement des risques génère des mesures nouvelles ou renforcées. |
| Fournisseurs | Les fournisseurs constituent des parties prenantes de l'écosystème (Atelier 3 EBIOS RM) et peuvent être des vecteurs de risque. |
| Audits | Les constats d'audit peuvent révéler des risques ou valider l'efficacité des traitements. |
| Incidents | Les incidents alimentent la réévaluation des risques et valident (ou invalident) les scénarios identifiés. |

---

## 2. Modèle de données — Socle commun

### 2.1 Entité : RiskAssessment (Appréciation des risques)

Représente une campagne d'appréciation des risques, conduite selon l'une ou l'autre méthodologie. C'est l'entité racine qui regroupe tous les éléments d'analyse.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. RA-2026-001) |
| `name` | string | requis, max 255 | Intitulé de l'appréciation |
| `description` | text | optionnel | Description et contexte |
| `methodology` | enum | requis | `iso27005`, `ebios_rm` |
| `assessment_date` | date | requis | Date de réalisation |
| `assessor_id` | relation | FK → User, requis | Responsable de l'appréciation |
| `team_members` | relation | M2M → User | Membres de l'équipe d'appréciation |
| `risk_criteria_id` | relation | FK → RiskCriteria, requis | Critères de risque appliqués |
| `status` | enum | requis | `draft`, `in_progress`, `completed`, `validated`, `archived` |
| `validated_by` | relation | FK → User, optionnel | Validateur |
| `validated_at` | datetime | optionnel | Date de validation |
| `next_review_date` | date | optionnel | Prochaine date de revue |
| `summary` | text | optionnel | Synthèse des résultats |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.2 Entité : RiskCriteria (Critères de risque)

Définit les échelles, la matrice et les seuils d'acceptation utilisés pour une appréciation des risques. Réutilisable entre plusieurs appréciations.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Nom du jeu de critères (ex. « Critères 2026 ») |
| `description` | text | optionnel | Description |
| `likelihood_scale` | relation | O2M → ScaleLevel | Échelle de vraisemblance |
| `impact_scale` | relation | O2M → ScaleLevel | Échelle d'impact |
| `risk_matrix` | json | requis | Matrice de risque (likelihood × impact → risk level) |
| `risk_levels` | relation | O2M → RiskLevel | Niveaux de risque résultants |
| `acceptance_threshold` | integer | requis | Seuil d'acceptation (niveau de risque au-delà duquel le traitement est obligatoire) |
| `is_default` | boolean | requis, défaut false | Critères par défaut pour les nouvelles appréciations |
| `status` | enum | requis | `draft`, `active`, `archived` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.3 Sous-entité : ScaleLevel (Niveau d'échelle)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `criteria_id` | relation | FK → RiskCriteria, requis | Critères parent |
| `scale_type` | enum | requis | `likelihood`, `impact` |
| `level` | integer | requis | Valeur numérique (ex. 1, 2, 3, 4) |
| `name` | string | requis, max 100 | Libellé (ex. « Rare », « Probable », « Quasi certain ») |
| `description` | text | optionnel | Description détaillée et exemples |
| `color` | string | optionnel, format hex | Couleur d'affichage |

### 2.4 Sous-entité : RiskLevel (Niveau de risque)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `criteria_id` | relation | FK → RiskCriteria, requis | Critères parent |
| `level` | integer | requis | Valeur numérique (ex. 1, 2, 3, 4) |
| `name` | string | requis, max 100 | Libellé (ex. « Faible », « Modéré », « Élevé », « Critique ») |
| `description` | text | optionnel | Description et actions attendues |
| `color` | string | requis, format hex | Couleur d'affichage |
| `requires_treatment` | boolean | requis | Traitement obligatoire à ce niveau |

### 2.5 Entité : Risk (Risque)

Représente un risque identifié, quelle que soit la méthodologie d'origine. C'est l'entité centrale du registre des risques.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation source |
| `reference` | string | requis, unique | Code de référence (ex. RSK-001) |
| `name` | string | requis, max 255 | Intitulé du risque |
| `description` | text | requis | Description narrative du scénario de risque |
| `risk_source` | enum | requis | `iso27005_analysis`, `ebios_strategic_scenario`, `ebios_operational_scenario`, `incident`, `audit`, `compliance`, `manual` |
| `source_entity_id` | UUID | optionnel | Identifiant de l'entité source (ISO27005Risk, StrategicScenario, etc.) |
| `source_entity_type` | string | optionnel | Type de l'entité source |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Biens essentiels impactés |
| `affected_support_assets` | relation | M2M → SupportAsset | Biens supports concernés |
| `impact_confidentiality` | boolean | requis, défaut false | Impact sur la confidentialité |
| `impact_integrity` | boolean | requis, défaut false | Impact sur l'intégrité |
| `impact_availability` | boolean | requis, défaut false | Impact sur la disponibilité |
| `initial_likelihood` | integer | requis | Vraisemblance initiale (brute) — valeur sur l'échelle |
| `initial_impact` | integer | requis | Impact initial (brut) — valeur sur l'échelle |
| `initial_risk_level` | integer | calculé | Niveau de risque initial (via la matrice) |
| `current_likelihood` | integer | optionnel | Vraisemblance actuelle (après mesures existantes) |
| `current_impact` | integer | optionnel | Impact actuel |
| `current_risk_level` | integer | calculé | Niveau de risque actuel |
| `residual_likelihood` | integer | optionnel | Vraisemblance résiduelle (après traitement planifié) |
| `residual_impact` | integer | optionnel | Impact résiduel |
| `residual_risk_level` | integer | calculé | Niveau de risque résiduel |
| `treatment_decision` | enum | optionnel | `accept`, `mitigate`, `transfer`, `avoid`, `not_decided` |
| `treatment_justification` | text | optionnel | Justification de la décision de traitement |
| `risk_owner_id` | relation | FK → User, requis | Propriétaire du risque (décideur) |
| `linked_measures` | relation | M2M → Measure | Mesures existantes couvrant ce risque |
| `linked_requirements` | relation | M2M → Requirement | Exigences de conformité associées |
| `linked_incidents` | relation | M2M → Incident | Incidents liés |
| `priority` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `identified`, `analyzed`, `evaluated`, `treatment_planned`, `treatment_in_progress`, `treated`, `accepted`, `closed`, `monitoring` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.6 Entité : RiskTreatmentPlan (Plan de traitement du risque)

Représente les actions de traitement associées à un risque.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `risk_id` | relation | FK → Risk, requis | Risque traité |
| `reference` | string | requis, unique | Code de référence (ex. PTR-001) |
| `name` | string | requis, max 255 | Intitulé du plan |
| `description` | text | optionnel | Description détaillée |
| `treatment_type` | enum | requis | `mitigate`, `transfer`, `avoid` |
| `actions` | relation | O2M → TreatmentAction | Actions de traitement |
| `expected_residual_likelihood` | integer | optionnel | Vraisemblance résiduelle attendue |
| `expected_residual_impact` | integer | optionnel | Impact résiduel attendu |
| `cost_estimate` | decimal | optionnel | Estimation du coût global |
| `owner_id` | relation | FK → User, requis | Responsable du plan |
| `start_date` | date | optionnel | Date de début |
| `target_date` | date | requis | Date cible d'achèvement |
| `completion_date` | date | optionnel | Date d'achèvement effective |
| `progress_percentage` | integer | optionnel, 0-100 | Avancement global |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.7 Sous-entité : TreatmentAction (Action de traitement)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `treatment_plan_id` | relation | FK → RiskTreatmentPlan, requis | Plan de traitement parent |
| `description` | text | requis | Description de l'action |
| `owner_id` | relation | FK → User, requis | Responsable de l'action |
| `target_date` | date | requis | Date cible |
| `completion_date` | date | optionnel | Date d'achèvement |
| `linked_measures` | relation | M2M → Measure | Mesures associées (Module Mesures) |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled` |
| `order` | integer | requis | Ordre d'exécution |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.8 Entité : RiskAcceptance (Acceptation de risque)

Formalise l'acceptation d'un risque par le propriétaire du risque, conformément au processus décisionnel de l'organisme.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `risk_id` | relation | FK → Risk, requis | Risque accepté |
| `accepted_by` | relation | FK → User, requis | Acceptant (propriétaire du risque) |
| `accepted_at` | datetime | requis | Date d'acceptation |
| `risk_level_at_acceptance` | integer | requis | Niveau de risque au moment de l'acceptation |
| `justification` | text | requis | Justification de l'acceptation |
| `conditions` | text | optionnel | Conditions d'acceptation (ex. revue trimestrielle) |
| `valid_until` | date | optionnel | Date de validité de l'acceptation |
| `review_date` | date | requis | Date de revue obligatoire |
| `status` | enum | requis | `active`, `expired`, `revoked`, `renewed` |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

---

## 3. Modèle de données — Sous-module ISO 27005

### 3.1 Entité : Threat (Menace)

Représente une menace pouvant exploiter des vulnérabilités et causer des dommages aux actifs.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. MEN-001) |
| `name` | string | requis, max 255 | Nom de la menace |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `deliberate`, `accidental`, `environmental`, `other` |
| `origin` | enum | requis | `human_internal`, `human_external`, `natural`, `technical`, `other` |
| `category` | enum | requis | Voir liste ci-dessous |
| `typical_likelihood` | integer | optionnel | Vraisemblance typique (estimation générique) |
| `is_from_catalog` | boolean | requis, défaut false | Issue du catalogue de menaces prédéfini |
| `status` | enum | requis | `active`, `inactive` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de menaces (valeurs de `category`) :**

`malware`, `social_engineering`, `unauthorized_access`, `denial_of_service`, `data_breach`, `physical_attack`, `supply_chain_attack`, `insider_threat`, `natural_disaster`, `power_failure`, `hardware_failure`, `software_failure`, `network_failure`, `human_error`, `data_loss`, `eavesdropping`, `tampering`, `fraud`, `theft`, `sabotage`, `espionage`, `other`

> Note : Les catégories doivent être paramétrables. Un catalogue de menaces prédéfini (basé sur ISO 27005 Annexe A et ENISA Threat Landscape) est fourni à l'installation.

### 3.2 Entité : Vulnerability (Vulnérabilité)

Représente une faiblesse d'un actif ou d'un groupe d'actifs pouvant être exploitée par une menace.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. VUL-001) |
| `name` | string | requis, max 255 | Nom de la vulnérabilité |
| `description` | text | optionnel | Description détaillée |
| `category` | enum | requis | Voir liste ci-dessous |
| `severity` | enum | requis | `low`, `medium`, `high`, `critical` |
| `affected_asset_types` | json | optionnel | Types de biens supports concernés |
| `affected_assets` | relation | M2M → SupportAsset | Biens supports spécifiques affectés |
| `cve_references` | json | optionnel | Références CVE associées |
| `remediation_guidance` | text | optionnel | Recommandations de remédiation |
| `is_from_catalog` | boolean | requis, défaut false | Issue du catalogue de vulnérabilités prédéfini |
| `status` | enum | requis | `identified`, `confirmed`, `mitigated`, `accepted`, `closed` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de vulnérabilités (valeurs de `category`) :**

`configuration_weakness`, `missing_patch`, `design_flaw`, `insecure_protocol`, `weak_authentication`, `missing_encryption`, `insufficient_logging`, `physical_exposure`, `lack_of_awareness`, `insufficient_redundancy`, `inadequate_procedure`, `third_party_dependency`, `obsolescence`, `other`

> Note : Les catégories doivent être paramétrables. Un catalogue de vulnérabilités prédéfini est fourni à l'installation.

### 3.3 Entité : ISO27005Risk (Analyse de risque ISO 27005)

Représente l'analyse détaillée d'un scénario de risque selon la méthodologie ISO 27005 : un triplet (menace, vulnérabilité, actif) avec évaluation de la vraisemblance et de l'impact.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente (methodology = iso27005) |
| `threat_id` | relation | FK → Threat, requis | Menace exploitante |
| `vulnerability_id` | relation | FK → Vulnerability, requis | Vulnérabilité exploitée |
| `affected_essential_assets` | relation | M2M → EssentialAsset | Biens essentiels impactés |
| `affected_support_assets` | relation | M2M → SupportAsset | Biens supports ciblés |
| `threat_likelihood` | integer | requis | Vraisemblance de la menace (sur l'échelle) |
| `vulnerability_exposure` | integer | requis | Niveau d'exposition de la vulnérabilité (sur l'échelle) |
| `combined_likelihood` | integer | calculé | Vraisemblance combinée |
| `impact_confidentiality` | integer | optionnel | Impact sur la confidentialité (sur l'échelle) |
| `impact_integrity` | integer | optionnel | Impact sur l'intégrité |
| `impact_availability` | integer | optionnel | Impact sur la disponibilité |
| `max_impact` | integer | calculé | Impact maximum retenu |
| `risk_level` | integer | calculé | Niveau de risque (via matrice) |
| `existing_controls` | text | optionnel | Mesures existantes prises en compte |
| `existing_measures` | relation | M2M → Measure | Mesures existantes formalisées |
| `risk_id` | relation | FK → Risk, optionnel | Risque consolidé dans le registre |
| `description` | text | optionnel | Description narrative du scénario |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

---

## 4. Modèle de données — Sous-module EBIOS RM

### 4.1 Atelier 1 — Socle de sécurité

L'atelier 1 s'appuie principalement sur les données des Modules 1 (Contexte) et 2 (Actifs). Il ajoute une couche d'analyse spécifique.

#### 4.1.1 Entité : SecurityBaseline (Cadrage du socle de sécurité)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente (methodology = ebios_rm) |
| `business_scope_summary` | text | requis | Synthèse du périmètre métier (recueil depuis Module 1) |
| `technical_scope_summary` | text | requis | Synthèse du périmètre technique (recueil depuis Module 2) |
| `feared_events` | relation | O2M → FearedEvent | Événements redoutés identifiés |
| `baseline_gaps` | relation | O2M → BaselineGap | Écarts au socle de sécurité |
| `status` | enum | requis | `draft`, `in_progress`, `completed` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.1.2 Sous-entité : FearedEvent (Événement redouté)

Représente un événement redouté sur un bien essentiel, caractérisé par l'atteinte au critère DIC et son niveau de gravité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `baseline_id` | relation | FK → SecurityBaseline, requis | Socle parent |
| `essential_asset_id` | relation | FK → EssentialAsset, requis | Bien essentiel concerné |
| `name` | string | requis, max 255 | Intitulé de l'événement redouté |
| `description` | text | requis | Description de l'événement |
| `dic_criteria` | enum | requis | `confidentiality`, `integrity`, `availability` |
| `gravity_level` | integer | requis | Niveau de gravité (sur l'échelle d'impact) |
| `gravity_justification` | text | optionnel | Justification du niveau de gravité |
| `impacts` | text | optionnel | Impacts détaillés (financier, juridique, image, etc.) |
| `order` | integer | requis | Ordre d'affichage |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.1.3 Sous-entité : BaselineGap (Écart au socle de sécurité)

Représente un écart constaté entre l'état actuel de sécurité et le socle de sécurité attendu (référentiels, bonnes pratiques).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `baseline_id` | relation | FK → SecurityBaseline, requis | Socle parent |
| `reference_source` | string | requis | Source du socle (ex. « ISO 27002 — A.8.1 », « Guide ANSSI ») |
| `linked_requirement_id` | relation | FK → Requirement, optionnel | Exigence de conformité liée (Module Conformité) |
| `description` | text | requis | Description de l'écart |
| `affected_assets` | relation | M2M → SupportAsset | Biens supports concernés |
| `severity` | enum | requis | `low`, `medium`, `high`, `critical` |
| `remediation` | text | optionnel | Remédiation proposée |
| `status` | enum | requis | `identified`, `accepted`, `in_remediation`, `remediated` |
| `order` | integer | requis | Ordre d'affichage |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 4.2 Atelier 2 — Sources de risque

#### 4.2.1 Entité : RiskSource (Source de risque)

Représente une source de risque, c'est-à-dire un élément (personne, groupe, organisation, état, phénomène) susceptible d'être à l'origine de scénarios de risque.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente |
| `reference` | string | requis, unique | Code de référence (ex. SR-001) |
| `name` | string | requis, max 255 | Nom de la source de risque |
| `description` | text | optionnel | Description détaillée |
| `category` | enum | requis | `state`, `organized_crime`, `terrorist`, `activist`, `competitor`, `employee`, `supplier`, `amateur`, `natural`, `other` |
| `motivation` | text | optionnel | Motivations de la source de risque |
| `resources_level` | enum | requis | `limited`, `moderate`, `significant`, `unlimited` |
| `activity_level` | enum | optionnel | `low`, `medium`, `high`, `very_high` |
| `is_retained` | boolean | requis, défaut true | Retenu pour la suite de l'analyse |
| `retention_justification` | text | optionnel | Justification de la rétention ou de l'exclusion |
| `objectives` | relation | O2M → TargetedObjective | Objectifs visés |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.2.2 Sous-entité : TargetedObjective (Objectif visé — OV)

Représente un objectif visé par une source de risque, c'est-à-dire ce que la source de risque cherche à obtenir ou à provoquer.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `risk_source_id` | relation | FK → RiskSource, requis | Source de risque parente |
| `name` | string | requis, max 255 | Intitulé de l'objectif visé |
| `description` | text | optionnel | Description détaillée |
| `targeted_essential_assets` | relation | M2M → EssentialAsset | Biens essentiels ciblés |
| `targeted_feared_events` | relation | M2M → FearedEvent | Événements redoutés associés |
| `relevance_level` | enum | requis | `low`, `medium`, `high`, `critical` |
| `is_retained` | boolean | requis, défaut true | Retenu pour la suite |
| `order` | integer | requis | Ordre d'affichage |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.2.3 Entité : RiskSourceObjectivePair (Couple SR/OV)

Représente la combinaison formelle d'une source de risque et d'un objectif visé, évaluée en pertinence.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente |
| `risk_source_id` | relation | FK → RiskSource, requis | Source de risque |
| `targeted_objective_id` | relation | FK → TargetedObjective, requis | Objectif visé |
| `relevance` | enum | requis | `low`, `medium`, `high`, `critical` |
| `justification` | text | optionnel | Justification de la pertinence |
| `is_retained` | boolean | requis, défaut true | Retenu pour l'atelier 3 |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`risk_source_id`, `targeted_objective_id`) doit être unique par assessment.

### 4.3 Atelier 3 — Scénarios stratégiques

#### 4.3.1 Entité : EcosystemStakeholder (Partie prenante de l'écosystème)

Représente une partie prenante de l'écosystème pouvant constituer un vecteur d'attaque. Distinct des parties intéressées du Module 1 (focus sur le rôle technique et la surface d'exposition).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente |
| `stakeholder_id` | relation | FK → Stakeholder, optionnel | Lien vers la partie intéressée (Module 1) si existante |
| `name` | string | requis, max 255 | Nom de la partie prenante |
| `description` | text | optionnel | Description du rôle dans l'écosystème |
| `category` | enum | requis | `supplier`, `partner`, `subcontractor`, `customer`, `regulator`, `shared_infrastructure`, `other` |
| `dependency_level` | enum | requis | `low`, `medium`, `high`, `critical` |
| `trust_level` | enum | requis | `untrusted`, `limited_trust`, `trusted`, `highly_trusted` |
| `exposure_level` | enum | requis | `low`, `medium`, `high`, `critical` |
| `maturity_level` | enum | optionnel | `low`, `medium`, `high` |
| `access_to_assets` | relation | M2M → SupportAsset | Biens supports accessibles |
| `penetration_difficulty` | enum | optionnel | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `is_attack_vector` | boolean | requis, défaut false | Identifié comme vecteur d'attaque potentiel |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.3.2 Entité : StrategicScenario (Scénario stratégique)

Représente un scénario stratégique : un chemin d'attaque de haut niveau depuis une source de risque vers un objectif visé, en passant par les parties prenantes de l'écosystème.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente |
| `reference` | string | requis, unique | Code de référence (ex. SS-001) |
| `name` | string | requis, max 255 | Intitulé du scénario |
| `description` | text | requis | Description narrative du scénario |
| `sr_ov_pair_id` | relation | FK → RiskSourceObjectivePair, requis | Couple SR/OV source |
| `attack_path` | relation | O2M → AttackPathStep | Étapes du chemin d'attaque |
| `targeted_feared_events` | relation | M2M → FearedEvent | Événements redoutés visés |
| `gravity_level` | integer | requis | Niveau de gravité (sur l'échelle d'impact) |
| `likelihood_level` | integer | requis | Vraisemblance stratégique |
| `risk_level` | integer | calculé | Niveau de risque (via matrice) |
| `existing_security_measures` | text | optionnel | Mesures de sécurité existantes |
| `is_retained` | boolean | requis, défaut true | Retenu pour l'atelier 4 |
| `risk_id` | relation | FK → Risk, optionnel | Risque consolidé dans le registre |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.3.3 Sous-entité : AttackPathStep (Étape du chemin d'attaque)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scenario_id` | relation | FK → StrategicScenario, requis | Scénario stratégique parent |
| `order` | integer | requis | Ordre de l'étape dans le chemin |
| `stakeholder_id` | relation | FK → EcosystemStakeholder, optionnel | Partie prenante impliquée |
| `description` | text | requis | Description de l'étape |
| `action_type` | enum | requis | `initial_access`, `lateral_movement`, `privilege_escalation`, `data_exfiltration`, `disruption`, `manipulation`, `other` |
| `difficulty` | enum | optionnel | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 4.4 Atelier 4 — Scénarios opérationnels

#### 4.4.1 Entité : OperationalScenario (Scénario opérationnel)

Représente un scénario opérationnel : la déclinaison technique d'un scénario stratégique décrivant les modes opératoires sur les biens supports.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente |
| `strategic_scenario_id` | relation | FK → StrategicScenario, requis | Scénario stratégique parent |
| `reference` | string | requis, unique | Code de référence (ex. SO-001) |
| `name` | string | requis, max 255 | Intitulé du scénario |
| `description` | text | requis | Description narrative technique |
| `targeted_support_assets` | relation | M2M → SupportAsset | Biens supports ciblés |
| `attack_techniques` | relation | O2M → AttackTechnique | Techniques d'attaque utilisées |
| `likelihood_level` | integer | requis | Vraisemblance opérationnelle |
| `gravity_level` | integer | calculé ou saisi | Gravité (héritée du scénario stratégique ou ajustée) |
| `risk_level` | integer | calculé | Niveau de risque (via matrice) |
| `existing_controls` | text | optionnel | Mesures existantes prises en compte |
| `existing_measures` | relation | M2M → Measure | Mesures existantes formalisées |
| `risk_id` | relation | FK → Risk, optionnel | Risque consolidé dans le registre |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

#### 4.4.2 Sous-entité : AttackTechnique (Technique d'attaque)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scenario_id` | relation | FK → OperationalScenario, requis | Scénario opérationnel parent |
| `order` | integer | requis | Ordre dans la séquence d'attaque |
| `name` | string | requis, max 255 | Nom de la technique |
| `description` | text | optionnel | Description de la technique |
| `mitre_attack_id` | string | optionnel | Référence MITRE ATT&CK (ex. T1566.001) |
| `mitre_attack_tactic` | string | optionnel | Tactique MITRE ATT&CK (ex. « Initial Access ») |
| `targeted_asset_id` | relation | FK → SupportAsset, optionnel | Bien support ciblé par cette technique |
| `difficulty` | enum | optionnel | `trivial`, `easy`, `moderate`, `difficult`, `very_difficult` |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 4.5 Atelier 5 — Traitement du risque (EBIOS RM)

L'atelier 5 s'appuie sur les entités communes du socle (§2.5 à §2.8 : Risk, RiskTreatmentPlan, TreatmentAction, RiskAcceptance). Il ajoute une structure de synthèse.

#### 4.5.1 Entité : EbiosSummary (Synthèse EBIOS RM)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → RiskAssessment, requis | Appréciation parente |
| `residual_risk_strategy` | text | requis | Stratégie globale de traitement du risque résiduel |
| `monitoring_plan` | text | optionnel | Plan de suivi et d'amélioration continue |
| `security_action_plan` | text | optionnel | Synthèse du PACS (Plan d'Amélioration Continue de la Sécurité) |
| `risk_mapping_before` | json | optionnel | Snapshot de la cartographie des risques avant traitement |
| `risk_mapping_after` | json | optionnel | Snapshot de la cartographie des risques après traitement |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

---

## 5. Règles de gestion

### 5.1 Règles générales

| ID | Règle |
|---|---|
| RG-01 | Toute appréciation des risques doit être rattachée à un **Scope** et utiliser un jeu de **RiskCriteria**. |
| RG-02 | La suppression d'un risque référencé par le module Mesures, Incidents ou Conformité est interdite. La désactivation via `status = closed` est utilisée à la place. |
| RG-03 | Toute modification d'un objet génère une entrée dans le **journal d'audit**. |
| RG-04 | Les niveaux de risque (initial, actuel, résiduel) sont **calculés automatiquement** via la matrice définie dans les `RiskCriteria` associés. |
| RG-05 | Les codes de référence suivent un format paramétrable avec incrémentation automatique. |

### 5.2 Règles du socle commun

| ID | Règle |
|---|---|
| RS-01 | Le **niveau de risque** est déterminé par croisement vraisemblance × impact dans la `risk_matrix` des `RiskCriteria`. |
| RS-02 | Un risque avec `current_risk_level` ≥ `acceptance_threshold` et `treatment_decision = not_decided` déclenche une **alerte** de traitement requis. |
| RS-03 | Un risque avec `treatment_decision = accept` doit posséder un enregistrement `RiskAcceptance` valide. Le système émet une alerte si l'acceptation est expirée (`valid_until` dépassé). |
| RS-04 | Un `RiskTreatmentPlan` avec `target_date` dépassée et `status ≠ completed` ou `cancelled` passe automatiquement en `status = overdue`. |
| RS-05 | La complétion d'un `RiskTreatmentPlan` déclenche une **suggestion de réévaluation** du risque associé (recalcul du niveau résiduel). |
| RS-06 | La validation d'une `RiskAssessment` verrouille ses données en modification. Toute modification ultérieure nécessite de créer une nouvelle version ou de repasser le statut en `in_progress`. |

### 5.3 Règles ISO 27005

| ID | Règle |
|---|---|
| RI-01 | Un `ISO27005Risk` est rattaché à une appréciation de `methodology = iso27005`. |
| RI-02 | La `combined_likelihood` est calculée comme `MAX(threat_likelihood, vulnerability_exposure)` par défaut. Ce mode de calcul est paramétrable (MAX, MOYENNE, ou formule personnalisée). |
| RI-03 | Le `max_impact` est calculé comme `MAX(impact_confidentiality, impact_integrity, impact_availability)`. Les impacts non renseignés sont exclus du calcul. |
| RI-04 | À la création d'un `ISO27005Risk`, un `Risk` correspondant est automatiquement proposé à l'utilisateur pour consolidation dans le registre. L'utilisateur peut fusionner avec un risque existant ou créer un nouveau. |

### 5.4 Règles EBIOS RM

| ID | Règle |
|---|---|
| RE-01 | Les entités EBIOS RM sont rattachées à une appréciation de `methodology = ebios_rm`. |
| RE-02 | Un `FearedEvent` est associé à un seul critère DIC (`confidentiality`, `integrity` ou `availability`). Pour un même bien essentiel, il peut exister jusqu'à 3 événements redoutés (un par critère). |
| RE-03 | Seuls les couples SR/OV marqués `is_retained = true` sont utilisables dans les scénarios stratégiques (atelier 3). |
| RE-04 | Seuls les scénarios stratégiques marqués `is_retained = true` sont déclinables en scénarios opérationnels (atelier 4). |
| RE-05 | Chaque `StrategicScenario` et `OperationalScenario` peut être consolidé en `Risk` dans le registre commun via le champ `risk_id`. |
| RE-06 | Le `gravity_level` d'un scénario opérationnel est par défaut hérité du scénario stratégique parent. L'utilisateur peut l'ajuster avec justification. |
| RE-07 | Les étapes du chemin d'attaque (`AttackPathStep`) doivent respecter un ordre logique (`order` croissant). |
| RE-08 | Les techniques d'attaque (`AttackTechnique`) peuvent référencer le framework **MITRE ATT&CK**. Le système propose une autocomplétion basée sur un catalogue intégré. |

---

## 6. Spécifications API REST

### 6.1 Conventions générales

Identiques aux modules précédents. Base URL : `/api/v1/risks/`

### 6.2 Endpoints — Socle commun

#### Risk Assessments (Appréciations)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments` | Lister toutes les appréciations |
| `POST` | `/assessments` | Créer une appréciation |
| `GET` | `/assessments/{id}` | Détail d'une appréciation |
| `PUT` | `/assessments/{id}` | Mise à jour complète |
| `PATCH` | `/assessments/{id}` | Mise à jour partielle |
| `DELETE` | `/assessments/{id}` | Supprimer (si en draft) |
| `POST` | `/assessments/{id}/validate` | Valider l'appréciation |
| `POST` | `/assessments/{id}/duplicate` | Dupliquer pour nouvelle itération |
| `GET` | `/assessments/{id}/export` | Export (PDF, DOCX, JSON) |
| `GET` | `/assessments/{id}/summary` | Synthèse (KPIs) |

#### Risk Criteria (Critères)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/criteria` | Lister les jeux de critères |
| `POST` | `/criteria` | Créer un jeu de critères |
| `GET` | `/criteria/{id}` | Détail d'un jeu de critères |
| `PUT` | `/criteria/{id}` | Mise à jour complète |
| `PATCH` | `/criteria/{id}` | Mise à jour partielle |
| `DELETE` | `/criteria/{id}` | Supprimer (si non utilisé) |
| `GET` | `/criteria/{id}/matrix-preview` | Aperçu visuel de la matrice |

#### Risk Register (Registre des risques)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/risks` | Lister tous les risques (registre, filtrable) |
| `POST` | `/risks` | Créer un risque manuellement |
| `GET` | `/risks/{id}` | Détail d'un risque |
| `PUT` | `/risks/{id}` | Mise à jour complète |
| `PATCH` | `/risks/{id}` | Mise à jour partielle |
| `DELETE` | `/risks/{id}` | Supprimer (si non référencé) |
| `GET` | `/risks/{id}/treatment-plans` | Lister les plans de traitement |
| `GET` | `/risks/{id}/acceptances` | Lister les acceptations |
| `GET` | `/risks/{id}/history` | Historique des évaluations |
| `GET` | `/risks/matrix` | Cartographie des risques (données pour matrice) |
| `GET` | `/risks/dashboard` | Tableau de bord (KPIs) |

**Paramètres de filtrage :**

- `?assessment_id={uuid}`
- `?methodology=iso27005|ebios_rm`
- `?risk_source=iso27005_analysis|ebios_strategic_scenario|manual`
- `?treatment_decision=accept|mitigate|transfer|avoid|not_decided`
- `?status=identified|analyzed|treatment_in_progress|accepted`
- `?initial_risk_level_min=3`
- `?current_risk_level_min=2`
- `?risk_owner_id={uuid}`
- `?affected_essential_asset_id={uuid}`
- `?priority=high,critical`
- `?search=terme`

#### Treatment Plans (Plans de traitement)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/treatment-plans` | Lister tous les plans de traitement |
| `POST` | `/treatment-plans` | Créer un plan de traitement |
| `GET` | `/treatment-plans/{id}` | Détail d'un plan |
| `PUT` | `/treatment-plans/{id}` | Mise à jour |
| `PATCH` | `/treatment-plans/{id}` | Mise à jour partielle |
| `DELETE` | `/treatment-plans/{id}` | Supprimer |
| `POST` | `/treatment-plans/{id}/actions` | Ajouter une action |
| `PUT` | `/treatment-plans/{id}/actions/{action_id}` | Modifier une action |
| `DELETE` | `/treatment-plans/{id}/actions/{action_id}` | Supprimer une action |
| `GET` | `/treatment-plans/overdue` | Plans en retard |

#### Risk Acceptances (Acceptations)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/acceptances` | Lister toutes les acceptations |
| `POST` | `/acceptances` | Créer une acceptation |
| `GET` | `/acceptances/{id}` | Détail d'une acceptation |
| `PATCH` | `/acceptances/{id}` | Mise à jour (renouvellement, révocation) |
| `GET` | `/acceptances/expiring` | Acceptations arrivant à expiration |

### 6.3 Endpoints — ISO 27005

#### Threats (Menaces)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/threats` | Lister les menaces |
| `POST` | `/iso27005/threats` | Créer une menace |
| `GET` | `/iso27005/threats/{id}` | Détail d'une menace |
| `PUT` | `/iso27005/threats/{id}` | Mise à jour |
| `DELETE` | `/iso27005/threats/{id}` | Supprimer |
| `GET` | `/iso27005/threats/catalog` | Catalogue de menaces prédéfini |
| `POST` | `/iso27005/threats/import-catalog` | Importer depuis le catalogue |

#### Vulnerabilities (Vulnérabilités)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/vulnerabilities` | Lister les vulnérabilités |
| `POST` | `/iso27005/vulnerabilities` | Créer une vulnérabilité |
| `GET` | `/iso27005/vulnerabilities/{id}` | Détail |
| `PUT` | `/iso27005/vulnerabilities/{id}` | Mise à jour |
| `DELETE` | `/iso27005/vulnerabilities/{id}` | Supprimer |
| `GET` | `/iso27005/vulnerabilities/catalog` | Catalogue prédéfini |

#### ISO 27005 Risk Analysis

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/iso27005/analyses` | Lister les analyses de risque ISO 27005 |
| `POST` | `/iso27005/analyses` | Créer une analyse |
| `GET` | `/iso27005/analyses/{id}` | Détail d'une analyse |
| `PUT` | `/iso27005/analyses/{id}` | Mise à jour |
| `DELETE` | `/iso27005/analyses/{id}` | Supprimer |
| `POST` | `/iso27005/analyses/{id}/consolidate` | Consolider en risque du registre |
| `GET` | `/assessments/{id}/iso27005/summary` | Synthèse ISO 27005 d'une appréciation |

### 6.4 Endpoints — EBIOS RM

#### Atelier 1 — Socle de sécurité

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/ebios/assessments/{id}/baseline` | Consulter le socle de sécurité |
| `POST` | `/ebios/assessments/{id}/baseline` | Créer/initialiser le socle |
| `PUT` | `/ebios/assessments/{id}/baseline` | Mise à jour |
| `GET` | `/ebios/baselines/{id}/feared-events` | Lister les événements redoutés |
| `POST` | `/ebios/baselines/{id}/feared-events` | Créer un événement redouté |
| `PUT` | `/ebios/feared-events/{id}` | Modifier un événement redouté |
| `DELETE` | `/ebios/feared-events/{id}` | Supprimer |
| `GET` | `/ebios/baselines/{id}/gaps` | Lister les écarts au socle |
| `POST` | `/ebios/baselines/{id}/gaps` | Créer un écart |
| `PUT` | `/ebios/gaps/{id}` | Modifier un écart |
| `DELETE` | `/ebios/gaps/{id}` | Supprimer |

#### Atelier 2 — Sources de risque

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/ebios/assessments/{id}/risk-sources` | Lister les sources de risque |
| `POST` | `/ebios/assessments/{id}/risk-sources` | Créer une source de risque |
| `GET` | `/ebios/risk-sources/{id}` | Détail |
| `PUT` | `/ebios/risk-sources/{id}` | Mise à jour |
| `DELETE` | `/ebios/risk-sources/{id}` | Supprimer |
| `POST` | `/ebios/risk-sources/{id}/objectives` | Ajouter un objectif visé |
| `PUT` | `/ebios/objectives/{id}` | Modifier un objectif visé |
| `DELETE` | `/ebios/objectives/{id}` | Supprimer |
| `GET` | `/ebios/assessments/{id}/sr-ov-pairs` | Lister les couples SR/OV |
| `POST` | `/ebios/assessments/{id}/sr-ov-pairs` | Créer un couple SR/OV |
| `PUT` | `/ebios/sr-ov-pairs/{id}` | Modifier |
| `DELETE` | `/ebios/sr-ov-pairs/{id}` | Supprimer |

#### Atelier 3 — Scénarios stratégiques

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/ebios/assessments/{id}/ecosystem` | Lister les parties prenantes écosystème |
| `POST` | `/ebios/assessments/{id}/ecosystem` | Créer une partie prenante |
| `GET` | `/ebios/ecosystem/{id}` | Détail |
| `PUT` | `/ebios/ecosystem/{id}` | Mise à jour |
| `DELETE` | `/ebios/ecosystem/{id}` | Supprimer |
| `GET` | `/ebios/assessments/{id}/ecosystem/graph` | Graphe de l'écosystème |
| `GET` | `/ebios/assessments/{id}/strategic-scenarios` | Lister les scénarios stratégiques |
| `POST` | `/ebios/assessments/{id}/strategic-scenarios` | Créer un scénario |
| `GET` | `/ebios/strategic-scenarios/{id}` | Détail |
| `PUT` | `/ebios/strategic-scenarios/{id}` | Mise à jour |
| `DELETE` | `/ebios/strategic-scenarios/{id}` | Supprimer |
| `POST` | `/ebios/strategic-scenarios/{id}/attack-path` | Ajouter une étape |
| `PUT` | `/ebios/attack-path-steps/{id}` | Modifier une étape |
| `DELETE` | `/ebios/attack-path-steps/{id}` | Supprimer |
| `PATCH` | `/ebios/strategic-scenarios/{id}/attack-path/reorder` | Réordonner les étapes |
| `POST` | `/ebios/strategic-scenarios/{id}/consolidate` | Consolider en risque du registre |

#### Atelier 4 — Scénarios opérationnels

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/ebios/assessments/{id}/operational-scenarios` | Lister les scénarios opérationnels |
| `POST` | `/ebios/assessments/{id}/operational-scenarios` | Créer un scénario |
| `GET` | `/ebios/operational-scenarios/{id}` | Détail |
| `PUT` | `/ebios/operational-scenarios/{id}` | Mise à jour |
| `DELETE` | `/ebios/operational-scenarios/{id}` | Supprimer |
| `POST` | `/ebios/operational-scenarios/{id}/techniques` | Ajouter une technique d'attaque |
| `PUT` | `/ebios/attack-techniques/{id}` | Modifier |
| `DELETE` | `/ebios/attack-techniques/{id}` | Supprimer |
| `GET` | `/ebios/mitre-attack/catalog` | Catalogue MITRE ATT&CK (autocomplétion) |
| `POST` | `/ebios/operational-scenarios/{id}/consolidate` | Consolider en risque du registre |

#### Atelier 5 — Synthèse EBIOS RM

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/ebios/assessments/{id}/summary` | Consulter la synthèse |
| `POST` | `/ebios/assessments/{id}/summary` | Créer/initialiser la synthèse |
| `PUT` | `/ebios/summaries/{id}` | Mise à jour |
| `GET` | `/ebios/assessments/{id}/risk-mapping` | Cartographie avant/après traitement |

### 6.5 Endpoints transversaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/risks/dashboard` | Tableau de bord global du module |
| `GET` | `/risks/export` | Export global (PDF, DOCX, JSON) |
| `GET` | `/risks/audit-trail` | Journal d'audit du module |
| `GET` | `/risks/config/enums` | Lister les listes de valeurs |
| `PUT` | `/risks/config/enums/{enum_name}` | Modifier une liste de valeurs |
| `GET` | `/risks/statistics` | Statistiques globales |
| `GET` | `/risks/alerts` | Alertes actives |

---

## 7. Spécifications d'interface utilisateur

### 7.1 Navigation

Le module est accessible via un élément de navigation principal « Gestion des Risques » se décomposant en :

- **Appréciations** (liste des campagnes)
- **Registre des risques** (vue consolidée)
- **ISO 27005** (sous-menu : Menaces, Vulnérabilités, Analyses)
- **EBIOS RM** (sous-menu : Atelier 1 à 5)
- **Traitements** (plans de traitement, acceptations)
- **Cartographie** (matrices de risque)
- **Tableau de bord**

### 7.2 Vue « Appréciations »

- **Liste :** Tableau avec colonnes (Référence, Nom, Méthodologie, Date, Responsable, Nombre de risques, Statut). Badge de méthodologie (ISO 27005 / EBIOS RM).
- **Création :** Assistant en étapes : choix de la méthodologie → sélection du périmètre → sélection des critères de risque → informations générales.
- **Détail :** Vue de synthèse avec accès aux sous-modules et progression de l'analyse.

### 7.3 Vue « Critères de risque »

- **Éditeur d'échelles :** Interface de configuration des niveaux de vraisemblance et d'impact (ajout, modification, suppression de niveaux avec libellé, description et couleur).
- **Éditeur de matrice :** Grille interactive vraisemblance (lignes) × impact (colonnes) où chaque cellule est assignée à un niveau de risque par sélection. Aperçu visuel coloré en temps réel.
- **Niveaux de risque :** Configuration des niveaux résultants avec seuil d'acceptation.

### 7.4 Vue « Registre des risques »

- **Liste :** Tableau avec colonnes (Référence, Nom, Source, Biens impactés, C/I/D, Vraisemblance, Impact, Niveau initial, Niveau actuel, Niveau résiduel, Traitement, Propriétaire, Statut). Code couleur par niveau de risque. Filtres avancés.
- **Matrice de risques :** Vue matricielle vraisemblance × impact positionnant chaque risque sous forme de bulle (taille proportionnelle au nombre de biens impactés). Bascule entre risque initial / actuel / résiduel.
- **Vue comparée :** Superposition des positions initiales et résiduelles pour visualiser l'effet du traitement.
- **Détail / Édition :** Formulaire avec onglets (Identification, Analyse, Traitement, Acceptation, Historique, Relations).

### 7.5 Vues ISO 27005

#### 7.5.1 Menaces et vulnérabilités

- **Listes :** Tableaux filtrables avec accès au catalogue prédéfini.
- **Catalogue :** Bibliothèque de menaces et vulnérabilités avec sélection et import.

#### 7.5.2 Analyse de risque

- **Vue de travail :** Interface de création des triplets (menace × vulnérabilité × actif) avec évaluation de la vraisemblance et de l'impact. Mode formulaire ou mode tableau en ligne.
- **Matrice croisée :** Vue menaces × vulnérabilités avec les actifs concernés et les niveaux de risque.
- **Consolidation :** Bouton de consolidation vers le registre avec option de fusion.

### 7.6 Vues EBIOS RM

L'interface EBIOS RM est organisée en **5 ateliers** accessibles séquentiellement (avec navigation libre). Un indicateur de progression affiche l'état d'avancement de chaque atelier.

#### 7.6.1 Atelier 1 — Socle de sécurité

- **Périmètre métier :** Affichage récapitulatif des activités, biens essentiels et valorisations DIC (lecture depuis les Modules 1 et 2).
- **Périmètre technique :** Affichage récapitulatif des biens supports et cartographie des dépendances (lecture depuis le Module 2).
- **Événements redoutés :** Tableau avec colonnes (Bien essentiel, Critère DIC, Description, Gravité). Formulaire d'ajout avec sélection du bien essentiel et évaluation de la gravité.
- **Écarts au socle :** Tableau des écarts identifiés par rapport aux référentiels et bonnes pratiques. Lien vers les exigences du Module Conformité.

#### 7.6.2 Atelier 2 — Sources de risque

- **Sources de risque :** Tableau avec colonnes (Référence, Nom, Catégorie, Ressources, Retenu). Formulaire d'ajout.
- **Objectifs visés :** Sous-liste par source de risque, avec lien vers les biens essentiels ciblés et les événements redoutés.
- **Couples SR/OV :** Matrice croisée Sources de risque × Objectifs visés avec niveau de pertinence dans chaque cellule. Cellules cliquables pour saisir la justification. Case à cocher pour retenir/exclure.

#### 7.6.3 Atelier 3 — Scénarios stratégiques

- **Écosystème :** Cartographie interactive des parties prenantes sous forme de graphe (nœuds = parties prenantes, arêtes = relations). Code couleur par niveau d'exposition et de confiance. Possibilité de marquer les vecteurs d'attaque.
- **Scénarios stratégiques :** Liste des scénarios avec éditeur de chemin d'attaque en mode visuel (étapes chaînées avec parties prenantes). Évaluation gravité/vraisemblance. Consolidation vers le registre.

#### 7.6.4 Atelier 4 — Scénarios opérationnels

- **Scénarios opérationnels :** Liste groupée par scénario stratégique parent. Éditeur de séquence d'attaque avec techniques (autocomplétion MITRE ATT&CK). Lien vers les biens supports ciblés. Évaluation vraisemblance/gravité.
- **Vue MITRE ATT&CK :** Mapping des techniques utilisées sur la matrice MITRE ATT&CK (vue heatmap).

#### 7.6.5 Atelier 5 — Traitement

- **Cartographie avant/après :** Deux matrices de risques côte à côte (avant et après traitement).
- **Plans de traitement :** Interface commune avec le socle (§7.4).
- **PACS :** Synthèse du Plan d'Amélioration Continue de la Sécurité.

### 7.7 Tableau de bord du module

- Nombre total de risques par niveau (initial, actuel, résiduel)
- Répartition par décision de traitement (camembert)
- Évolution des niveaux de risque dans le temps (courbes de tendance)
- Cartographie matricielle des risques (miniature interactive)
- Top 10 des risques les plus critiques
- Plans de traitement en retard
- Acceptations de risques arrivant à expiration
- Biens essentiels les plus exposés (nombre de risques associés)
- Couverture des risques par les mesures existantes
- Alertes et actions requises

---

## 8. Permissions et contrôle d'accès

### 8.1 Modèle RBAC

| Permission | Description |
|---|---|
| `risks.assessment.read` | Consulter les appréciations |
| `risks.assessment.write` | Créer/modifier les appréciations |
| `risks.assessment.validate` | Valider une appréciation |
| `risks.assessment.delete` | Supprimer les appréciations |
| `risks.criteria.read` | Consulter les critères de risque |
| `risks.criteria.write` | Créer/modifier les critères |
| `risks.criteria.delete` | Supprimer les critères |
| `risks.risk.read` | Consulter le registre des risques |
| `risks.risk.write` | Créer/modifier les risques |
| `risks.risk.delete` | Supprimer les risques |
| `risks.treatment.read` | Consulter les plans de traitement |
| `risks.treatment.write` | Créer/modifier les plans de traitement |
| `risks.treatment.delete` | Supprimer les plans de traitement |
| `risks.acceptance.read` | Consulter les acceptations |
| `risks.acceptance.write` | Créer/modifier les acceptations (réservé aux propriétaires de risque) |
| `risks.iso27005.read` | Consulter les données ISO 27005 (menaces, vulnérabilités, analyses) |
| `risks.iso27005.write` | Créer/modifier les données ISO 27005 |
| `risks.iso27005.delete` | Supprimer les données ISO 27005 |
| `risks.ebios.read` | Consulter les données EBIOS RM (ateliers 1-5) |
| `risks.ebios.write` | Créer/modifier les données EBIOS RM |
| `risks.ebios.delete` | Supprimer les données EBIOS RM |
| `risks.export` | Exporter les données du module |
| `risks.config.manage` | Gérer les catalogues et listes de valeurs |
| `risks.audit_trail.read` | Consulter le journal d'audit |

### 8.2 Rôles applicatifs suggérés

| Rôle | Permissions |
|---|---|
| **Administrateur** | Toutes les permissions |
| **RSSI / DPO** | Toutes sauf `*.delete` et `config.manage` |
| **Analyste risque** | `*.read` + `*.write` + `risks.iso27005.*` + `risks.ebios.*` (hors validate et config) |
| **Propriétaire de risque** | `risks.risk.read` + `risks.treatment.read` + `risks.acceptance.write` (restreint à ses risques) |
| **Auditeur** | `*.read` + `risks.export` + `risks.audit_trail.read` |
| **Lecteur** | `*.read` uniquement |

---

## 9. Journalisation et traçabilité

### 9.1 Audit Trail

Actions spécifiques à ce module :

| Action | Description |
|---|---|
| `create` | Création d'une entité du module |
| `update` | Modification |
| `delete` | Suppression |
| `validate_assessment` | Validation d'une appréciation |
| `consolidate_risk` | Consolidation d'une analyse/scénario en risque du registre |
| `accept_risk` | Acceptation formelle d'un risque |
| `revoke_acceptance` | Révocation d'une acceptation |
| `complete_treatment` | Clôture d'un plan de traitement |
| `evaluate_risk` | Évaluation/réévaluation d'un risque |

### 9.2 Rétention

Identique aux modules précédents. Durée paramétrable, défaut 7 ans.

---

## 10. Export et reporting

### 10.1 Formats d'export

| Format | Contenu |
|---|---|
| **JSON** | Export brut structuré |
| **PDF** | Rapport formaté avec matrices, cartographies, détail des risques |
| **DOCX** | Document éditable |
| **CSV** | Export tabulaire (registre, menaces, vulnérabilités, scénarios) |

### 10.2 Rapports prédéfinis

| Rapport | Description |
|---|---|
| Registre des risques | Liste complète avec niveaux initial/actuel/résiduel et traitements |
| Cartographie des risques | Matrice vraisemblance × impact (avant et après traitement) |
| Rapport d'appréciation ISO 27005 | Synthèse complète d'une appréciation ISO 27005 |
| Rapport d'appréciation EBIOS RM | Synthèse complète des 5 ateliers EBIOS RM |
| Plan de traitement des risques | Liste des plans de traitement avec avancement |
| Rapport d'acceptation des risques | Risques acceptés avec justification et dates de revue |
| Rapport de tendance | Évolution des niveaux de risque dans le temps |
| PACS (EBIOS RM) | Plan d'Amélioration Continue de la Sécurité |
| Matrice MITRE ATT&CK | Mapping des techniques d'attaque identifiées |

---

## 11. Notifications et alertes

| Événement | Destinataires | Canal |
|---|---|---|
| Risque de niveau critique identifié | RSSI, Propriétaire du risque | In-app, email |
| Traitement requis (risque au-dessus du seuil, non traité) | Propriétaire du risque | In-app, email |
| Plan de traitement en retard | Responsable du plan, RSSI | In-app, email |
| Acceptation de risque arrivant à expiration (30 jours avant) | Propriétaire du risque, RSSI | In-app, email |
| Acceptation de risque expirée | Propriétaire du risque, RSSI | In-app, email |
| Appréciation en attente de validation | Validateur | In-app, email |
| Date de revue d'un risque atteinte | Propriétaire du risque | In-app, email |
| Nouveau risque consolidé dans le registre | RSSI | In-app |
| Plan de traitement complété — suggestion de réévaluation | Propriétaire du risque | In-app |
| Réévaluation périodique requise (fréquence paramétrable) | Responsable de l'appréciation | In-app, email |

---

## 12. Considérations techniques

### 12.1 Calcul automatique des niveaux de risque

Le calcul du niveau de risque est effectué côté serveur à partir de la matrice définie dans les `RiskCriteria` :

```
risk_level = risk_matrix[likelihood][impact]
```

La matrice est stockée au format JSON :

```json
{
  "matrix": [
    [1, 1, 2, 3],
    [1, 2, 3, 4],
    [2, 3, 3, 4],
    [3, 3, 4, 4]
  ]
}
```

Où `matrix[likelihood_index][impact_index]` retourne le `risk_level`.

Le recalcul est déclenché à chaque modification de vraisemblance ou d'impact, et à la modification des critères de risque (recalcul de tous les risques associés).

### 12.2 Consolidation des risques

Le mécanisme de consolidation permet de créer un `Risk` dans le registre commun à partir d'un `ISO27005Risk`, `StrategicScenario` ou `OperationalScenario` :

1. L'utilisateur initie la consolidation depuis l'entité source
2. Le système propose de créer un nouveau risque ou de fusionner avec un risque existant (recherche par similarité)
3. Les données sont pré-remplies à partir de l'entité source
4. L'utilisateur valide et ajuste
5. Le lien bidirectionnel est maintenu (`source_entity_id` / `risk_id`)

### 12.3 Catalogue MITRE ATT&CK

Un catalogue MITRE ATT&CK est intégré et mis à jour périodiquement. Il fournit :

- La liste des tactiques et techniques avec descriptions
- L'autocomplétion lors de la saisie des techniques d'attaque
- La visualisation en heatmap des techniques identifiées dans les scénarios

### 12.4 Catalogues de menaces et vulnérabilités

Des catalogues prédéfinis sont fournis à l'installation :

- **Menaces** : basé sur ISO 27005 Annexe A et ENISA Threat Landscape
- **Vulnérabilités** : basé sur ISO 27005 Annexe D et CWE (Common Weakness Enumeration)

Ces catalogues sont importables en un clic et personnalisables ensuite.

### 12.5 Multi-tenant

Identique aux modules précédents. Les catalogues prédéfinis sont globaux (partagés entre tenants) ; les éléments ajoutés par les utilisateurs sont isolés par tenant.

### 12.6 Internationalisation (i18n)

Identique aux modules précédents. Les catalogues prédéfinis sont fournis en français et en anglais.

### 12.7 Performances

- Les listes paginées ne doivent pas dépasser **200 ms** pour 1 000 enregistrements.
- Le calcul de la matrice de risques pour 500 risques doit s'exécuter en moins de **1 seconde**.
- Le graphe de l'écosystème (Atelier 3) doit se charger en moins de **2 secondes** pour 50 nœuds.
- La heatmap MITRE ATT&CK doit se charger en moins de **1 seconde**.
- Les tableaux de bord agrégés sont mis en cache avec un TTL de **5 minutes**.
- Les exports volumineux sont traités de manière asynchrone.

### 12.8 Webhooks

Événements spécifiques :

- `risks.assessment.created`, `validated`
- `risks.risk.created`, `updated`, `consolidated`
- `risks.risk.level_changed` (changement de niveau de risque)
- `risks.treatment_plan.created`, `completed`, `overdue`
- `risks.acceptance.created`, `expired`, `revoked`
- `risks.ebios.scenario_created` (stratégique ou opérationnel)

---

## 13. Critères d'acceptation

### 13.1 Socle commun

- [ ] CRUD complet sur les appréciations, critères, risques, plans de traitement et acceptations
- [ ] La matrice de risques est configurable (échelles, niveaux, couleurs)
- [ ] Les niveaux de risque (initial, actuel, résiduel) sont calculés automatiquement via la matrice
- [ ] Le registre des risques est consultable avec tous les filtres
- [ ] La cartographie matricielle des risques est interactive (bascule initial/actuel/résiduel)
- [ ] Les plans de traitement supportent le suivi d'avancement et la détection de retard
- [ ] L'acceptation formelle des risques est fonctionnelle avec gestion d'expiration
- [ ] Le tableau de bord affiche les données correctes avec tendances

### 13.2 ISO 27005

- [ ] Les catalogues de menaces et vulnérabilités sont importables
- [ ] L'analyse de risque par triplet (menace × vulnérabilité × actif) est fonctionnelle
- [ ] Le calcul combiné de vraisemblance est correct
- [ ] La consolidation vers le registre fonctionne (création et fusion)
- [ ] Le rapport d'appréciation ISO 27005 est générable

### 13.3 EBIOS RM

- [ ] Les 5 ateliers sont accessibles et séquencés
- [ ] Atelier 1 : les événements redoutés et écarts au socle sont gérables
- [ ] Atelier 2 : les sources de risque, objectifs visés et couples SR/OV sont gérables, la matrice croisée est fonctionnelle
- [ ] Atelier 3 : le graphe de l'écosystème est interactif, les scénarios stratégiques et chemins d'attaque sont éditables
- [ ] Atelier 4 : les scénarios opérationnels et techniques d'attaque sont éditables, l'autocomplétion MITRE ATT&CK fonctionne
- [ ] Atelier 5 : la cartographie avant/après est fonctionnelle, le PACS est générable
- [ ] La consolidation des scénarios vers le registre fonctionne
- [ ] Le rapport d'appréciation EBIOS RM complet est générable

### 13.4 API

- [ ] Tous les endpoints documentés sont implémentés et fonctionnels
- [ ] La documentation OpenAPI (Swagger) est générée automatiquement
- [ ] Les codes d'erreur et structures de réponse sont conformes
- [ ] Les webhooks sont déclenchés pour chaque événement de mutation

### 13.5 Sécurité

- [ ] Le contrôle d'accès RBAC est appliqué sur chaque endpoint et vue
- [ ] La restriction « propriétaire de risque » limite bien l'acceptation aux risques dont l'utilisateur est propriétaire
- [ ] Le journal d'audit enregistre toutes les opérations
- [ ] Les données sont isolées entre tenants

### 13.6 Performance

- [ ] Les temps de réponse respectent les seuils définis (§12.7)
- [ ] Les exports volumineux sont traités de manière asynchrone

---

*Fin des spécifications du Module 4 — Gestion des Risques*
