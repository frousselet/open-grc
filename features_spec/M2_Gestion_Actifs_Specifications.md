# Module 2 — Gestion des Actifs

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 27 février 2026
**Statut :** Draft

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **Gestion des Actifs** permet d'identifier, classifier et maintenir à jour l'inventaire des actifs informationnels de l'organisme. Il distingue les **biens essentiels** (processus métier, informations) des **biens supports** (matériels, logiciels, réseaux, personnes, sites) conformément aux approches ISO 27001 (annexe A — A.5.9 à A.5.14), ISO 27005 et EBIOS RM (socle de sécurité et identification des biens supports).

Ce module constitue le socle de l'appréciation des risques : les biens essentiels portent les besoins de sécurité (critères DIC — Disponibilité, Intégrité, Confidentialité) et les biens supports héritent de ces besoins via leurs relations de dépendance.

### 1.2 Périmètre fonctionnel

Le module couvre quatre sous-domaines :

1. Biens essentiels (processus métier et informations)
2. Biens supports (matériels, logiciels, réseaux, personnes, sites, services)
3. Relations de dépendance entre biens essentiels et biens supports
4. Valorisation et classification des actifs (besoins de sécurité DIC)

### 1.3 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Contexte et Organisation | Les activités/processus (Module 1) sont rattachés aux biens essentiels. Le périmètre (Scope) cadre l'inventaire des actifs. |
| Gestion des risques | Les biens essentiels et supports sont les sujets de l'appréciation des risques (ISO 27005 et EBIOS RM). Les besoins de sécurité DIC alimentent l'évaluation de l'impact. |
| Conformité | Certaines exigences réglementaires portent directement sur des catégories d'actifs (données personnelles, données de santé, etc.). |
| Mesures | Les mesures de sécurité sont appliquées sur des biens supports pour protéger les biens essentiels. |
| Fournisseurs | Les biens supports de type service externalisé sont liés aux fournisseurs. |
| Incidents | Les incidents sont rattachés aux actifs impactés. |

---

## 2. Modèle de données

### 2.1 Entité : EssentialAsset (Bien essentiel)

Représente un processus métier ou un type d'information essentiel pour l'organisme dont la compromission aurait un impact significatif.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. BE-001) |
| `name` | string | requis, max 255 | Nom du bien essentiel |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `business_process`, `information` |
| `category` | enum | requis | Voir liste ci-dessous |
| `owner_id` | relation | FK → User, requis | Propriétaire du bien essentiel |
| `custodian_id` | relation | FK → User, optionnel | Dépositaire / responsable opérationnel |
| `confidentiality_level` | enum | requis | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `integrity_level` | enum | requis | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `availability_level` | enum | requis | `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4) |
| `confidentiality_justification` | text | optionnel | Justification du niveau de confidentialité |
| `integrity_justification` | text | optionnel | Justification du niveau d'intégrité |
| `availability_justification` | text | optionnel | Justification du niveau de disponibilité |
| `max_tolerable_downtime` | string | optionnel | Durée maximale d'indisponibilité tolérable (DMIT / MTD) |
| `recovery_time_objective` | string | optionnel | Objectif de temps de reprise (RTO) |
| `recovery_point_objective` | string | optionnel | Objectif de point de reprise (RPO) |
| `data_classification` | enum | optionnel | `public`, `internal`, `confidential`, `restricted`, `secret` |
| `personal_data` | boolean | requis, défaut false | Contient des données à caractère personnel |
| `personal_data_categories` | json | optionnel | Catégories de données personnelles (RGPD) |
| `regulatory_constraints` | text | optionnel | Contraintes réglementaires spécifiques |
| `related_activities` | relation | M2M → Activity | Activités métier associées (Module 1) |
| `supporting_assets` | relation | M2M → SupportAsset (via AssetDependency) | Biens supports associés |
| `status` | enum | requis | `identified`, `active`, `under_review`, `decommissioned` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de biens essentiels (valeurs de `category`) :**

- *Type `business_process` :* `core_process`, `support_process`, `management_process`
- *Type `information` :* `strategic_data`, `operational_data`, `personal_data`, `financial_data`, `technical_data`, `legal_data`, `research_data`, `commercial_data`

> Note : Les catégories doivent être paramétrables par l'administrateur.

### 2.2 Entité : SupportAsset (Bien support)

Représente un actif technique, humain ou physique qui supporte les biens essentiels et sur lequel les vulnérabilités peuvent être exploitées.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `reference` | string | requis, unique | Code de référence (ex. BS-001) |
| `name` | string | requis, max 255 | Nom du bien support |
| `description` | text | optionnel | Description détaillée |
| `type` | enum | requis | `hardware`, `software`, `network`, `person`, `site`, `service`, `paper` |
| `category` | enum | requis | Voir liste ci-dessous |
| `owner_id` | relation | FK → User, requis | Propriétaire du bien support |
| `custodian_id` | relation | FK → User, optionnel | Dépositaire / responsable opérationnel |
| `location` | string | optionnel | Localisation physique |
| `manufacturer` | string | optionnel | Fabricant / éditeur |
| `model` | string | optionnel | Modèle / version |
| `serial_number` | string | optionnel | Numéro de série |
| `version` | string | optionnel | Version (logiciel, firmware) |
| `ip_address` | string | optionnel | Adresse IP (si applicable) |
| `hostname` | string | optionnel | Nom d'hôte (si applicable) |
| `operating_system` | string | optionnel | Système d'exploitation |
| `acquisition_date` | date | optionnel | Date d'acquisition |
| `end_of_life_date` | date | optionnel | Date de fin de vie / fin de support |
| `warranty_expiry_date` | date | optionnel | Date d'expiration de la garantie |
| `supplier_id` | relation | FK → Supplier, optionnel | Fournisseur associé (Module Fournisseurs) |
| `contract_reference` | string | optionnel | Référence du contrat associé |
| `inherited_confidentiality` | enum | calculé | Niveau hérité max des biens essentiels |
| `inherited_integrity` | enum | calculé | Niveau hérité max des biens essentiels |
| `inherited_availability` | enum | calculé | Niveau hérité max des biens essentiels |
| `exposure_level` | enum | optionnel | `internal`, `exposed`, `internet_facing`, `dmz` |
| `environment` | enum | optionnel | `production`, `staging`, `development`, `test`, `disaster_recovery` |
| `essential_assets` | relation | M2M → EssentialAsset (via AssetDependency) | Biens essentiels supportés |
| `parent_asset_id` | relation | FK → SupportAsset, optionnel | Bien support parent (composition) |
| `related_measures` | relation | M2M → Measure | Mesures de sécurité appliquées (Module Mesures) |
| `status` | enum | requis | `in_stock`, `deployed`, `active`, `under_maintenance`, `decommissioned`, `disposed` |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

**Catégories de biens supports (valeurs de `category`) :**

- *`hardware` :* `server`, `workstation`, `laptop`, `mobile_device`, `network_equipment`, `storage`, `peripheral`, `iot_device`, `removable_media`, `other_hardware`
- *`software` :* `operating_system`, `database`, `application`, `middleware`, `security_tool`, `development_tool`, `saas_application`, `other_software`
- *`network` :* `lan`, `wan`, `wifi`, `vpn`, `internet_link`, `firewall_zone`, `dmz`, `other_network`
- *`person` :* `internal_staff`, `contractor`, `external_provider`, `administrator`, `developer`, `other_person`
- *`site` :* `datacenter`, `office`, `remote_site`, `cloud_region`, `other_site`
- *`service` :* `cloud_service`, `hosting_service`, `managed_service`, `telecom_service`, `outsourced_service`, `other_service`
- *`paper` :* `archive`, `printed_document`, `form`, `other_paper`

> Note : Les catégories doivent être paramétrables par l'administrateur.

### 2.3 Entité : AssetDependency (Relation de dépendance)

Représente le lien de dépendance entre un bien essentiel et un bien support. C'est via cette relation que les besoins de sécurité DIC sont hérités par les biens supports.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `essential_asset_id` | relation | FK → EssentialAsset, requis | Bien essentiel source |
| `support_asset_id` | relation | FK → SupportAsset, requis | Bien support cible |
| `dependency_type` | enum | requis | `runs_on`, `stored_in`, `transmitted_by`, `managed_by`, `hosted_at`, `protected_by`, `other` |
| `criticality` | enum | requis | `low`, `medium`, `high`, `critical` |
| `description` | text | optionnel | Description de la relation de dépendance |
| `is_single_point_of_failure` | boolean | requis, défaut false | Point unique de défaillance |
| `redundancy_level` | enum | optionnel | `none`, `partial`, `full` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Contrainte d'unicité : le couple (`essential_asset_id`, `support_asset_id`) doit être unique.

### 2.4 Entité : AssetGroup (Groupe d'actifs)

Permet de regrouper des biens supports par lot logique (ex. « Serveurs de production », « Postes de travail site Paris ») pour faciliter la gestion et l'appréciation des risques.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Nom du groupe |
| `description` | text | optionnel | Description du groupe |
| `type` | enum | requis | Même typologie que SupportAsset.type |
| `members` | relation | M2M → SupportAsset | Biens supports membres |
| `owner_id` | relation | FK → User, optionnel | Responsable du groupe |
| `status` | enum | requis | `active`, `inactive` |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.5 Sous-entité : AssetValuation (Historique de valorisation)

Conserve l'historique des évaluations DIC d'un bien essentiel, permettant de suivre l'évolution des besoins de sécurité dans le temps.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `essential_asset_id` | relation | FK → EssentialAsset, requis | Bien essentiel évalué |
| `evaluation_date` | date | requis | Date de l'évaluation |
| `confidentiality_level` | enum | requis | Niveau C à cette date |
| `integrity_level` | enum | requis | Niveau I à cette date |
| `availability_level` | enum | requis | Niveau D à cette date |
| `evaluated_by` | relation | FK → User, requis | Évaluateur |
| `justification` | text | optionnel | Justification globale de l'évaluation |
| `context` | text | optionnel | Contexte de l'évaluation (revue annuelle, incident, changement…) |
| `created_at` | datetime | auto | Date de création |

---

## 3. Règles de gestion

### 3.1 Règles générales

| ID | Règle |
|---|---|
| RG-01 | Tout actif (bien essentiel ou bien support) doit être rattaché à un **Scope** actif. |
| RG-02 | Tout actif doit avoir un **propriétaire** (`owner_id`) désigné. |
| RG-03 | La suppression d'un actif référencé par le module Risques ou Mesures est interdite. Une désactivation (`status = decommissioned` ou `disposed`) est utilisée à la place. |
| RG-04 | Toute modification d'un actif génère une entrée dans le **journal d'audit**. |
| RG-05 | Les champs `created_at` et `updated_at` sont gérés automatiquement par le système. |
| RG-06 | Les listes de valeurs paramétrables (catégories, types) sont gérées via la table de configuration dédiée. |
| RG-07 | Les relations M2M sont stockées dans des tables de jointure dédiées. |
| RG-08 | Les codes de référence (`reference`) suivent un format paramétrable avec incrémentation automatique. Le préfixe par défaut est `BE-` pour les biens essentiels et `BS-` pour les biens supports. |

### 3.2 Règles de valorisation et héritage DIC

| ID | Règle |
|---|---|
| RV-01 | Les niveaux DIC (Disponibilité, Intégrité, Confidentialité) d'un bien essentiel sont évalués sur une échelle à 5 niveaux : `negligible` (0), `low` (1), `medium` (2), `high` (3), `critical` (4). |
| RV-02 | L'échelle DIC et ses descriptions associées sont paramétrables par l'administrateur. |
| RV-03 | Les niveaux DIC **hérités** par un bien support correspondent au **maximum** des niveaux DIC de tous les biens essentiels auxquels il est rattaché. Ce calcul est effectué automatiquement. |
| RV-04 | Toute modification des niveaux DIC d'un bien essentiel déclenche un **recalcul** des niveaux hérités de ses biens supports associés. |
| RV-05 | L'utilisateur peut consulter le détail de l'héritage DIC d'un bien support (quels biens essentiels contribuent à chaque niveau). |
| RV-06 | Lors de chaque modification des niveaux DIC d'un bien essentiel, un enregistrement `AssetValuation` est créé pour conserver l'historique. |

### 3.3 Règles spécifiques

| ID | Règle |
|---|---|
| RS-01 | Un bien essentiel de type `business_process` ne peut avoir que des catégories de processus, et inversement pour `information`. |
| RS-02 | Un bien support de type donné ne peut avoir que des catégories correspondant à ce type. |
| RS-03 | Un bien support avec `end_of_life_date` dépassée et `status = active` déclenche une **alerte** de fin de vie. |
| RS-04 | Un bien support avec `status = decommissioned` ou `disposed` ne peut pas être rattaché à de nouvelles dépendances. |
| RS-05 | Un bien essentiel marqué `personal_data = true` doit renseigner `data_classification` avec un niveau ≥ `confidential`. Le système émet une alerte dans le cas contraire. |
| RS-06 | Un bien support enfant (`parent_asset_id` renseigné) doit appartenir au même **Scope** que son parent. |
| RS-07 | Une relation `AssetDependency` marquée `is_single_point_of_failure = true` avec `redundancy_level = none` déclenche une **alerte** spécifique affichée sur le tableau de bord. |
| RS-08 | Un bien essentiel sans aucun bien support associé déclenche une **alerte** (bien essentiel non supporté). |
| RS-09 | Un bien support sans aucun bien essentiel associé déclenche un **avertissement** (bien support orphelin). |

---

## 4. Spécifications API REST

### 4.1 Conventions générales

Identiques au Module 1. Base URL : `/api/v1/assets/`

### 4.2 Endpoints — Essential Assets (Biens essentiels)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/essential-assets` | Lister tous les biens essentiels (filtrable) |
| `GET` | `/scopes/{scope_id}/essential-assets` | Lister les biens essentiels d'un périmètre |
| `POST` | `/scopes/{scope_id}/essential-assets` | Créer un bien essentiel |
| `GET` | `/essential-assets/{id}` | Détail d'un bien essentiel |
| `PUT` | `/essential-assets/{id}` | Mise à jour complète |
| `PATCH` | `/essential-assets/{id}` | Mise à jour partielle |
| `DELETE` | `/essential-assets/{id}` | Supprimer (si non référencé) |
| `GET` | `/essential-assets/{id}/supporting-assets` | Lister les biens supports associés |
| `GET` | `/essential-assets/{id}/dependencies` | Lister les relations de dépendance |
| `GET` | `/essential-assets/{id}/valuations` | Historique des valorisations DIC |
| `POST` | `/essential-assets/{id}/valuations` | Enregistrer une nouvelle valorisation |
| `GET` | `/essential-assets/{id}/risks` | Lister les risques associés (Module Risques) |
| `GET` | `/essential-assets/categories` | Lister les catégories disponibles |
| `GET` | `/essential-assets/dashboard` | Données de tableau de bord (KPIs agrégés) |

**Paramètres de filtrage spécifiques :**

- `?type=business_process|information`
- `?category=core_process`
- `?confidentiality_level=high,critical`
- `?integrity_level=high,critical`
- `?availability_level=high,critical`
- `?personal_data=true`
- `?data_classification=confidential,restricted,secret`
- `?owner_id={uuid}`
- `?status=active`
- `?has_supporting_assets=true|false`
- `?activity_id={uuid}` (biens essentiels liés à une activité)

### 4.3 Endpoints — Support Assets (Biens supports)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/support-assets` | Lister tous les biens supports (filtrable) |
| `GET` | `/scopes/{scope_id}/support-assets` | Lister les biens supports d'un périmètre |
| `POST` | `/scopes/{scope_id}/support-assets` | Créer un bien support |
| `GET` | `/support-assets/{id}` | Détail d'un bien support |
| `PUT` | `/support-assets/{id}` | Mise à jour complète |
| `PATCH` | `/support-assets/{id}` | Mise à jour partielle |
| `DELETE` | `/support-assets/{id}` | Supprimer (si non référencé) |
| `GET` | `/support-assets/{id}/essential-assets` | Lister les biens essentiels supportés |
| `GET` | `/support-assets/{id}/dependencies` | Lister les relations de dépendance |
| `GET` | `/support-assets/{id}/inherited-dic` | Détail du calcul DIC hérité |
| `GET` | `/support-assets/{id}/children` | Lister les sous-biens supports |
| `GET` | `/support-assets/{id}/measures` | Lister les mesures appliquées (Module Mesures) |
| `GET` | `/support-assets/{id}/risks` | Lister les risques associés (Module Risques) |
| `GET` | `/support-assets/{id}/incidents` | Lister les incidents associés (Module Incidents) |
| `GET` | `/support-assets/categories` | Lister les catégories disponibles |
| `GET` | `/support-assets/tree` | Arborescence des biens supports |
| `GET` | `/support-assets/end-of-life` | Lister les actifs en fin de vie ou proches |
| `GET` | `/support-assets/dashboard` | Données de tableau de bord (KPIs agrégés) |

**Paramètres de filtrage spécifiques :**

- `?type=hardware|software|network|person|site|service|paper`
- `?category=server`
- `?exposure_level=internet_facing`
- `?environment=production`
- `?inherited_confidentiality=high,critical`
- `?owner_id={uuid}`
- `?supplier_id={uuid}`
- `?status=active`
- `?end_of_life_before={date}` (actifs dont la fin de vie est avant une date)
- `?has_essential_assets=true|false`
- `?is_orphan=true` (pas de bien essentiel associé)
- `?group_id={uuid}`

### 4.4 Endpoints — Asset Dependencies (Relations de dépendance)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/dependencies` | Lister toutes les relations de dépendance |
| `POST` | `/dependencies` | Créer une relation de dépendance |
| `GET` | `/dependencies/{id}` | Détail d'une relation |
| `PUT` | `/dependencies/{id}` | Mise à jour complète |
| `PATCH` | `/dependencies/{id}` | Mise à jour partielle |
| `DELETE` | `/dependencies/{id}` | Supprimer une relation |
| `GET` | `/dependencies/spof` | Lister les points uniques de défaillance |
| `GET` | `/dependencies/graph` | Graphe de dépendances (données pour visualisation) |

### 4.5 Endpoints — Asset Groups (Groupes d'actifs)

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/groups` | Lister les groupes d'actifs |
| `POST` | `/groups` | Créer un groupe |
| `GET` | `/groups/{id}` | Détail d'un groupe |
| `PUT` | `/groups/{id}` | Mise à jour complète |
| `PATCH` | `/groups/{id}` | Mise à jour partielle |
| `DELETE` | `/groups/{id}` | Supprimer un groupe |
| `POST` | `/groups/{id}/members` | Ajouter des membres au groupe |
| `DELETE` | `/groups/{id}/members/{asset_id}` | Retirer un membre du groupe |
| `GET` | `/groups/{id}/members` | Lister les membres du groupe |

### 4.6 Endpoints transversaux

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/assets/dashboard` | Tableau de bord synthétique du module |
| `GET` | `/assets/export` | Export global des actifs (PDF, DOCX, JSON, CSV) |
| `GET` | `/assets/audit-trail` | Journal d'audit du module |
| `GET` | `/assets/config/enums` | Lister toutes les listes de valeurs paramétrables |
| `PUT` | `/assets/config/enums/{enum_name}` | Modifier une liste de valeurs |
| `GET` | `/assets/config/dic-scale` | Consulter l'échelle DIC paramétrée |
| `PUT` | `/assets/config/dic-scale` | Modifier l'échelle DIC |
| `GET` | `/assets/statistics` | Statistiques globales (répartition par type, classification, etc.) |
| `POST` | `/assets/import` | Import en masse (CSV, JSON) |
| `GET` | `/assets/alerts` | Lister les alertes actives (fin de vie, orphelins, SPOF, etc.) |

---

## 5. Spécifications d'interface utilisateur

### 5.1 Navigation

Le module est accessible via un élément de navigation principal « Gestion des Actifs » se décomposant en sous-menus : Biens essentiels, Biens supports, Groupes d'actifs, Cartographie des dépendances, Tableau de bord.

### 5.2 Vue « Biens essentiels »

- **Liste :** Tableau avec colonnes (Référence, Nom, Type, Catégorie, Propriétaire, C/I/D, Classification, Statut). Chaque niveau DIC est affiché avec un indicateur coloré (vert → rouge). Filtres et tri sur toutes les colonnes.
- **Détail / Édition :** Formulaire avec onglets :
  - *Informations générales :* identification, type, catégorie, propriétaire, dépositaire.
  - *Valorisation DIC :* évaluation des 3 critères avec curseurs ou sélecteurs, justifications, DMIT/RTO/RPO.
  - *Classification :* classification des données, données personnelles, contraintes réglementaires.
  - *Relations :* biens supports associés (avec type de dépendance), activités métier liées.
  - *Historique :* historique des valorisations et modifications.
- **Actions :** Créer, Modifier, Évaluer (DIC), Exporter.

### 5.3 Vue « Biens supports »

- **Liste :** Tableau avec colonnes (Référence, Nom, Type, Catégorie, Propriétaire, DIC hérité, Environnement, Exposition, Statut, Fin de vie). Indicateur visuel pour les actifs en fin de vie (icône d'avertissement). Filtres et tri sur toutes les colonnes.
- **Vue par type :** Affichage groupé par type (matériel, logiciel, réseau, etc.) avec compteurs.
- **Détail / Édition :** Formulaire avec onglets :
  - *Informations générales :* identification, type, catégorie, propriétaire, dépositaire.
  - *Caractéristiques techniques :* fabricant, modèle, version, IP, hostname, OS, numéro de série.
  - *Cycle de vie :* dates d'acquisition, fin de vie, garantie, environnement, exposition.
  - *DIC hérité :* affichage en lecture seule des niveaux DIC hérités avec le détail de la provenance (quels biens essentiels).
  - *Relations :* biens essentiels supportés, sous-biens supports, groupes, mesures appliquées.
  - *Fournisseur :* lien vers le fournisseur et la référence contrat.
  - *Historique :* journal des modifications.
- **Actions :** Créer, Modifier, Décommissionner, Exporter.

### 5.4 Vue « Groupes d'actifs »

- **Liste :** Tableau avec colonnes (Nom, Type, Nombre de membres, Propriétaire, Statut).
- **Détail :** Liste des membres avec possibilité d'ajout/retrait, informations du groupe.
- **Actions :** Créer, Modifier, Ajouter/Retirer des membres, Supprimer.

### 5.5 Vue « Cartographie des dépendances »

- **Graphe interactif :** Visualisation en graphe des relations entre biens essentiels et biens supports. Les nœuds sont colorés par type d'actif, les arêtes annotées par le type de dépendance. Zoom, filtrage par type/criticité, mise en évidence des SPOF.
- **Matrice de dépendance :** Vue tabulaire croisée biens essentiels × biens supports avec indicateurs de criticité et type de dépendance dans chaque cellule.
- **Vue par bien essentiel :** Sélection d'un bien essentiel pour afficher tous ses biens supports associés en arborescence.

### 5.6 Vue « Classification et DIC »

- **Heatmap DIC :** Vue matricielle des biens essentiels avec les 3 colonnes C, I, D colorées par niveau. Tri possible par niveau le plus élevé.
- **Répartition par classification :** Graphique en secteurs ou barres de la répartition des biens par niveau de classification.
- **Données personnelles :** Vue filtrée des biens essentiels contenant des données personnelles, avec catégories RGPD.

### 5.7 Tableau de bord du module

Un tableau de bord synthétique agrège les informations clés :

- Nombre total de biens essentiels et supports, répartition par type et statut
- Répartition des niveaux DIC (graphique en barres empilées)
- Nombre et liste des biens supports en fin de vie ou proches
- Nombre et liste des points uniques de défaillance (SPOF)
- Biens essentiels sans bien support associé
- Biens supports orphelins (sans bien essentiel)
- Biens essentiels contenant des données personnelles
- Activités critiques et leurs biens supports
- Top 10 des biens supports les plus sollicités (nombre de biens essentiels rattachés)
- Alertes et actions requises

---

## 6. Permissions et contrôle d'accès

### 6.1 Modèle RBAC

| Permission | Description |
|---|---|
| `assets.essential.read` | Consulter les biens essentiels |
| `assets.essential.write` | Créer/modifier les biens essentiels |
| `assets.essential.evaluate` | Évaluer les niveaux DIC |
| `assets.essential.delete` | Supprimer les biens essentiels |
| `assets.support.read` | Consulter les biens supports |
| `assets.support.write` | Créer/modifier les biens supports |
| `assets.support.delete` | Supprimer les biens supports |
| `assets.dependency.read` | Consulter les relations de dépendance |
| `assets.dependency.write` | Créer/modifier les relations de dépendance |
| `assets.dependency.delete` | Supprimer les relations de dépendance |
| `assets.group.read` | Consulter les groupes d'actifs |
| `assets.group.write` | Créer/modifier les groupes d'actifs |
| `assets.group.delete` | Supprimer les groupes d'actifs |
| `assets.import` | Importer des actifs en masse |
| `assets.export` | Exporter les données du module |
| `assets.config.manage` | Gérer les listes de valeurs et l'échelle DIC |
| `assets.audit_trail.read` | Consulter le journal d'audit |

### 6.2 Rôles applicatifs suggérés

| Rôle | Permissions |
|---|---|
| **Administrateur** | Toutes les permissions |
| **RSSI / DPO** | Toutes sauf `*.delete` et `config.manage` |
| **Auditeur** | `*.read` + `assets.export` + `assets.audit_trail.read` |
| **Contributeur** | `*.read` + `*.write` + `assets.dependency.write` |
| **Propriétaire d'actif** | `*.read` + `assets.essential.write` + `assets.support.write` + `assets.essential.evaluate` (restreint à ses propres actifs) |
| **Lecteur** | `*.read` uniquement |

---

## 7. Journalisation et traçabilité

### 7.1 Audit Trail

Identique au Module 1 (§7.1). Les actions spécifiques à ce module incluent :

| Action | Description |
|---|---|
| `create` | Création d'un actif, groupe ou dépendance |
| `update` | Modification d'un actif, groupe ou dépendance |
| `delete` | Suppression d'un actif, groupe ou dépendance |
| `evaluate_dic` | Évaluation ou réévaluation des niveaux DIC |
| `decommission` | Mise hors service d'un actif |
| `import` | Import en masse d'actifs |
| `add_dependency` | Ajout d'une relation de dépendance |
| `remove_dependency` | Suppression d'une relation de dépendance |
| `add_to_group` | Ajout d'un actif à un groupe |
| `remove_from_group` | Retrait d'un actif d'un groupe |

### 7.2 Rétention

Identique au Module 1 (§7.2). Durée paramétrable, défaut 7 ans.

---

## 8. Export et reporting

### 8.1 Formats d'export

| Format | Contenu |
|---|---|
| **JSON** | Export brut structuré (pour interopérabilité API) |
| **PDF** | Document formaté avec inventaire, classifications, cartographie |
| **DOCX** | Document éditable au format Word |
| **CSV** | Export tabulaire séparé : biens essentiels, biens supports, dépendances |

### 8.2 Import

| Format | Contenu |
|---|---|
| **CSV** | Import tabulaire avec mapping de colonnes configurable |
| **JSON** | Import structuré conforme au schéma API |

L'import supporte les modes suivants : création uniquement, mise à jour uniquement, ou création + mise à jour (upsert basé sur la référence).

### 8.3 Rapports prédéfinis

| Rapport | Description |
|---|---|
| Inventaire des biens essentiels | Liste complète avec valorisation DIC et classification |
| Inventaire des biens supports | Liste complète avec caractéristiques techniques et DIC hérité |
| Matrice de dépendances | Tableau croisé biens essentiels × biens supports |
| Rapport de classification | Répartition des actifs par niveau de classification |
| Rapport données personnelles | Biens essentiels contenant des données personnelles avec catégories |
| Rapport fin de vie | Biens supports en fin de vie ou arrivant à échéance |
| Rapport SPOF | Points uniques de défaillance identifiés |
| Rapport de couverture | Biens essentiels non supportés et biens supports orphelins |

---

## 9. Notifications et alertes

| Événement | Destinataires | Canal |
|---|---|---|
| Bien support arrivant en fin de vie (30/60/90 jours avant) | Propriétaire, Administrateur | In-app, email |
| Bien support en fin de vie dépassée | Propriétaire, RSSI | In-app, email |
| Bien essentiel sans bien support associé | Propriétaire | In-app |
| Bien support orphelin (sans bien essentiel) | Propriétaire | In-app |
| Point unique de défaillance détecté (SPOF sans redondance) | Propriétaire, RSSI | In-app, email |
| Données personnelles avec classification insuffisante | DPO, Propriétaire | In-app, email |
| Date de revue atteinte (bien essentiel ou support) | Propriétaire | In-app, email |
| Modification des niveaux DIC d'un bien essentiel | Propriétaires des biens supports impactés | In-app |
| Import en masse terminé | Utilisateur ayant lancé l'import | In-app, email |
| Garantie arrivant à expiration (30/60 jours avant) | Propriétaire | In-app |

---

## 10. Considérations techniques

### 10.1 Calcul automatique de l'héritage DIC

Le calcul des niveaux DIC hérités d'un bien support est effectué côté serveur. L'algorithme est le suivant :

```
Pour chaque bien support BS :
    BS.inherited_confidentiality = MAX(C de tous les biens essentiels liés via AssetDependency)
    BS.inherited_integrity = MAX(I de tous les biens essentiels liés via AssetDependency)
    BS.inherited_availability = MAX(D de tous les biens essentiels liés via AssetDependency)
```

Ce calcul est déclenché :
- À la création ou suppression d'une relation `AssetDependency`
- À la modification des niveaux DIC d'un `EssentialAsset`
- Les résultats sont mis en cache et invalidés lors des événements ci-dessus

### 10.2 Import en masse

L'import en masse d'actifs (CSV, JSON) est traité de manière asynchrone :

1. L'utilisateur téléverse le fichier et configure le mapping des colonnes (pour CSV)
2. Le système valide le fichier (format, champs requis, cohérence des références)
3. Un rapport de pré-import est généré (nombre d'enregistrements, erreurs détectées, avertissements)
4. L'utilisateur confirme l'import
5. Le traitement est exécuté en arrière-plan avec notification à la fin
6. Un rapport d'import est généré (succès, échecs, enregistrements ignorés)

### 10.3 Graphe de dépendances

La visualisation du graphe de dépendances s'appuie sur un endpoint API dédié qui retourne les données au format suivant :

```json
{
  "nodes": [
    {
      "id": "uuid-xxx",
      "label": "BE-001 - Processus RH",
      "type": "essential_asset",
      "subtype": "business_process",
      "dic": { "c": 3, "i": 2, "d": 3 }
    },
    {
      "id": "uuid-yyy",
      "label": "BS-012 - Serveur SIRH",
      "type": "support_asset",
      "subtype": "hardware",
      "inherited_dic": { "c": 3, "i": 2, "d": 3 }
    }
  ],
  "edges": [
    {
      "id": "uuid-zzz",
      "source": "uuid-xxx",
      "target": "uuid-yyy",
      "dependency_type": "runs_on",
      "criticality": "high",
      "is_spof": true
    }
  ]
}
```

### 10.4 Multi-tenant

Identique au Module 1 (§10.2). Isolation des données via `tenant_id`.

### 10.5 Internationalisation (i18n)

Identique au Module 1 (§10.3). Support français et anglais minimum.

### 10.6 Performances

- Les listes paginées ne doivent pas dépasser un temps de réponse de **200 ms** pour 1 000 enregistrements.
- Le calcul d'héritage DIC doit s'exécuter en moins de **500 ms** pour un bien essentiel lié à 100 biens supports.
- Le graphe de dépendances doit se charger en moins de **2 secondes** pour 500 nœuds.
- Les tableaux de bord agrégés sont mis en cache avec un TTL de **5 minutes**.
- Les imports volumineux (> 500 enregistrements) sont traités de manière asynchrone avec notification.

### 10.7 Webhooks

Identique au Module 1 (§10.5). Événements spécifiques :

- `assets.essential_asset.created`, `updated`, `deleted`
- `assets.essential_asset.dic_evaluated`
- `assets.support_asset.created`, `updated`, `deleted`, `decommissioned`
- `assets.dependency.created`, `deleted`
- `assets.group.members_changed`
- `assets.import.completed`

---

## 11. Critères d'acceptation

### 11.1 Fonctionnels

- [ ] CRUD complet sur les biens essentiels, biens supports, groupes et dépendances
- [ ] Toutes les relations entre entités sont fonctionnelles
- [ ] Les vues liste supportent pagination, tri, filtrage et recherche
- [ ] L'évaluation DIC des biens essentiels fonctionne avec historisation
- [ ] L'héritage DIC vers les biens supports est calculé automatiquement et correctement
- [ ] Le détail de l'héritage DIC (provenance) est consultable
- [ ] Le graphe de dépendances est affiché et interactif
- [ ] La matrice de dépendances est consultable
- [ ] Les alertes (fin de vie, SPOF, orphelins, données personnelles) sont fonctionnelles
- [ ] L'import en masse (CSV, JSON) est opérationnel avec pré-validation
- [ ] Les exports sont opérationnels dans tous les formats prévus
- [ ] Le tableau de bord synthétique affiche les données correctes
- [ ] La vue par type et la vue arborescente fonctionnent

### 11.2 API

- [ ] Tous les endpoints documentés sont implémentés et fonctionnels
- [ ] La documentation OpenAPI (Swagger) est générée automatiquement
- [ ] Les codes d'erreur et structures de réponse sont conformes aux spécifications
- [ ] La pagination, le tri et le filtrage fonctionnent sur tous les endpoints de liste
- [ ] L'endpoint de graphe retourne les données au format spécifié
- [ ] Les webhooks sont déclenchés pour chaque événement de mutation

### 11.3 Sécurité

- [ ] Le contrôle d'accès RBAC est appliqué sur chaque endpoint et chaque vue
- [ ] La restriction « propriétaire d'actif » limite bien l'accès aux actifs dont l'utilisateur est propriétaire
- [ ] Le journal d'audit enregistre toutes les opérations
- [ ] Les données sont isolées entre tenants

### 11.4 Performance

- [ ] Les temps de réponse respectent les seuils définis (§10.6)
- [ ] Le calcul d'héritage DIC respecte le seuil de 500 ms
- [ ] Les imports volumineux sont traités de manière asynchrone

---

*Fin des spécifications du Module 2 — Gestion des Actifs*
