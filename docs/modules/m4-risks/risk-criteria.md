# RiskCriteria

`risks.models.risk_criteria.RiskCriteria`

Échelles, matrice et seuils d'acceptation utilisés pour une appréciation des risques. Réutilisable entre plusieurs appréciations.

## 2.2 Entité : RiskCriteria (Critères de risque)

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
| `workflow_state` | enum | requis, défaut `draft` | Cycle de vie unifié : `draft`, `pending`, `validated`, `archived`. Voir [governance/workflow.md](../governance/workflow.md). |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

## ScaleLevel

`risks.models.risk_criteria.ScaleLevel`

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

## RiskLevel

`risks.models.risk_criteria.RiskLevel`

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
