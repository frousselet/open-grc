# SwotAnalysis

`context.models.swot.SwotAnalysis`

Représente une analyse SWOT réalisée pour un périmètre donné.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `scope_id` | relation | FK → Scope, requis | Périmètre rattaché |
| `name` | string | requis, max 255 | Intitulé de l'analyse |
| `description` | text | optionnel | Contexte de l'analyse |
| `analysis_date` | date | requis | Date de réalisation |
| `workflow_state` | enum | requis, défaut `draft` | Cycle de vie unifié : `draft`, `pending`, `validated`, `archived`. Voir [governance/workflow.md](../governance/workflow.md). |
| `validated_by` | relation | FK → User | Validateur |
| `validated_at` | datetime | optionnel | Date de validation |
| `items` | relation | O2M → SwotItem | Éléments SWOT |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

## SwotItem

Sous-entité : élément SWOT.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `swot_analysis_id` | relation | FK → SwotAnalysis, requis | Analyse parente |
| `quadrant` | enum | requis | `strength`, `weakness`, `opportunity`, `threat` |
| `description` | text | requis | Description de l'élément |
| `impact_level` | enum | requis | `low`, `medium`, `high` |
| `related_issues` | relation | M2M → Issue | Enjeux associés |
| `related_objectives` | relation | M2M → Objective | Objectifs associés |
| `order` | integer | requis | Ordre d'affichage dans le quadrant |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
