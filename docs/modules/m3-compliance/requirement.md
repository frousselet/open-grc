# Requirement

`compliance.models.requirement.Requirement`

Exigence individuelle extraite d'un [Framework](framework.md), unité élémentaire d'évaluation de la conformité.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `framework_id` | relation | FK -> Framework, requis | Référentiel parent |
| `section_id` | relation | FK -> Section, optionnel | Section de rattachement |
| `requirement_number` | string | optionnel, max 100 | Numéro / référence métier de l'exigence (ex. « A.5.1.1 », « Art. 32.1.a »). Unique par framework quand renseigné. |
| `reference` | string | auto-généré `REQT-N`, unique | Référence interne |
| `name` | string | requis, max 500 | Intitulé court de l'exigence |
| `description` | text | requis | Texte complet de l'exigence |
| `guidance` | text | optionnel | Recommandations de mise en œuvre / notes d'interprétation |
| `type` | enum | requis | `mandatory`, `recommended`, `optional` |
| `category` | enum | optionnel | `organizational`, `technical`, `physical`, `legal`, `human`, `other` |
| `is_applicable` | boolean | requis, défaut `true` | Applicable au périmètre |
| `applicability_justification` | text | optionnel | Justification de la non-applicabilité (DdA) |
| `compliance_status` | enum | requis, défaut `not_assessed` | Voir la section « Statuts de conformité » ci-dessous |
| `compliance_level` | integer | défaut 0, 0-100 | Niveau de conformité (%). Propagé depuis les `AssessmentResult` par `assessment.recalculate_counts()` |
| `compliance_evidence` | text | optionnel | Preuves / éléments de conformité |
| `compliance_finding` | text | optionnel | Constat d'audit / écarts (anciennement `compliance_gaps` dans la spec d'origine, renommé pour s'aligner sur le vocabulaire audit du module Audits) |
| `last_assessment_date` | date | optionnel | Date de la dernière évaluation |
| `last_assessed_by` | relation | FK -> User, optionnel | Dernier évaluateur |
| `owner_id` | relation | FK -> User, optionnel | Responsable de la mise en conformité |
| `priority` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `target_date` | date | optionnel | Date cible de mise en conformité |
| `linked_assets` | relation | M2M -> EssentialAsset | Biens essentiels concernés |
| `linked_stakeholder_expectations` | relation | M2M -> StakeholderExpectation | Attentes de parties intéressées associées |
| `linked_risks` | reverse M2M | -> Risk via `Risk.linked_requirements` | Risques associés (alimenté côté Risk) |
| `mapped_requirements` | relation | M2M via [`RequirementMapping`](requirement-mapping.md) | Exigences d'autres référentiels mappées |
| `status` | enum | requis, défaut `active` | `active`, `deprecated`, `superseded` |
| `is_approved` / `approved_by` / `approved_at` | bool / FK -> User / datetime | optionnel | Workflow d'approbation standard |
| `version` | int | auto-incrémenté | Bumpé à chaque modification majeure |
| `tags` | relation | M2M -> Tag | |
| `created_by` | relation | FK -> User | Créateur |
| `created_at` / `updated_at` | datetime | auto | |

> Contrainte d'unicité : `(framework_id, requirement_number)` quand `requirement_number` est non vide.

## Statuts de conformité

L'énumération `compliance_status` réunit deux familles de valeurs : les statuts de conformité simples (les 5 de la spec ISO d'origine) et les statuts d'audit (issus du module Audits, ISO 19011 et conventions ISMS internes). Les deux familles cohabitent volontairement dans la même énumération : un audit produit un constat avec un statut d'audit, et ce statut sert directement de `compliance_status` sur l'exigence évaluée via le report RC-06. Avoir deux énumérations à maintenir en miroir générait de la friction (double saisie, table de mapping interne, statut audit invisible en dehors des audits) ; une seule énumération sert les deux modules.

### Statuts de conformité simples

| Valeur | Sens |
|---|---|
| `not_assessed` | Exigence pas encore évaluée. Valeur par défaut à la création |
| `non_compliant` | Non conforme. Déclenche RC-05 (alerte réglementaire si le framework est `is_mandatory`) |
| `partially_compliant` | Partiellement conforme. La part conforme est capturée par `compliance_level` |
| `compliant` | Conforme |
| `not_applicable` | Non applicable au périmètre. Exclue des moyennes RC-01 / RC-02 (cf. CHANGELOG ISO 27001 SoA) |

### Statuts d'audit

Issus du module Audits. Permettent un `compliance_status` plus précis quand l'évaluation est conduite dans le cadre d'un audit formel.

| Valeur | Sens | Mapping conformité implicite |
|---|---|---|
| `evaluated` | Évaluation planifiée mais non encore conclue (placeholder). Traitée comme `not_assessed` dans les agrégats, avec fallback sur l'évaluation précédente. | `not_assessed` (placeholder) |
| `major_non_conformity` | Non-conformité majeure (manquement systémique ISO 19011). Alerte critique. | `non_compliant` |
| `minor_non_conformity` | Non-conformité mineure (manquement ponctuel). | `partially_compliant` |
| `observation` | Observation neutre, pas de manquement constaté mais point d'attention. | `compliant` |
| `improvement_opportunity` | Opportunité d'amélioration. Pas de non-conformité, suggestion d'optimisation. | `compliant` |
| `strength` | Point fort relevé par l'auditeur. | `compliant` |

Le mapping implicite (colonne de droite) sert au calcul du `compliance_level` agrégé et aux compteurs des tableaux de bord : un statut `major_non_conformity` contribue au taux de non-conformité, un `strength` contribue au taux de conformité.

## Effet de chaque statut sur les calculs

### RC-01 (niveau global d'un framework)

`Framework.recalculate_compliance` lit le `compliance_status` et `compliance_level` directement sur chaque `Requirement` applicable :

- `not_applicable` est exclu (numérateur et dénominateur, convention SoA).
- `not_assessed` et `evaluated` comptent comme `compliance_level = 0` (sauf fallback géré par `recalculate_counts` qui injecte la dernière évaluation utile).
- Les autres statuts contribuent leur `compliance_level` (0-100).

### RC-02 (niveau d'une section)

Identique à RC-01, scoped à la section. Inclut récursivement les sous-sections : la moyenne de la section parente intègre les niveaux des enfants.

### RC-04 (alerte « non révisé »)

Une exigence `compliant` qui n'a pas eu de `last_assessment_date` depuis plus de N jours (configurable, défaut 365) est listée dans le panneau « Conformité périmée ». Les statuts d'audit `observation`, `improvement_opportunity` et `strength` participent à RC-04 au même titre que `compliant` (ils sont mappés conforme).

### RC-05 (alerte réglementaire)

Une exigence `non_compliant` ou `major_non_conformity` ou `minor_non_conformity` sur un framework `is_mandatory=true` déclenche l'alerte critique de non-conformité réglementaire. `partially_compliant` produit une alerte de niveau warning.

### RC-06 (report résultat d'audit -> exigence)

À la fermeture d'une évaluation (`ComplianceAssessment.recalculate_counts`), chaque `AssessmentResult` propage son `compliance_status` et `compliance_level` à l'exigence ciblée. Les résultats `not_assessed` ne sont pas reportés (cf. #45 résolu) : c'est la valeur antérieure de l'exigence qui est conservée. Le résultat `evaluated` est résolu via fallback sur la dernière évaluation effective.

## Articulation avec le module Audits

Le module Audits (`audits/` côté code) produit des `Finding` (constats) liés à des `ComplianceAssessment`. Le type d'un finding (`finding_type` : `compliant`, `non_compliant`, `partially_compliant`, `major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`, `not_applicable`) est la même énumération que `compliance_status` côté Requirement et `compliance_status` côté AssessmentResult, ce qui élimine la friction de mapping entre les deux modules. Quand un finding est attaché à un `AssessmentResult` et que la méthode `apply_findings_to_results()` est appelée, le `compliance_status` du résultat est aligné sur le statut le plus sévère parmi les findings rattachés (selon `FINDING_SEVERITY_ORDER` défini dans `compliance.constants`).

## Règles de gestion

| ID | Règle |
|---|---|
| RG-REQ-01 | `(framework_id, requirement_number)` est unique quand `requirement_number` est non vide. |
| RG-REQ-02 | Modifier le `compliance_status` ou le `compliance_level` d'une exigence directement déclenche le signal `post_save` qui rafraîchit la section porteuse, ses ancêtres et le framework (issue #41 résolue). |
| RG-REQ-03 | `is_applicable=false` doit s'accompagner d'une `applicability_justification` non vide ; cette règle est documentée mais non bloquante au niveau modèle (vérifiée à l'UI). |
| RG-REQ-04 | Lors du report RC-06, un résultat `not_assessed` ne réécrit pas le `compliance_status` existant (préservation des évaluations antérieures, issue #45 résolue). |
| RG-REQ-05 | `compliance_finding` est le nom canonique du champ (ancien `compliance_gaps` de la spec d'origine, renommé pour s'aligner sur le vocabulaire audit). |
