# Module 3 — Conformité

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 27 février 2026
**Statut :** Draft

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **Conformité** permet de gérer l'ensemble des référentiels normatifs, légaux et contractuels applicables à l'organisme, d'en décliner les exigences, d'évaluer le niveau de conformité et de suivre les écarts. Il offre également la possibilité de mapper les exigences entre référentiels afin de mutualiser les efforts de mise en conformité.

Ce module s'inscrit dans les exigences de l'ISO 27001 (chapitres 4.2, A.5.31 à A.5.36 notamment), du RGPD, et de toute autre réglementation sectorielle applicable (NIS 2, DORA, HDS, PCI DSS, etc.).

### 1.2 Périmètre fonctionnel

Le module couvre cinq sous-domaines :

1. Référentiels (normes, lois, règlements, contrats, politiques internes)
2. Exigences par référentiel (décomposition structurée des exigences)
3. Évaluations de conformité (mesure du niveau de conformité par exigence)
4. Mapping inter-référentiels (correspondances entre exigences de différents référentiels)
5. Plans d'action de mise en conformité

### 1.3 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Contexte et Organisation | Les parties intéressées expriment des attentes pouvant être liées à des exigences de conformité. Le périmètre (Scope) cadre les référentiels applicables. |
| Gestion des actifs | Certaines exigences portent sur des catégories d'actifs (données personnelles, infrastructures critiques). |
| Gestion des risques | Les non-conformités peuvent générer des risques. Les résultats d'appréciation des risques peuvent justifier l'applicabilité d'une exigence. |
| Mesures | Les mesures de sécurité sont les réponses opérationnelles aux exigences de conformité. Une exigence peut être couverte par une ou plusieurs mesures. |
| Fournisseurs | Les exigences contractuelles ou réglementaires peuvent s'appliquer aux fournisseurs. |
| Audits | Les audits évaluent la conformité aux référentiels. Les constats d'audit sont liés aux exigences. |
| Incidents | Certains incidents révèlent des non-conformités à tracer. |
| Formations | Certaines exigences imposent des obligations de formation. |

---

## 2. Modèle de données

### 2.1 Entité : Framework (Référentiel)

Représente un référentiel normatif, légal, réglementaire, contractuel ou interne auquel l'organisme doit ou choisit de se conformer.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. REF-001) |
| `name` | string | requis, max 255 | Nom du référentiel (ex. « ISO 27001:2022 ») |
| `short_name` | string | optionnel, max 50 | Abréviation (ex. « ISO 27001 ») |
| `description` | text | optionnel | Description du référentiel |
| `type` | enum | requis | `standard`, `law`, `regulation`, `contract`, `internal_policy`, `industry_framework`, `other` |
| `category` | enum | requis | Voir liste ci-dessous |
| `version` | string | optionnel | Version du référentiel (ex. « 2022 ») |
| `publication_date` | date | optionnel | Date de publication officielle |
| `effective_date` | date | optionnel | Date d'entrée en vigueur |
| `expiry_date` | date | optionnel | Date d'expiration ou d'abrogation |
| `issuing_body` | string | optionnel | Organisme émetteur (ex. « ISO », « Parlement européen ») |
| `jurisdiction` | string | optionnel | Juridiction applicable (ex. « France », « Union européenne », « International ») |
| `url` | string | optionnel, format URL | Lien vers le texte officiel |
| `is_mandatory` | boolean | requis, défaut false | Référentiel obligatoire (contrainte légale/réglementaire) |
| `is_applicable` | boolean | requis, défaut true | Applicable au périmètre |
| `applicability_justification` | text | optionnel | Justification de l'applicabilité ou de la non-applicabilité |
| `owner_id` | relation | FK → User, requis | Responsable du suivi de conformité pour ce référentiel |
| `related_stakeholders` | relation | M2M → Stakeholder | Parties intéressées à l'origine de ce référentiel |
| `compliance_level` | decimal | calculé, 0-100 | Niveau de conformité global calculé (%) |
| `last_assessment_date` | date | calculé | Date de la dernière évaluation |
| `status` | enum | requis | `draft`, `active`, `under_review`, `deprecated`, `archived` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de référentiels (valeurs de `category`) :**

- `information_security` (Sécurité de l'information — ISO 27001, ISO 27002, etc.)
- `privacy` (Protection des données — RGPD, CCPA, etc.)
- `risk_management` (Gestion des risques — ISO 27005, ISO 31000, etc.)
- `business_continuity` (Continuité d'activité — ISO 22301, etc.)
- `cloud_security` (Sécurité cloud — ISO 27017, ISO 27018, SecNumCloud, etc.)
- `sector_specific` (Réglementations sectorielles — NIS 2, DORA, HDS, PCI DSS, etc.)
- `it_governance` (Gouvernance IT — COBIT, ITIL, etc.)
- `quality` (Qualité — ISO 9001, etc.)
- `contractual` (Exigences contractuelles)
- `internal` (Politiques et procédures internes)
- `other`

> Note : Les catégories et les types doivent être paramétrables par l'administrateur.

### 2.2 Entité : Section (Section / Chapitre du référentiel)

Représente la structure hiérarchique d'un référentiel (chapitres, sections, sous-sections). Permet de reproduire fidèlement le plan du référentiel original.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK → Framework, requis | Référentiel parent |
| `parent_section_id` | relation | FK → Section, optionnel | Section parente (hiérarchie) |
| `reference` | string | requis | Numéro de section (ex. « A.5 », « 4.2.1 ») |
| `name` | string | requis, max 255 | Intitulé de la section |
| `description` | text | optionnel | Description ou texte de la section |
| `order` | integer | requis | Ordre d'affichage au sein du parent |
| `compliance_level` | decimal | calculé, 0-100 | Niveau de conformité agrégé de la section (%) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte : la combinaison (`framework_id`, `reference`) doit être unique.

### 2.3 Entité : Requirement (Exigence)

Représente une exigence individuelle extraite d'un référentiel. C'est l'unité élémentaire d'évaluation de la conformité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK → Framework, requis | Référentiel parent |
| `section_id` | relation | FK → Section, optionnel | Section de rattachement |
| `reference` | string | requis | Numéro de l'exigence (ex. « A.5.1.1 », « Art. 32.1.a ») |
| `name` | string | requis, max 500 | Intitulé court de l'exigence |
| `description` | text | requis | Texte complet de l'exigence |
| `guidance` | text | optionnel | Recommandations de mise en œuvre / notes d'interprétation |
| `type` | enum | requis | `mandatory`, `recommended`, `optional` |
| `category` | enum | optionnel | `organizational`, `technical`, `physical`, `legal`, `human`, `other` |
| `is_applicable` | boolean | requis, défaut true | Applicable au périmètre |
| `applicability_justification` | text | optionnel | Justification de la non-applicabilité (DdA) |
| `compliance_status` | enum | requis | `not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable` |
| `compliance_level` | integer | optionnel, 0-100 | Niveau de conformité (%) |
| `compliance_evidence` | text | optionnel | Preuves / éléments de conformité |
| `compliance_gaps` | text | optionnel | Écarts constatés |
| `last_assessment_date` | date | optionnel | Date de la dernière évaluation |
| `last_assessed_by` | relation | FK → User, optionnel | Dernier évaluateur |
| `owner_id` | relation | FK → User, optionnel | Responsable de la mise en conformité |
| `priority` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `target_date` | date | optionnel | Date cible de mise en conformité |
| `linked_measures` | relation | M2M → Measure | Mesures contribuant à la conformité (Module Mesures) |
| `linked_assets` | relation | M2M → EssentialAsset | Biens essentiels concernés (Module Actifs) |
| `linked_risks` | relation | M2M → Risk | Risques associés (Module Risques) |
| `linked_stakeholder_expectations` | relation | M2M → StakeholderExpectation | Attentes de PI associées (Module Contexte) |
| `mapped_requirements` | relation | M2M → Requirement (via RequirementMapping) | Exigences d'autres référentiels mappées |
| `order` | integer | requis | Ordre d'affichage au sein de la section |
| `status` | enum | requis | `active`, `deprecated`, `superseded` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte : la combinaison (`framework_id`, `reference`) doit être unique.

### 2.4 Entité : ComplianceAssessment (Évaluation de conformité)

Représente une campagne d'évaluation de conformité pour un référentiel donné. Permet de conserver l'historique des évaluations successives.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK → Framework, requis | Référentiel évalué |
| `name` | string | requis, max 255 | Intitulé de l'évaluation (ex. « Évaluation annuelle 2026 ») |
| `description` | text | optionnel | Contexte et objectif de l'évaluation |
| `assessment_date` | date | requis | Date de réalisation |
| `assessor_id` | relation | FK → User, requis | Évaluateur principal |
| `methodology` | text | optionnel | Méthodologie utilisée |
| `overall_compliance_level` | decimal | calculé, 0-100 | Niveau de conformité global (%) |
| `total_requirements` | integer | calculé | Nombre total d'exigences applicables |
| `compliant_count` | integer | calculé | Nombre d'exigences conformes |
| `partially_compliant_count` | integer | calculé | Nombre d'exigences partiellement conformes |
| `non_compliant_count` | integer | calculé | Nombre d'exigences non conformes |
| `not_assessed_count` | integer | calculé | Nombre d'exigences non évaluées |
| `status` | enum | requis | `draft`, `in_progress`, `completed`, `validated`, `archived` |
| `validated_by` | relation | FK → User, optionnel | Validateur |
| `validated_at` | datetime | optionnel | Date de validation |
| `results` | relation | O2M → AssessmentResult | Résultats par exigence |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.5 Sous-entité : AssessmentResult (Résultat d'évaluation par exigence)

Représente le résultat d'évaluation d'une exigence dans le cadre d'une campagne d'évaluation.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `assessment_id` | relation | FK → ComplianceAssessment, requis | Évaluation parente |
| `requirement_id` | relation | FK → Requirement, requis | Exigence évaluée |
| `compliance_status` | enum | requis | `not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable` |
| `compliance_level` | integer | optionnel, 0-100 | Niveau de conformité (%) |
| `evidence` | text | optionnel | Preuves constatées |
| `gaps` | text | optionnel | Écarts identifiés |
| `observations` | text | optionnel | Observations complémentaires |
| `assessed_by` | relation | FK → User, requis | Évaluateur |
| `assessed_at` | datetime | requis | Date et heure de l'évaluation |
| `attachments` | relation | O2M → Attachment | Pièces jointes (preuves documentaires) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`assessment_id`, `requirement_id`) doit être unique.

### 2.6 Entité : RequirementMapping (Mapping inter-référentiels)

Représente une correspondance entre deux exigences de référentiels différents. Permet de mutualiser les efforts de conformité et de visualiser les recouvrements.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `source_requirement_id` | relation | FK → Requirement, requis | Exigence source |
| `target_requirement_id` | relation | FK → Requirement, requis | Exigence cible |
| `mapping_type` | enum | requis | `equivalent`, `partial_overlap`, `includes`, `included_by`, `related` |
| `coverage_level` | enum | optionnel | `full`, `partial`, `minimal` |
| `description` | text | optionnel | Description de la correspondance |
| `justification` | text | optionnel | Justification du mapping |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`source_requirement_id`, `target_requirement_id`) doit être unique.
> Contrainte : `source_requirement_id` et `target_requirement_id` doivent appartenir à des référentiels différents.

**Types de mapping :**

| Type | Description |
|---|---|
| `equivalent` | Les deux exigences sont équivalentes (couverture mutuelle) |
| `partial_overlap` | Les exigences se recouvrent partiellement |
| `includes` | L'exigence source inclut / couvre l'exigence cible |
| `included_by` | L'exigence source est incluse / couverte par l'exigence cible |
| `related` | Les exigences sont liées sans recouvrement direct |

### 2.7 Entité : ComplianceActionPlan (Plan d'action de conformité)

Représente un plan d'action visant à corriger les écarts de conformité constatés lors d'une évaluation.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | requis, unique | Code de référence (ex. PAC-001) |
| `name` | string | requis, max 255 | Intitulé du plan d'action |
| `description` | text | optionnel | Description détaillée |
| `assessment_id` | relation | FK → ComplianceAssessment, optionnel | Évaluation source |
| `requirement_id` | relation | FK → Requirement, optionnel | Exigence concernée |
| `gap_description` | text | requis | Description de l'écart à combler |
| `remediation_plan` | text | requis | Plan de remédiation |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `owner_id` | relation | FK → User, requis | Responsable de l'action |
| `start_date` | date | optionnel | Date de début prévue |
| `target_date` | date | requis | Date cible d'achèvement |
| `completion_date` | date | optionnel | Date d'achèvement effective |
| `progress_percentage` | integer | optionnel, 0-100 | Pourcentage d'avancement |
| `cost_estimate` | decimal | optionnel | Estimation du coût |
| `linked_measures` | relation | M2M → Measure | Mesures à mettre en place (Module Mesures) |
| `status` | enum | requis | `planned`, `in_progress`, `completed`, `cancelled`, `overdue` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.8 Sous-entité : Attachment (Pièce jointe)

Utilisée pour stocker les preuves documentaires associées aux évaluations de conformité.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `entity_type` | string | requis | Type d'entité parente (ex. `AssessmentResult`, `ComplianceActionPlan`) |
| `entity_id` | UUID | requis | Identifiant de l'entité parente |
| `file_name` | string | requis, max 255 | Nom du fichier |
| `file_path` | string | requis | Chemin de stockage |
| `file_size` | integer | requis | Taille en octets |
| `mime_type` | string | requis | Type MIME |
| `description` | text | optionnel | Description de la pièce jointe |
| `uploaded_by` | relation | FK → User, requis | Utilisateur ayant téléversé |
| `created_at` | datetime | auto | Date de création |

---

## 3. Règles de gestion

### 3.1 Règles générales

| ID | Règle |
|---|---|
| RG-01 | Tout référentiel doit être rattaché à un **Scope** (périmètre). |
| RG-02 | La suppression d'un référentiel ou d'une exigence référencé(e) par un autre module (Mesures, Audits, Risques) est interdite. Une désactivation (`status = deprecated` ou `archived`) est utilisée à la place. |
| RG-03 | Toute modification d'un objet génère une entrée dans le **journal d'audit**. |
| RG-04 | Les champs `created_at` et `updated_at` sont gérés automatiquement par le système. |
| RG-05 | Les listes de valeurs paramétrables (catégories, types) sont gérées via la table de configuration dédiée. |
| RG-06 | Les relations M2M sont stockées dans des tables de jointure dédiées. |
| RG-07 | Les codes de référence (`reference`) des plans d'action suivent un format paramétrable avec incrémentation automatique. |

### 3.2 Règles de conformité et d'évaluation

| ID | Règle |
|---|---|
| RC-01 | Le **niveau de conformité global** d'un référentiel est calculé automatiquement comme la moyenne pondérée des niveaux de conformité de ses exigences applicables. Les exigences non applicables sont exclues du calcul. |
| RC-02 | Le niveau de conformité d'une **section** est calculé comme la moyenne des niveaux de conformité de ses exigences (et sous-sections) applicables. |
| RC-03 | Une exigence marquée `is_applicable = false` doit avoir un champ `applicability_justification` renseigné. Le système émet un avertissement dans le cas contraire. |
| RC-04 | Une exigence avec `compliance_status = compliant` doit avoir un `compliance_level` ≥ 80. Le système émet une alerte de cohérence dans le cas contraire. |
| RC-05 | Une exigence avec `compliance_status = non_compliant` et `type = mandatory` et un référentiel `is_mandatory = true` déclenche une **alerte critique** de non-conformité réglementaire. |
| RC-06 | Lors de la validation d'une **ComplianceAssessment**, les résultats (`AssessmentResult`) sont reportés sur les exigences (`Requirement`) correspondantes pour mettre à jour leur `compliance_status` et `compliance_level` courants. |
| RC-07 | L'historique des évaluations est conservé via les entités `ComplianceAssessment` / `AssessmentResult`. Les anciennes évaluations ne sont jamais écrasées. |

### 3.3 Règles de mapping

| ID | Règle |
|---|---|
| RM-01 | Un mapping ne peut exister qu'entre des exigences de **référentiels différents**. |
| RM-02 | Un mapping de type `equivalent` entre une exigence A et une exigence B implique que le mapping inverse existe automatiquement (symétrie). |
| RM-03 | Un mapping de type `includes` entre A → B génère automatiquement un mapping inverse `included_by` entre B → A. |
| RM-04 | Les mappings ne propagent pas automatiquement les niveaux de conformité. La propagation est une **suggestion** présentée à l'utilisateur pour validation manuelle. |
| RM-05 | Le système détecte et signale les **mappings circulaires** (A → B → C → A) comme avertissement. |

### 3.4 Règles des plans d'action

| ID | Règle |
|---|---|
| RP-01 | Un plan d'action avec `target_date` dépassée et `status ≠ completed` ou `cancelled` passe automatiquement en `status = overdue`. |
| RP-02 | Un plan d'action avec `status = completed` doit avoir `progress_percentage = 100` et `completion_date` renseigné. |
| RP-03 | La complétion d'un plan d'action déclenche une **suggestion de réévaluation** de l'exigence concernée. |

---

## 4. Spécifications API REST

### 4.1 Conventions générales

Identiques aux modules précédents. Base URL : `/api/v1/compliance/`

### 4.2 Endpoints — Frameworks (Référentiels)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/frameworks` | Lister tous les référentiels (filtrable) |
| `GET` | `/scopes/{scope_id}/frameworks` | Lister les référentiels d'un périmètre |
| `POST` | `/scopes/{scope_id}/frameworks` | Créer un référentiel |
| `GET` | `/frameworks/{id}` | Détail d'un référentiel |
| `PUT` | `/frameworks/{id}` | Mise à jour complète |
| `PATCH` | `/frameworks/{id}` | Mise à jour partielle |
| `DELETE` | `/frameworks/{id}` | Supprimer (si non référencé) |
| `GET` | `/frameworks/{id}/sections` | Lister les sections du référentiel |
| `GET` | `/frameworks/{id}/requirements` | Lister toutes les exigences du référentiel |
| `GET` | `/frameworks/{id}/compliance-summary` | Synthèse de conformité (par section, par statut) |
| `GET` | `/frameworks/{id}/assessments` | Lister les évaluations du référentiel |
| `GET` | `/frameworks/{id}/export` | Export (PDF, DOCX, JSON, CSV) |
| `GET` | `/frameworks/{id}/soa` | Déclaration d'applicabilité (Statement of Applicability) |
| `GET` | `/frameworks/categories` | Lister les catégories disponibles |
| `POST` | `/frameworks/import` | Import d'un référentiel (JSON, CSV) |

**Paramètres de filtrage spécifiques :**

- `?type=standard|law|regulation|contract|internal_policy`
- `?category=information_security`
- `?is_mandatory=true`
- `?is_applicable=true`
- `?status=active`
- `?owner_id={uuid}`
- `?compliance_level_min=50&compliance_level_max=80`
- `?search=terme`

### 4.3 Endpoints — Sections

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/frameworks/{framework_id}/sections` | Créer une section |
| `GET` | `/sections/{id}` | Détail d'une section |
| `PUT` | `/sections/{id}` | Mise à jour complète |
| `PATCH` | `/sections/{id}` | Mise à jour partielle |
| `DELETE` | `/sections/{id}` | Supprimer (si aucune exigence rattachée) |
| `GET` | `/sections/{id}/children` | Lister les sous-sections |
| `GET` | `/sections/{id}/requirements` | Lister les exigences de la section |
| `GET` | `/frameworks/{framework_id}/sections/tree` | Arborescence complète des sections |
| `PATCH` | `/frameworks/{framework_id}/sections/reorder` | Réordonner les sections |

### 4.4 Endpoints — Requirements (Exigences)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/requirements` | Lister toutes les exigences (tous référentiels, filtrable) |
| `POST` | `/frameworks/{framework_id}/requirements` | Créer une exigence |
| `GET` | `/requirements/{id}` | Détail d'une exigence |
| `PUT` | `/requirements/{id}` | Mise à jour complète |
| `PATCH` | `/requirements/{id}` | Mise à jour partielle |
| `DELETE` | `/requirements/{id}` | Supprimer (si non référencée) |
| `PATCH` | `/requirements/{id}/assess` | Évaluer la conformité d'une exigence (mise à jour rapide) |
| `GET` | `/requirements/{id}/measures` | Lister les mesures liées |
| `GET` | `/requirements/{id}/mappings` | Lister les mappings de cette exigence |
| `GET` | `/requirements/{id}/action-plans` | Lister les plans d'action liés |
| `GET` | `/requirements/{id}/history` | Historique des évaluations de cette exigence |
| `GET` | `/requirements/categories` | Lister les catégories disponibles |

**Paramètres de filtrage spécifiques :**

- `?framework_id={uuid}`
- `?section_id={uuid}`
- `?type=mandatory|recommended|optional`
- `?category=technical`
- `?is_applicable=true|false`
- `?compliance_status=non_compliant,partially_compliant`
- `?compliance_level_min=0&compliance_level_max=50`
- `?owner_id={uuid}`
- `?priority=high,critical`
- `?has_measures=true|false`
- `?has_mappings=true|false`
- `?search=terme`

### 4.5 Endpoints — Compliance Assessments (Évaluations)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/assessments` | Lister toutes les évaluations |
| `POST` | `/frameworks/{framework_id}/assessments` | Créer une évaluation pour un référentiel |
| `GET` | `/assessments/{id}` | Détail d'une évaluation |
| `PUT` | `/assessments/{id}` | Mise à jour complète |
| `PATCH` | `/assessments/{id}` | Mise à jour partielle |
| `DELETE` | `/assessments/{id}` | Supprimer (si en draft uniquement) |
| `POST` | `/assessments/{id}/validate` | Valider l'évaluation (reporte les résultats sur les exigences) |
| `POST` | `/assessments/{id}/results` | Ajouter ou mettre à jour un résultat |
| `GET` | `/assessments/{id}/results` | Lister les résultats |
| `PUT` | `/assessments/{id}/results/{result_id}` | Modifier un résultat |
| `GET` | `/assessments/{id}/summary` | Synthèse de l'évaluation (KPIs) |
| `GET` | `/assessments/{id}/export` | Export (PDF, DOCX, JSON) |
| `GET` | `/assessments/{id}/comparison` | Comparaison avec l'évaluation précédente |

### 4.6 Endpoints — Requirement Mappings (Mappings inter-référentiels)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/mappings` | Lister tous les mappings (filtrable) |
| `POST` | `/mappings` | Créer un mapping |
| `GET` | `/mappings/{id}` | Détail d'un mapping |
| `PUT` | `/mappings/{id}` | Mise à jour complète |
| `PATCH` | `/mappings/{id}` | Mise à jour partielle |
| `DELETE` | `/mappings/{id}` | Supprimer un mapping |
| `GET` | `/mappings/matrix` | Matrice de mapping entre deux référentiels |
| `GET` | `/mappings/coverage` | Analyse de couverture entre référentiels |
| `POST` | `/mappings/import` | Import de mappings en masse (CSV, JSON) |

**Paramètres de filtrage :**

- `?source_framework_id={uuid}`
- `?target_framework_id={uuid}`
- `?mapping_type=equivalent|partial_overlap`
- `?coverage_level=full|partial`

### 4.7 Endpoints — Action Plans (Plans d'action)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/action-plans` | Lister tous les plans d'action |
| `POST` | `/action-plans` | Créer un plan d'action |
| `GET` | `/action-plans/{id}` | Détail d'un plan d'action |
| `PUT` | `/action-plans/{id}` | Mise à jour complète |
| `PATCH` | `/action-plans/{id}` | Mise à jour partielle |
| `DELETE` | `/action-plans/{id}` | Supprimer |
| `GET` | `/action-plans/overdue` | Lister les plans d'action en retard |
| `GET` | `/action-plans/dashboard` | Données de tableau de bord (KPIs agrégés) |

**Paramètres de filtrage :**

- `?requirement_id={uuid}`
- `?assessment_id={uuid}`
- `?framework_id={uuid}`
- `?owner_id={uuid}`
- `?status=in_progress|overdue`
- `?priority=high,critical`

### 4.8 Endpoints transversaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/compliance/dashboard` | Tableau de bord synthétique du module |
| `GET` | `/compliance/export` | Export global (PDF, DOCX, JSON) |
| `GET` | `/compliance/audit-trail` | Journal d'audit du module |
| `GET` | `/compliance/config/enums` | Lister les listes de valeurs paramétrables |
| `PUT` | `/compliance/config/enums/{enum_name}` | Modifier une liste de valeurs |
| `GET` | `/compliance/statistics` | Statistiques globales de conformité |
| `GET` | `/compliance/alerts` | Lister les alertes actives |

---

## 5. Spécifications d'interface utilisateur

### 5.1 Navigation

Le module est accessible via un élément de navigation principal « Conformité » se décomposant en sous-menus : Référentiels, Exigences, Évaluations, Mappings, Plans d'action, Tableau de bord.

### 5.2 Vue « Référentiels » (Frameworks)

- **Liste :** Tableau avec colonnes (Référence, Nom, Type, Catégorie, Obligatoire, Conformité %, Statut, Responsable). Jauge de conformité visuelle pour chaque référentiel. Filtres et tri sur toutes les colonnes.
- **Détail / Édition :** Formulaire avec onglets :
  - *Informations générales :* identification, type, catégorie, organisme émetteur, dates, juridiction.
  - *Applicabilité :* statut d'applicabilité, justification, parties intéressées liées.
  - *Structure :* arborescence des sections et exigences (tree view éditable).
  - *Conformité :* synthèse visuelle (graphiques en barres par section, camembert par statut), niveau global.
  - *Évaluations :* historique des évaluations avec tendance.
  - *Mappings :* référentiels mappés avec couverture.
  - *Historique :* journal des modifications.
- **Actions :** Créer, Modifier, Importer, Exporter, Générer la DdA.

### 5.3 Vue « Exigences » (Requirements)

- **Liste :** Tableau avec colonnes (Référence, Intitulé, Référentiel, Section, Type, Applicable, Statut de conformité, Conformité %, Priorité, Responsable). Code couleur par statut de conformité (rouge/orange/vert/gris). Filtres avancés.
- **Vue par référentiel :** Exigences regroupées par section, affichage hiérarchique fidèle à la structure du référentiel.
- **Détail / Édition :** Formulaire avec onglets :
  - *Informations :* texte de l'exigence, type, catégorie, applicabilité, justification.
  - *Conformité :* statut, niveau, preuves, écarts. Formulaire d'évaluation rapide.
  - *Relations :* mesures liées, biens essentiels, risques, attentes de PI.
  - *Mappings :* exigences mappées dans d'autres référentiels.
  - *Plans d'action :* actions correctives en cours.
  - *Historique :* évolution du statut de conformité dans le temps (graphique de tendance).
- **Actions :** Créer, Modifier, Évaluer, Exporter.

### 5.4 Vue « Évaluations » (Compliance Assessments)

- **Liste :** Tableau avec colonnes (Nom, Référentiel, Date, Évaluateur, Conformité %, Statut).
- **Détail :** Vue de campagne d'évaluation avec :
  - Barre de progression (exigences évaluées / total).
  - Liste des exigences avec formulaire d'évaluation en ligne (statut, niveau, preuves, écarts).
  - Navigation exigence par exigence (mode « assistant ») pour les évaluations systématiques.
  - Synthèse graphique en temps réel pendant l'évaluation.
- **Comparaison :** Vue comparative entre deux évaluations successives montrant l'évolution par exigence (progression/régression).
- **Actions :** Créer, Évaluer, Valider, Exporter, Comparer.

### 5.5 Vue « Mappings inter-référentiels »

- **Matrice de mapping :** Tableau croisé Référentiel A (lignes) × Référentiel B (colonnes) avec indicateur de correspondance dans chaque cellule. Sélection des deux référentiels via des filtres.
- **Vue par exigence :** Sélection d'une exigence pour afficher toutes ses correspondances dans les autres référentiels.
- **Analyse de couverture :** Pour un référentiel donné, pourcentage des exigences couvertes par un autre référentiel. Visualisation en barres empilées.
- **Détail / Édition :** Formulaire de création/modification d'un mapping avec type, couverture, justification.
- **Actions :** Créer, Modifier, Importer en masse, Exporter.

### 5.6 Vue « Plans d'action »

- **Liste :** Tableau avec colonnes (Référence, Intitulé, Exigence, Référentiel, Priorité, Responsable, Date cible, Avancement %, Statut). Barre de progression visuelle. Code couleur pour les actions en retard.
- **Kanban :** Vue en colonnes par statut (Planifié → En cours → Terminé / En retard).
- **Détail / Édition :** Formulaire avec description de l'écart, plan de remédiation, liens vers mesures et exigence.
- **Actions :** Créer, Modifier, Clôturer, Exporter.

### 5.7 Vue « Déclaration d'applicabilité » (Statement of Applicability — DdA)

Vue dédiée spécifique à l'ISO 27001 :

- Tableau listant toutes les mesures de l'Annexe A avec colonnes (Référence, Intitulé, Applicable, Justification d'inclusion/exclusion, Statut de mise en œuvre, Référence à la mesure Open GRC).
- Filtres par section de l'Annexe A, par applicabilité, par statut.
- Export PDF/DOCX formaté conforme aux attendus d'un audit de certification.

### 5.8 Tableau de bord du module

Un tableau de bord synthétique agrège les informations clés :

- Niveau de conformité global par référentiel (jauges)
- Répartition des exigences par statut de conformité (camembert / barres empilées)
- Évolution du niveau de conformité dans le temps (courbe de tendance par référentiel)
- Nombre d'exigences non conformes par priorité (critique, haute, moyenne, basse)
- Non-conformités réglementaires critiques (alertes)
- Plans d'action en retard
- Couverture des mappings entre référentiels
- Prochaines dates de revue et d'évaluation
- Top 10 des exigences les plus à risque (non conformes, priorité élevée, référentiel obligatoire)
- Alertes et actions requises

---

## 6. Permissions et contrôle d'accès

### 6.1 Modèle RBAC

| Permission | Description |
|---|---|
| `compliance.framework.read` | Consulter les référentiels |
| `compliance.framework.write` | Créer/modifier les référentiels |
| `compliance.framework.delete` | Supprimer les référentiels |
| `compliance.section.read` | Consulter les sections |
| `compliance.section.write` | Créer/modifier les sections |
| `compliance.section.delete` | Supprimer les sections |
| `compliance.requirement.read` | Consulter les exigences |
| `compliance.requirement.write` | Créer/modifier les exigences |
| `compliance.requirement.assess` | Évaluer la conformité des exigences |
| `compliance.requirement.delete` | Supprimer les exigences |
| `compliance.assessment.read` | Consulter les évaluations |
| `compliance.assessment.write` | Créer/modifier les évaluations |
| `compliance.assessment.validate` | Valider une évaluation |
| `compliance.assessment.delete` | Supprimer les évaluations |
| `compliance.mapping.read` | Consulter les mappings |
| `compliance.mapping.write` | Créer/modifier les mappings |
| `compliance.mapping.delete` | Supprimer les mappings |
| `compliance.action_plan.read` | Consulter les plans d'action |
| `compliance.action_plan.write` | Créer/modifier les plans d'action |
| `compliance.action_plan.delete` | Supprimer les plans d'action |
| `compliance.import` | Importer des référentiels et mappings en masse |
| `compliance.export` | Exporter les données du module |
| `compliance.config.manage` | Gérer les listes de valeurs paramétrables |
| `compliance.audit_trail.read` | Consulter le journal d'audit |

### 6.2 Rôles applicatifs suggérés

| Rôle | Permissions |
|---|---|
| **Administrateur** | Toutes les permissions |
| **RSSI / DPO** | Toutes sauf `*.delete` et `config.manage` |
| **Auditeur** | `*.read` + `compliance.export` + `compliance.audit_trail.read` |
| **Évaluateur** | `*.read` + `compliance.requirement.assess` + `compliance.assessment.write` |
| **Contributeur** | `*.read` + `*.write` (hors validate et config) |
| **Lecteur** | `*.read` uniquement |

---

## 7. Journalisation et traçabilité

### 7.1 Audit Trail

Identique aux modules précédents (§7.1 du Module 1). Les actions spécifiques à ce module incluent :

| Action | Description |
|---|---|
| `create` | Création d'un référentiel, section, exigence, mapping ou plan d'action |
| `update` | Modification d'un objet |
| `delete` | Suppression d'un objet |
| `assess` | Évaluation de la conformité d'une exigence |
| `validate_assessment` | Validation d'une campagne d'évaluation |
| `import` | Import en masse (référentiel, mappings) |
| `create_mapping` | Création d'un mapping inter-référentiels |
| `delete_mapping` | Suppression d'un mapping |
| `complete_action_plan` | Clôture d'un plan d'action |

### 7.2 Rétention

Identique aux modules précédents. Durée paramétrable, défaut 7 ans.

---

## 8. Export et reporting

### 8.1 Formats d'export

| Format | Contenu |
|---|---|
| **JSON** | Export brut structuré (pour interopérabilité API) |
| **PDF** | Document formaté avec synthèse de conformité, détail par référentiel |
| **DOCX** | Document éditable au format Word |
| **CSV** | Export tabulaire : référentiels, exigences, résultats d'évaluation, mappings |

### 8.2 Import

| Format | Contenu |
|---|---|
| **CSV** | Import tabulaire de référentiels (sections + exigences) et de mappings |
| **JSON** | Import structuré conforme au schéma API |

L'import supporte les modes : création uniquement, mise à jour uniquement, ou upsert basé sur la référence.

### 8.3 Rapports prédéfinis

| Rapport | Description |
|---|---|
| Synthèse de conformité | Vue globale par référentiel avec jauges et tendances |
| Déclaration d'applicabilité (DdA / SoA) | Tableau des exigences avec applicabilité et justification (ISO 27001) |
| Rapport d'évaluation | Détail des résultats d'une campagne d'évaluation |
| Rapport d'écarts | Liste des non-conformités avec priorisation |
| Rapport de couverture inter-référentiels | Analyse de couverture entre deux référentiels via les mappings |
| Suivi des plans d'action | Liste des plans d'action avec avancement et retards |
| Rapport de tendance | Évolution de la conformité sur plusieurs évaluations |
| Rapport données personnelles (RGPD) | Exigences RGPD avec statut de conformité et mesures associées |

---

## 9. Notifications et alertes

| Événement | Destinataires | Canal |
|---|---|---|
| Non-conformité critique détectée (exigence obligatoire, référentiel réglementaire) | RSSI, DPO, Responsable du référentiel | In-app, email |
| Évaluation en attente de validation | Validateur désigné | In-app, email |
| Plan d'action en retard | Responsable de l'action, RSSI | In-app, email |
| Date de revue atteinte (référentiel, exigence) | Responsable du référentiel | In-app, email |
| Référentiel arrivant à expiration | Responsable, Administrateur | In-app, email |
| Nouvelle évaluation disponible pour un référentiel | Responsable du référentiel | In-app |
| Import en masse terminé | Utilisateur ayant lancé l'import | In-app, email |
| Mapping créé sur une exigence dont on est responsable | Responsable de l'exigence | In-app |
| Plan d'action complété — suggestion de réévaluation | Responsable de l'exigence | In-app |
| Niveau de conformité passé sous un seuil paramétrable | RSSI, Responsable du référentiel | In-app, email |

---

## 10. Considérations techniques

### 10.1 Calcul automatique des niveaux de conformité

Le calcul du niveau de conformité est effectué côté serveur selon l'algorithme suivant :

```
Pour chaque Framework F :
    exigences_applicables = Requirements de F où is_applicable = true
    F.compliance_level = MOYENNE(compliance_level de chaque exigence applicable)
    
Pour chaque Section S :
    exigences_applicables = Requirements de S (et sous-sections) où is_applicable = true
    S.compliance_level = MOYENNE(compliance_level de chaque exigence applicable)
```

Correspondance statut → niveau par défaut (paramétrable) :

| Statut | Niveau par défaut |
|---|---|
| `not_assessed` | 0 % |
| `non_compliant` | 0 % |
| `partially_compliant` | 50 % |
| `compliant` | 100 % |
| `not_applicable` | Exclu du calcul |

Le recalcul est déclenché :
- À la modification du `compliance_status` ou `compliance_level` d'une exigence
- À la validation d'une évaluation
- À la modification de l'applicabilité d'une exigence
- Les résultats sont mis en cache avec invalidation événementielle

### 10.2 Import de référentiels

L'import d'un référentiel complet (sections + exigences) est traité de manière asynchrone :

1. L'utilisateur téléverse le fichier et configure le mapping des colonnes (pour CSV)
2. Le système valide la structure (hiérarchie des sections, références uniques)
3. Un rapport de pré-import est généré
4. L'utilisateur confirme l'import
5. Le traitement est exécuté en arrière-plan
6. Un rapport d'import est généré (succès, échecs, doublons)

Des **modèles de référentiels prédéfinis** peuvent être fournis (ISO 27001 Annexe A, RGPD, NIS 2, etc.) sous forme de fichiers JSON importables. Ces modèles contiennent la structure et les exigences mais pas les évaluations.

### 10.3 Gestion des pièces jointes

Les pièces jointes (preuves documentaires) sont stockées sur un système de fichiers ou un stockage objet (S3-compatible). Les métadonnées sont en base de données, les fichiers binaires sur le stockage. Taille maximale par fichier paramétrable (défaut : 50 Mo). Types MIME autorisés paramétrables.

### 10.4 Multi-tenant

Identique aux modules précédents. Isolation des données via `tenant_id`.

### 10.5 Internationalisation (i18n)

Identique aux modules précédents. Support français et anglais minimum. Les référentiels et exigences sont saisis dans la langue de l'utilisateur ; le système ne gère pas la traduction automatique du contenu des exigences.

### 10.6 Performances

- Les listes paginées ne doivent pas dépasser un temps de réponse de **200 ms** pour 1 000 enregistrements.
- Le calcul du niveau de conformité d'un référentiel de 500 exigences doit s'exécuter en moins de **1 seconde**.
- La matrice de mapping entre deux référentiels de 200 exigences chacun doit se charger en moins de **2 secondes**.
- Les tableaux de bord agrégés sont mis en cache avec un TTL de **5 minutes**.
- Les imports volumineux (> 200 exigences) sont traités de manière asynchrone.

### 10.7 Webhooks

Identique aux modules précédents. Événements spécifiques :

- `compliance.framework.created`, `updated`, `deleted`
- `compliance.requirement.created`, `updated`, `assessed`
- `compliance.assessment.created`, `validated`
- `compliance.mapping.created`, `deleted`
- `compliance.action_plan.created`, `completed`, `overdue`
- `compliance.import.completed`

---

## 11. Critères d'acceptation

### 11.1 Fonctionnels

- [ ] CRUD complet sur les référentiels, sections, exigences, évaluations, mappings et plans d'action
- [ ] Toutes les relations entre entités sont fonctionnelles
- [ ] Les vues liste supportent pagination, tri, filtrage et recherche
- [ ] La structure hiérarchique des sections est navigable et éditable
- [ ] L'évaluation de conformité fonctionne exigence par exigence et en mode campagne
- [ ] Le niveau de conformité est calculé automatiquement à tous les niveaux (exigence, section, référentiel)
- [ ] La comparaison entre deux évaluations successives est fonctionnelle
- [ ] Les mappings inter-référentiels sont créables et consultables sous forme de matrice
- [ ] L'analyse de couverture entre référentiels est fonctionnelle
- [ ] Les plans d'action sont gérables avec suivi d'avancement
- [ ] La vue Déclaration d'Applicabilité (DdA) est fonctionnelle et exportable
- [ ] Les alertes (non-conformité critique, plans en retard, revues) sont fonctionnelles
- [ ] L'import en masse de référentiels et de mappings est opérationnel
- [ ] Les exports sont opérationnels dans tous les formats prévus
- [ ] Le tableau de bord synthétique affiche les données correctes avec tendances

### 11.2 API

- [ ] Tous les endpoints documentés sont implémentés et fonctionnels
- [ ] La documentation OpenAPI (Swagger) est générée automatiquement
- [ ] Les codes d'erreur et structures de réponse sont conformes aux spécifications
- [ ] La pagination, le tri et le filtrage fonctionnent sur tous les endpoints de liste
- [ ] Les webhooks sont déclenchés pour chaque événement de mutation

### 11.3 Sécurité

- [ ] Le contrôle d'accès RBAC est appliqué sur chaque endpoint et chaque vue
- [ ] La permission `compliance.assessment.validate` est requise pour valider une évaluation
- [ ] La permission `compliance.requirement.assess` est requise pour évaluer une exigence
- [ ] Le journal d'audit enregistre toutes les opérations
- [ ] Les données sont isolées entre tenants
- [ ] Les pièces jointes ne sont accessibles qu'aux utilisateurs autorisés

### 11.4 Performance

- [ ] Les temps de réponse respectent les seuils définis (§10.6)
- [ ] Le calcul de conformité respecte le seuil de 1 seconde pour 500 exigences
- [ ] Les imports volumineux sont traités de manière asynchrone

---

*Fin des spécifications du Module 3 — Conformité*
