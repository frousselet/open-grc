# Scope

`context.models.scope.Scope`

Représente le périmètre couvert par le dispositif GRC.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `name` | string | requis, max 255 | Nom du périmètre |
| `description` | text | requis | Description détaillée du périmètre |
| `version` | string | requis | Version du document de périmètre |
| `workflow_state` | enum | requis, défaut `draft` | Cycle de vie unifié : `draft`, `pending`, `validated`, `archived`. Voir [governance/workflow.md](../governance/workflow.md). |
| `boundaries` | text | optionnel | Limites et exclusions du périmètre |
| `justification_exclusions` | text | optionnel | Justification des exclusions |
| `geographic_scope` | text | optionnel | Périmètre géographique |
| `organizational_scope` | text | optionnel | Périmètre organisationnel |
| `technical_scope` | text | optionnel | Périmètre technique |
| `applicable_standards` | relation | M2M → Referential | Référentiels applicables |
| `approved_by` | relation | FK → User | Approbateur |
| `approved_at` | datetime | optionnel | Date d'approbation |
| `effective_date` | date | optionnel | Date d'entrée en vigueur |
| `review_date` | date | optionnel | Prochaine date de revue |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |
