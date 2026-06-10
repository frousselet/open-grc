# Indicator

`context.models.indicator.Indicator`

Indicateur de pilotage (KPI) du SMSI, manuel, alimenté par API ou prédéfini par Cairn. Quantifie un objectif, le respect d'une exigence ou la performance d'un contrôle, et sert d'entrée aux tableaux de bord et aux revues de direction.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto-généré `INDC-N`, unique | Référence métier |
| `scopes` | relation | M2M → Scope | Périmètres rattachés (RG-01) |
| `name` | string | requis, max 255 | Intitulé de l'indicateur |
| `description` | text | optionnel, HTML | Description et finalité |
| `indicator_type` | enum | requis | `organizational`, `technical` |
| `collection_method` | enum | requis, défaut `manual` | `manual`, `api`, `internal` |
| `format` | enum | requis, défaut `number` | `number`, `boolean` |
| `unit` | string | optionnel, max 50, interdit pour `boolean` | Unité d'affichage (`%`, `j`, `incidents`, etc.) |
| `current_value` | string | lecture seule, max 255 | Dernière valeur mesurée (mise à jour automatiquement à chaque `IndicatorMeasurement`) |
| `expected_level` | string | optionnel, max 255 | Cible attendue (libellé libre) |
| `critical_threshold_operator` | enum | optionnel | `below`, `above`, `is_false`, `is_true` |
| `critical_threshold_value` | string | optionnel | Valeur seuil (pour `below` / `above`) |
| `critical_threshold_min` | float | optionnel, nombres uniquement | Borne basse hors zone critique |
| `critical_threshold_max` | float | optionnel, nombres uniquement | Borne haute hors zone critique |
| `review_frequency` | enum | requis | `daily`, `weekly`, `monthly`, `quarterly`, `semi_annual`, `annual` |
| `first_review_date` | date | requis | Première date de revue (doit être aujourd'hui ou plus tard à la création) |
| `status` | enum | requis, défaut `active` | `active`, `inactive`, `draft` |
| `is_internal` | boolean | défaut `false` | `true` = indicateur prédéfini Cairn, alimenté en interne |
| `internal_source` | enum | requis si `is_internal=true` | `global_compliance_rate`, `framework_compliance_rate`, `objective_progress`, `risk_treatment_rate`, `approved_scopes_rate`, `mandatory_roles_coverage` |
| `internal_source_parameter` | string | optionnel | Paramètre de la source prédéfinie (par exemple UUID du référentiel pour `framework_compliance_rate`) |
| `owner` | relation | FK → User, optionnel | Propriétaire métier responsable de la mesure et de la revue |
| `linked_objectives` | relation | M2M → Objective | Objectifs dont l'indicateur mesure le progrès (ISO 27001 §6.2 / §9.1) |
| `linked_requirements` | relation | M2M → Requirement | Exigences dont l'indicateur mesure le respect |
| `tags` | relation | M2M → Tag | Étiquettes libres |
| `is_approved` | boolean | défaut `false` | Indicateur validé par un approbateur |
| `approved_by` | relation | FK → User, optionnel | Approbateur |
| `approved_at` | datetime | optionnel | Date d'approbation |
| `version` | int | auto-incrémenté | Bumpé à chaque modification majeure |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

## Énumérations

### `indicator_type`

- `organizational` : indicateur métier ou de gouvernance (taux de conformité, couverture des rôles, etc.). Obligatoire pour les indicateurs prédéfinis (`is_internal=true`).
- `technical` : indicateur technique (temps de réponse, disponibilité, taux d'incidents).

### `collection_method`

- `manual` : saisi à la main par un utilisateur via `IndicatorMeasurement`.
- `api` : alimenté par un appel externe (script, intégration, agent).
- `internal` : alimenté automatiquement par Cairn à partir d'une `internal_source` (cf. ci-dessous).

### `internal_source` (sources prédéfinies)

| Source | Format | Unité | Description |
|---|---|---|---|
| `global_compliance_rate` | number | `%` | Taux de conformité agrégé sur l'ensemble des référentiels applicables |
| `framework_compliance_rate` | number | `%` | Taux de conformité d'un référentiel précis (paramètre = UUID du `Framework`) |
| `objective_progress` | number | `%` | Avancement moyen des objectifs (`Objective.progress_percentage`) |
| `risk_treatment_rate` | number | `%` | Part des risques dont un plan de traitement est `completed` |
| `approved_scopes_rate` | number | `%` | Part des `Scope` au statut `active` ET `is_approved=true` |
| `mandatory_roles_coverage` | number | `%` | Part des rôles avec `is_mandatory=true` qui ont au moins un utilisateur affecté |

Les indicateurs internes sont recalculés périodiquement par un service en arrière-plan ; voir [§ Pilotage automatique](README.md#pilotage-et-calculs-automatiques) du module.

## Sous-entité : `IndicatorMeasurement`

`context.models.indicator.IndicatorMeasurement`

Une mesure historique d'un indicateur. Plusieurs mesures par indicateur, indexées par date, alimentent les sparklines et l'évolution.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | Identifiant unique |
| `indicator` | relation | FK → Indicator, requis | Indicateur mesuré |
| `value` | string | requis, max 255 | Valeur mesurée (nombre ou booléen sérialisé en chaîne) |
| `recorded_at` | datetime | défaut `now`, indexé | Horodatage de la mesure. Modifiable, ce qui permet d'importer des séries historiques |
| `recorded_by` | relation | FK → User, optionnel | Auteur de la mesure |
| `notes` | text | optionnel | Commentaire libre (méthodologie, événement contextuel) |

Le `current_value` de l'indicateur est mis à jour automatiquement à la création de chaque `IndicatorMeasurement` avec la valeur de la mesure la plus récente.

## Règles de gestion spécifiques

| ID | Règle |
|---|---|
| RS-IND-01 | Un indicateur prédéfini (`is_internal=true`) doit avoir `indicator_type=organizational`. |
| RS-IND-02 | Un indicateur prédéfini doit renseigner `internal_source` ; ses `format` et `unit` sont alignés sur `PREDEFINED_SOURCE_FORMAT`. |
| RS-IND-03 | Un indicateur de `format=boolean` ne peut pas avoir d'`unit`. |
| RS-IND-04 | Un indicateur de `format=boolean` n'utilise que `is_true` ou `is_false` comme `critical_threshold_operator`. |
| RS-IND-05 | Un indicateur de `format=number` n'utilise que `below` ou `above` comme `critical_threshold_operator`. |
| RS-IND-06 | `critical_threshold_min` et `critical_threshold_max` sont réservés au `format=number`. Si les deux sont renseignés, `min < max`. |
| RS-IND-07 | À la création, `first_review_date` doit être aujourd'hui ou ultérieure. |
| RS-IND-08 | À chaque création d'`IndicatorMeasurement`, `Indicator.current_value` est mis à jour avec la valeur de la nouvelle mesure. |

## État critique (`is_critical`)

Propriété calculée à la lecture, vraie quand :

- `format=boolean` et `current_value` viole l'opérateur configuré (`is_true` → valeur fausse, `is_false` → valeur vraie) ;
- `format=number` et `current_value < critical_threshold_min` ou `current_value > critical_threshold_max` ;
- `critical_threshold_operator=below` et `current_value < critical_threshold_value` ;
- `critical_threshold_operator=above` et `current_value > critical_threshold_value`.

Un indicateur critique s'affiche avec une bordure rouge sur le tableau de bord et apparaît dans les notifications hebdomadaires.

## Endpoints

### REST

- `GET /api/v1/context/indicators/` : liste avec filtres `indicator_type`, `status`, `format`, `collection_method`, `is_internal`
- `POST /api/v1/context/indicators/`
- `GET /api/v1/context/indicators/<uuid>/`
- `PUT/PATCH /api/v1/context/indicators/<uuid>/`
- `DELETE /api/v1/context/indicators/<uuid>/`
- `POST /api/v1/context/indicators/<uuid>/approve/`
- `GET /api/v1/context/indicators/<uuid>/measurements/` : historique des mesures
- `POST /api/v1/context/indicators/<uuid>/measurements/` : nouvelle mesure
- `POST /api/v1/context/indicators/batch/` : création en lot

### MCP

- `list_indicators` / `get_indicator` / `create_indicator` / `update_indicator` / `delete_indicator` / `approve_indicator` / `batch_create_indicators`
- `list_indicator_measurements` / `create_indicator_measurement` / `batch_create_indicator_measurements`

## Permissions

| Codename | Description |
|---|---|
| `context.indicator.read` | Lire les indicateurs et leurs mesures |
| `context.indicator.create` | Créer un indicateur et ses mesures |
| `context.indicator.update` | Modifier un indicateur |
| `context.indicator.delete` | Supprimer un indicateur |
| `context.indicator.approve` | Approuver un indicateur |

## Références

- ISO/IEC 27001:2022 §6.2 (Objectifs de sécurité et mesurabilité) et §9.1 (Surveillance, mesure, analyse, évaluation)
- [Objective](objective.md), [Requirement](../m3-compliance/requirement.md) : entités cibles des liens M2M
- [Indicator MCP tools](https://github.com/frousselet/open-grc/blob/main/mcp/tools.py) : implémentation
