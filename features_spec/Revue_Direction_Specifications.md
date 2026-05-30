# Revue de direction — Conformité ISO 27001:2022 (clause 9.3)

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 17 avril 2026
**Statut :** Draft
**Module concerné :** `reports` (transverse : context, compliance, risks, accounts)

---

## 1. Présentation générale

### 1.1 Objectif

Doter Cairn d'un processus complet de **revue de direction** conforme à la clause 9.3 de l'ISO 27001:2022. L'état actuel se limite à un **export ponctuel** (PPTX + DOCX) agrégeant les entrées de la clause 9.3.2. Cette spécification ajoute les éléments manquants pour produire des revues de direction **auditables, persistantes et traçables** :

- un cycle de vie complet de la revue (préparation, tenue, clôture)
- la capture structurée des **décisions** et **changements SMSI** exigés par la clause 9.3.3
- la **traçabilité revue-à-revue** (suivi des actions issues des revues précédentes)
- la formalisation des **retours des parties intéressées** (clause 9.3.2.e)
- la **tendance des mesures** (clause 9.3.2.d.2) via l'exploitation de `IndicatorMeasurement`

### 1.2 Périmètre fonctionnel

Le module couvre six sous-domaines :

1. **Revues de direction** (cycle de vie complet : entité persistante `ManagementReview`)
2. **Décisions** issues d'une revue (entité `ManagementReviewDecision`)
3. **Changements SMSI** identifiés (entité `IsmsChange`)
4. **Retours des parties intéressées** (entité `StakeholderFeedback`)
5. **Export enrichi** (PPTX/DOCX) consommant les données persistantes
6. **Rétrochaînage** des plans d'actions, plans de traitement des risques et objectifs vers la revue décisionnaire

### 1.3 Mapping exhaustif ISO 27001:2022 clause 9.3

| Clause | Exigence | Couverture actuelle | Couverture cible |
|---|---|---|---|
| 9.3.1 | Planification de la revue | Manquante | `ManagementReview.planned_date`, `frequency`, rappels |
| 9.3.2.a | Actions des revues précédentes | Partielle (plans d'actions listés) | FK `originating_review` sur actions + tableau de suivi |
| 9.3.2.b | Enjeux externes/internes | Complète | Inchangée |
| 9.3.2.c | Besoins/attentes des parties intéressées | Complète | Inchangée |
| 9.3.2.d.1 | Non-conformités et actions correctives | Complète | Inchangée |
| 9.3.2.d.2 | Surveillance et mesurage | Partielle (valeur courante) | Tendance via `IndicatorMeasurement` |
| 9.3.2.d.3 | Résultats d'audit | Complète | Inchangée |
| 9.3.2.d.4 | Atteinte des objectifs SSI | Complète | Inchangée |
| 9.3.2.e | Retours des parties intéressées | Partielle (attentes) | Nouvelle entité `StakeholderFeedback` |
| 9.3.2.f | Résultats d'appréciation et plan de traitement | Complète | Inchangée |
| 9.3.2.g | Opportunités d'amélioration | Partielle (constats d'audit) | Saisie libre dans la revue + constats |
| 9.3.3 | Sorties (décisions, changements SMSI) | Manquante (placeholder) | `ManagementReviewDecision` + `IsmsChange` |

### 1.4 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| `accounts` | Revue ≠ limitée au créateur : participants multiples, rédacteur, approbateur. Permissions `reports.management_review.*`. |
| `context` | Indicateurs (tendance), objectifs, enjeux, parties intéressées, retours. |
| `compliance` | Plans d'actions, constats, audits, référentiels — rétrochaînés à une revue. |
| `risks` | Appréciations, risques critiques, plans de traitement — rétrochaînés à une revue. |
| `reports` | Génération des exports PPTX/DOCX enrichis. |
| `mcp` | Exposition des revues, décisions, retours, changements SMSI. |

---

## 2. Modèle de données

### 2.1 Entité : `ManagementReview` (Revue de direction)

Représente une revue de direction planifiée ou tenue. Objet racine persistant qui remplace le fonctionnement "export éphémère" actuel.

Fichier : `reports/models/management_review.py`

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto (préfixe `MRVW`), unique | Référence séquentielle (ex. `MRVW-1`) |
| `title` | string | requis, max 255 | Intitulé (ex. « Revue de direction annuelle 2026 ») |
| `description` | text | optionnel | Contexte, objet de la revue |
| `scopes` | relation | M2M → Scope, au moins 1 | Périmètres couverts par la revue |
| `frequency` | enum | requis | `quarterly`, `semiannual`, `annual`, `exceptional` |
| `period_start` | date | requis | Début de la période examinée |
| `period_end` | date | requis | Fin de la période examinée |
| `planned_date` | date | requis | Date planifiée de la revue |
| `held_date` | date | optionnel | Date effective de tenue |
| `location` | string | optionnel, max 255 | Lieu (physique ou visio) |
| `status` | enum | requis | `planned`, `in_preparation`, `held`, `closed`, `cancelled` |
| `facilitator` | FK → User | requis | Animateur / rédacteur |
| `approver` | FK → User | optionnel | Approbateur (typiquement direction) |
| `approved_at` | datetime | optionnel | Date d'approbation |
| `next_review_date` | date | optionnel | Date prévue de la prochaine revue |
| `summary` | text | optionnel | Synthèse exécutive rédigée par l'animateur |
| `agenda` | text | optionnel | Ordre du jour (HTML rich text) |
| `minutes` | text | optionnel | Compte rendu détaillé (HTML rich text) |
| `snapshot_data` | JSONField | optionnel | Snapshot des données agrégées au moment de la clôture (pour geler l'auditabilité) |
| `created_by` | FK → User | auto | Créateur |
| `created_at`, `updated_at` | datetime | auto | Traçabilité |
| `tags` | M2M → Tag | optionnel | Étiquetage libre |

**Historique** : `django-simple-history` (`HistoricalRecords`) pour audit-trail.

**Cycle de vie (workflow)** :

```
planned ─► in_preparation ─► held ─► closed
       └──────────────────────────► cancelled
```

Transitions :

- `planned → in_preparation` : l'animateur verrouille l'ordre du jour et déclenche la collecte des données.
- `in_preparation → held` : sur saisie de `held_date`. Les données entrées de clause 9.3.2 sont gelées dans `snapshot_data`.
- `held → closed` : toutes les décisions doivent avoir un responsable et une échéance ; le statut bascule si `approver` valide. Capture `approved_at`.
- `* → cancelled` : motif obligatoire, stocké via commentaire (cf. 2.6).

L'UI doit utiliser le **stepper horizontal** décrit dans `CLAUDE.md` (cf. `compliance/templates/compliance/assessment_detail.html`).

### 2.2 Entité : `ManagementReviewParticipant`

Table de liaison enrichie entre `ManagementReview` et `User` (participants internes ou externes).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `review` | FK → ManagementReview | requis, `on_delete=CASCADE` | Revue parente |
| `user` | FK → User | optionnel | Participant interne (null pour externes) |
| `external_name` | string | max 255, optionnel | Nom en clair pour participant externe |
| `external_role` | string | max 255, optionnel | Fonction en clair pour participant externe |
| `role` | enum | requis | `facilitator`, `decision_maker`, `contributor`, `observer` |
| `attended` | boolean | défaut false | A assisté à la réunion |
| `signature_data` | text | optionnel | Signature (base64 PNG ou texte) pour le DOCX |

> Contrainte : `user` ou (`external_name` + `external_role`) doit être renseigné (`CheckConstraint`).

### 2.3 Entité : `ManagementReviewDecision` (Décision)

Capture structurée des décisions exigées par la clause 9.3.3. Sert à produire le bloc « Décisions » du compte rendu et alimente automatiquement les plans d'actions.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (préfixe `DECS`), unique | ex. `DECS-1` |
| `review` | FK → ManagementReview | requis, CASCADE | Revue d'origine |
| `category` | enum | requis | `improvement`, `isms_change`, `resource_allocation`, `risk_acceptance`, `objective_adjustment`, `policy_update`, `other` |
| `input_clause` | enum | optionnel | Entrée 9.3.2 à laquelle se rattache la décision (`a`–`g`) |
| `title` | string | requis, max 255 | Intitulé synthétique |
| `description` | text | requis | Texte complet de la décision |
| `rationale` | text | optionnel | Justification, éléments de contexte |
| `owner` | FK → User | requis | Responsable de la mise en œuvre |
| `due_date` | date | requis | Échéance |
| `priority` | enum | requis | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `pending`, `in_progress`, `implemented`, `cancelled` |
| `implemented_at` | date | optionnel | Date de mise en œuvre effective |
| `implementation_evidence` | text | optionnel | Preuve (lien vers document, URL) |
| `linked_action_plan` | FK → ComplianceActionPlan | optionnel, SET_NULL | Plan d'action généré depuis cette décision |
| `linked_treatment_plan` | FK → RiskTreatmentPlan | optionnel, SET_NULL | Plan de traitement généré |
| `linked_objective` | FK → Objective | optionnel, SET_NULL | Objectif SSI créé/ajusté |
| `linked_isms_change` | FK → IsmsChange | optionnel, SET_NULL | Changement SMSI associé |
| `created_at`, `updated_at` | datetime | auto | |

**Historique** : `HistoricalRecords`.

**Règles de gestion** :

- Une revue ne peut passer en `closed` que si **toutes ses décisions** ont `owner` ET `due_date` renseignés.
- Lorsqu'une décision passe à `implemented`, si `linked_action_plan` est renseigné, son statut doit être `CLOSED` ou `VALIDATED` (garde-fou métier, avertissement UI non bloquant).
- Une action « Créer un plan d'action depuis cette décision » génère un `ComplianceActionPlan` pré-rempli et renseigne `linked_action_plan` + `originating_review` (cf. §2.9).

### 2.4 Entité : `IsmsChange` (Changement SMSI)

Exigence 9.3.3 : « toute nécessité de modifier le SMSI ». Formalisation des changements décidés en revue.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (préfixe `ICHG`), unique | ex. `ICHG-1` |
| `review` | FK → ManagementReview | requis, CASCADE | Revue d'origine |
| `change_type` | enum | requis | `scope`, `policy`, `control`, `organization`, `resource`, `process`, `other` |
| `title` | string | requis, max 255 | Intitulé |
| `description` | text | requis | Description du changement |
| `impact_analysis` | text | optionnel | Analyse d'impact (PI, risques, actifs) |
| `affected_scopes` | M2M → Scope | optionnel | Périmètres impactés |
| `affected_frameworks` | M2M → Framework | optionnel | Référentiels impactés |
| `affected_policies` | text | optionnel | Liste des politiques à réviser (texte libre, évolution future vers un modèle `Policy`) |
| `status` | enum | requis | `proposed`, `approved`, `in_progress`, `implemented`, `rejected` |
| `owner` | FK → User | requis | Responsable de mise en œuvre |
| `target_date` | date | optionnel | Date cible |
| `implemented_at` | date | optionnel | Date de mise en œuvre effective |
| `created_at`, `updated_at` | datetime | auto | |

**Historique** : `HistoricalRecords`.

### 2.5 Entité : `StakeholderFeedback` (Retour de partie intéressée)

Formalisation du canal de feedback exigé par la clause 9.3.2.e (distinct des attentes `StakeholderExpectation`, qui sont des exigences permanentes).

Fichier : `context/models/stakeholder_feedback.py`

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto (préfixe `FBCK`), unique | ex. `FBCK-1` |
| `stakeholder` | FK → Stakeholder | requis, CASCADE | Partie intéressée émettrice |
| `channel` | enum | requis | `survey`, `meeting`, `complaint`, `email`, `audit`, `incident`, `other` |
| `received_date` | date | requis | Date de réception |
| `subject` | string | requis, max 255 | Objet du retour |
| `content` | text | requis | Contenu détaillé (HTML rich text) |
| `sentiment` | enum | optionnel | `positive`, `neutral`, `negative`, `mixed` |
| `severity` | enum | optionnel | `low`, `medium`, `high`, `critical` |
| `status` | enum | requis | `new`, `under_review`, `addressed`, `closed` |
| `response` | text | optionnel | Réponse apportée |
| `linked_issues` | M2M → Issue | optionnel | Enjeux associés |
| `linked_expectations` | M2M → StakeholderExpectation | optionnel | Attentes renforcées |
| `scopes` | M2M → Scope | requis, au moins 1 | Périmètres concernés |
| `created_by`, `created_at`, `updated_at` | auto | | Traçabilité |

**Historique** : `HistoricalRecords`.

**Agrégation en revue** : la section 5 de l'export devient :
- tableau des `StakeholderFeedback` sur la période (priorité aux `negative` + `critical`)
- plus la vue actuelle des attentes applicables (inchangée).

### 2.6 Entité : `ManagementReviewComment`

Fil de discussion attaché à une revue (utile pour arbitrage pré-réunion, justification d'annulation, etc.).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `review` | FK → ManagementReview | requis, CASCADE | |
| `author` | FK → User | requis, SET_NULL | |
| `content` | text | requis | HTML rich text |
| `created_at` | datetime | auto | |

Pattern identique à `ComplianceActionPlanComment`.

### 2.7 Entité : `ManagementReviewTransition`

Journal des transitions de statut, aligné sur `ComplianceActionPlanTransition`.

| Champ | Type | Description |
|---|---|---|
| `id` | UUID | PK |
| `review` | FK → ManagementReview | CASCADE |
| `from_status`, `to_status` | enum | - |
| `user` | FK → User | Auteur |
| `comment` | text | Commentaire obligatoire pour `cancelled` |
| `created_at` | datetime | auto |

### 2.8 Extension de `Indicator` / `IndicatorMeasurement`

**Aucun changement de modèle**. `IndicatorMeasurement` existe déjà (`context/models/indicator.py:352`). La spec impose uniquement d'exploiter ces mesures côté export :

- Calcul de la tendance sur la période de revue : comparaison de la **moyenne des mesures** `period_start → period_end` vs. la période précédente équivalente.
- Marqueur `trend` calculé : `improving`, `stable`, `degrading`, `insufficient_data` (< 2 mesures).
- Calcul du **respect de la fréquence** : nombre attendu de mesures sur la période (selon `review_frequency`) vs. nombre réel. Remonté en `measurement_compliance_pct`.

### 2.9 Modifications de modèles existants

Ajout de clés étrangères de **rétrochaînage** (nullable, `SET_NULL`). Permet de répondre au 9.3.2.a et de tracer l'origine décisionnelle.

| Modèle | Nouveau champ | Type | Rôle |
|---|---|---|---|
| `compliance.ComplianceActionPlan` | `originating_review` | FK → ManagementReview, null=True | Revue d'origine |
| `compliance.ComplianceActionPlan` | `originating_decision` | FK → ManagementReviewDecision, null=True | Décision source |
| `risks.RiskTreatmentPlan` | `originating_review` | FK → ManagementReview, null=True | Revue d'origine |
| `risks.RiskTreatmentPlan` | `originating_decision` | FK → ManagementReviewDecision, null=True | Décision source |
| `context.Objective` | `originating_review` | FK → ManagementReview, null=True | Revue d'origine |
| `context.Objective` | `originating_decision` | FK → ManagementReviewDecision, null=True | Décision source |

Aucune suppression. Les migrations sont additives et rétro-compatibles (tous les champs nullables).

---

## 3. Vues et parcours utilisateur

### 3.1 URL patterns

Fichier : `reports/urls.py`

```
/reports/management-reviews/                    → ManagementReviewListView
/reports/management-reviews/create/             → ManagementReviewCreateView
/reports/management-reviews/<uuid:pk>/          → ManagementReviewDetailView
/reports/management-reviews/<uuid:pk>/edit/     → ManagementReviewUpdateView
/reports/management-reviews/<uuid:pk>/delete/   → ManagementReviewDeleteView
/reports/management-reviews/<uuid:pk>/transition/   → ManagementReviewTransitionView
/reports/management-reviews/<uuid:pk>/export/pptx/  → ManagementReviewExportPptxView
/reports/management-reviews/<uuid:pk>/export/docx/  → ManagementReviewExportDocxView
/reports/management-reviews/<uuid:pk>/snapshot/     → ManagementReviewSnapshotView (POST)

/reports/management-reviews/<uuid:pk>/decisions/create/ → DecisionCreateView
/reports/decisions/<uuid:pk>/                           → DecisionDetailView
/reports/decisions/<uuid:pk>/edit/                      → DecisionUpdateView
/reports/decisions/<uuid:pk>/promote/                   → DecisionPromoteView (crée un ActionPlan)

/reports/management-reviews/<uuid:pk>/isms-changes/create/ → IsmsChangeCreateView
/reports/isms-changes/<uuid:pk>/                           → IsmsChangeDetailView

/context/stakeholder-feedback/                   → StakeholderFeedbackListView
/context/stakeholder-feedback/create/            → StakeholderFeedbackCreateView
/context/stakeholder-feedback/<uuid:pk>/         → StakeholderFeedbackDetailView
```

### 3.2 Page de détail `ManagementReviewDetailView`

Pattern **2 colonnes, pas d'onglets** (cf. `CLAUDE.md` : prefer 2-column card layout). Stepper de statut en haut, sticky sidebar à droite.

**Sidebar (colonne droite, sticky)** :

- Badge de statut (stepper miniature)
- Animateur, approbateur
- Période de revue (`period_start` → `period_end`)
- Date planifiée / tenue
- Participants (liste avec rôles et pastille « présent »)
- Prochaine revue
- Boutons : Exporter PPTX, Exporter DOCX, Ajouter une décision, Ajouter un changement SMSI

**Colonne principale** : sections `<details>` repliables, chacune correspondant à une entrée de 9.3.2 :

1. **9.3.2.a Actions des revues précédentes** — tableau des décisions `pending`/`in_progress` issues de revues antérieures, avec statut et échéance.
2. **9.3.2.b Enjeux** — internes/externes (utilise `Issue` filtré sur la période).
3. **9.3.2.c Attentes des parties intéressées** — utilise `StakeholderExpectation` filtré.
4. **9.3.2.d.1 Non-conformités** — utilise `Finding`.
5. **9.3.2.d.2 Surveillance et mesurage** — tableau avec **colonne « Tendance »** (🔺 amélioration, = stable, 🔻 dégradation) et **« Conformité fréquence »**.
6. **9.3.2.d.3 Audits** — utilise `ComplianceAssessment`.
7. **9.3.2.d.4 Objectifs** — utilise `Objective`.
8. **9.3.2.e Retours des PI** — nouvelle section consommant `StakeholderFeedback`.
9. **9.3.2.f Risques et plan de traitement** — synthèse + risques critiques.
10. **9.3.2.g Opportunités d'amélioration** — constats type `IMPROVEMENT_OPPORTUNITY` + champ texte libre `summary`.
11. **Décisions (sortie 9.3.3)** — tableau éditable, actions inline « Promouvoir en plan d'action ».
12. **Changements SMSI (sortie 9.3.3)** — liste des `IsmsChange`.
13. **Synthèse et prochaine revue** — `summary`, `next_review_date`.
14. **Commentaires** — fil (`ManagementReviewComment`).
15. **Historique** — `HistoricalRecords` de la revue et de ses décisions.

### 3.3 Formulaires

- `ManagementReviewForm` — création/édition (title, description, scopes, frequency, period_start, period_end, planned_date, location, facilitator, approver, next_review_date, agenda, summary, tags).
- `ManagementReviewParticipantFormSet` — gestion inline des participants.
- `ManagementReviewTransitionForm` — statut cible + commentaire (obligatoire si `cancelled`).
- `ManagementReviewDecisionForm` — tous les champs §2.3.
- `IsmsChangeForm` — tous les champs §2.4.
- `StakeholderFeedbackForm` — tous les champs §2.5.
- `DecisionPromoteForm` — modal générant un `ComplianceActionPlan` pré-rempli depuis une décision.

### 3.4 Liste `ManagementReviewListView`

- `SortableListMixin` (tri persisté par utilisateur)
- Colonnes : Référence, Titre, Période, Planifiée le, Statut, Animateur, Décisions (count), Scopes
- Filtres : statut, année, scope, animateur
- Badges de statut colorés
- Recherche plein texte sur `title`, `description`, `reference`

### 3.5 Snapshot et gel auditabilité

À la transition `held → closed`, le bouton **« Clôturer la revue »** exécute :

1. Génération `gather_management_review_data(...)` avec `period_start`/`period_end` de la revue.
2. Sérialisation du résultat dans `ManagementReview.snapshot_data` (JSONField).
3. Les exports ultérieurs consomment **en priorité** `snapshot_data` si non vide. L'UI affiche un badge « Données figées le DD/MM/YYYY » pour signaler l'immuabilité.

Rationale : une revue clôturée ne doit plus varier avec le temps (exigence d'auditabilité). Les données live continuent d'évoluer mais ne modifient pas le compte rendu approuvé.

---

## 4. Exports PPTX et DOCX enrichis

### 4.1 Source des données

Fichier : `reports/management_review.py` — refactoring de `gather_management_review_data` en **deux modes** :

- `gather_live(...)` : mode actuel, agrégation live (pour revues `planned`/`in_preparation`/`held`).
- `gather_from_snapshot(review)` : rehydrate depuis `snapshot_data` (pour revues `closed`).

Signature enrichie :
```python
gather_management_review_data(
    user,
    review=None,              # nouveau : ManagementReview, prioritaire
    scope_ids=None,
    period_start=None,
    period_end=None,
)
```

Si `review` est fourni :
- `scope_ids`, `period_start`, `period_end` en sont déduits.
- Si `review.status == closed`, snapshot utilisé.
- Les sections 11 (décisions) et 12 (changements SMSI) sont ajoutées.
- Participants injectés dans la page de garde DOCX et la slide de titre PPTX.

### 4.2 Ajouts dans l'export

**Section 4b (mesurage)** — nouvelles colonnes :

| Ref. | Indicateur | Valeur actuelle | Valeur précédente | Tendance | Cible | Conf. fréquence |
|---|---|---|---|---|---|---|

**Section 5 (retours PI)** — deux blocs :
- Tableau `StakeholderFeedback` (canal, sujet, sentiment, sévérité, statut)
- Tableau existant des attentes applicables

**Section 9.3.3 (sorties)** — nouvelles slides / sections DOCX :

- **Décisions prises** — tableau (référence, catégorie, titre, responsable, échéance, priorité, statut)
- **Changements SMSI** — tableau (référence, type, titre, responsable, statut, cible)
- **Synthèse exécutive** — insertion de `review.summary` (rich text stripé)
- **Prochaine revue** — `review.next_review_date`

**Page de signatures (DOCX)** — remplacer la table vide actuelle par une table pré-remplie avec les participants (nom, fonction, case signature). Si `signature_data` contient une image base64, l'intégrer.

### 4.3 Placeholders `[A completer]`

Suppression complète. Les données sont désormais saisies dans l'UI avant l'export et injectées à partir de la revue persistée.

---

## 5. API REST

Fichier : `reports/api/urls.py`, `reports/api/serializers.py`, `reports/api/views.py`.

Base URL : `/api/v1/reports/`

### 5.1 Endpoints

| Méthode | URL | Action |
|---|---|---|
| GET/POST | `/management-reviews/` | Liste / création |
| GET/PATCH/DELETE | `/management-reviews/<id>/` | Détail, mise à jour partielle, suppression |
| POST | `/management-reviews/<id>/transition/` | Transition de statut `{to_status, comment}` |
| POST | `/management-reviews/<id>/close/` | Clôture (déclenche snapshot) |
| GET | `/management-reviews/<id>/export/?format=pptx\|docx` | Télécharge l'export |
| GET/POST | `/management-reviews/<id>/decisions/` | Liste / création de décisions |
| GET/PATCH/DELETE | `/decisions/<id>/` | Détail décision |
| POST | `/decisions/<id>/promote-to-action-plan/` | Crée un `ComplianceActionPlan` lié |
| GET/POST | `/management-reviews/<id>/isms-changes/` | Liste / création changements SMSI |
| GET/PATCH | `/isms-changes/<id>/` | Détail changement SMSI |
| GET/POST | `/management-reviews/<id>/participants/` | Gestion participants |

Et dans `context` :

| Méthode | URL | Action |
|---|---|---|
| GET/POST | `/api/v1/context/stakeholder-feedback/` | Liste / création |
| GET/PATCH/DELETE | `/api/v1/context/stakeholder-feedback/<id>/` | Détail |

### 5.2 Sérialisation

- `ManagementReviewSerializer` — exhaustif, inclut `decisions_count`, `participants`, `status_display`, `snapshot_available`.
- `ManagementReviewDetailSerializer` — étend avec décisions et changements SMSI imbriqués.
- Permissions : classe `ManagementReviewPermission` héritant de `ModulePermission`.
- Approval workflow (`ApprovableAPIMixin`) réutilisé pour la transition `held → closed`.

---

## 6. Outils MCP

Fichier : `mcp/tools.py`. Suivre la convention existante (docstring détaillée, `@require_perm`).

| Tool | Permission | Description |
|---|---|---|
| `list_management_reviews` | `reports.management_review.read` | Liste filtrée (statut, période, scope). |
| `get_management_review` | `reports.management_review.read` | Détail d'une revue (id ou référence). |
| `create_management_review` | `reports.management_review.create` | Crée une revue. |
| `update_management_review` | `reports.management_review.update` | Met à jour. |
| `transition_management_review` | `reports.management_review.update` | Transition de statut. |
| `close_management_review` | `reports.management_review.approve` | Clôture avec snapshot. |
| `generate_management_review_report` | `reports.management_review.read` | Retourne un export (base64) PPTX ou DOCX. |
| `list_management_review_decisions` | `reports.management_review.read` | Liste les décisions d'une revue. |
| `create_management_review_decision` | `reports.management_review.update` | Ajoute une décision. |
| `promote_decision_to_action_plan` | `reports.management_review.update` + `compliance.action_plan.create` | Génère un plan d'action. |
| `list_isms_changes` | `reports.management_review.read` | Liste les changements SMSI. |
| `create_isms_change` | `reports.management_review.update` | Ajoute un changement SMSI. |
| `list_stakeholder_feedback` | `context.stakeholder_feedback.read` | Liste des retours. |
| `create_stakeholder_feedback` | `context.stakeholder_feedback.create` | Ajoute un retour. |

---

## 7. Permissions

Ajouts à `PERMISSION_REGISTRY` (`accounts/constants.py`) :

```python
"reports.management_review.read",
"reports.management_review.create",
"reports.management_review.update",
"reports.management_review.delete",
"reports.management_review.approve",
"context.stakeholder_feedback.read",
"context.stakeholder_feedback.create",
"context.stakeholder_feedback.update",
"context.stakeholder_feedback.delete",
```

Attribution aux groupes système :

| Groupe | Permissions |
|---|---|
| Super Admin, Admin | Toutes |
| RSSI/DPO | Toutes sauf `delete` |
| Auditeur | `read` uniquement |
| Contributeur | `read`, `create`, `update` sur stakeholder_feedback ; `read` sur management_review |
| Lecteur | `read` uniquement |

Ajout via **data migration** (pattern éprouvé, cf. migrations existantes populant `PERMISSION_REGISTRY`).

---

## 8. Internationalisation

- Toutes les nouvelles chaînes UI sont enveloppées `_()` / `{% trans %}`.
- Traductions FR systématiques dans `locale/fr/LC_MESSAGES/django.po`.
- Vérification **pas de doublon** de `msgid` (cf. CLAUDE.md). Utiliser `pgettext_lazy` avec contexte `"management review"` pour désambiguïser si besoin (ex. « Decision », « Status »).
- `compilemessages` doit réussir sans erreur.

---

## 9. Navigation et helpers

- Ajout d'un item **« Revues de direction »** dans le menu principal, sous « Reports » (nouveau sous-groupe).
- Nouveaux `HelpContent` dans `helpers` pour : page liste, page détail, création décision, création changement SMSI, création feedback.
- Dashboard (`core/views.py`) : ajout d'un widget « Prochaine revue de direction » (compte à rebours + lien) et « Décisions en retard ».

---

## 10. Tests

Couverture minimale attendue :

### 10.1 Unitaires

- `reports/tests/test_management_review_model.py` — cycle de vie, snapshot, contrainte de clôture (toutes décisions doivent avoir owner+due_date).
- `reports/tests/test_decision_model.py` — lien vers plan d'action, rétrochaînage.
- `reports/tests/test_isms_change_model.py` — workflow.
- `context/tests/test_stakeholder_feedback_model.py` — intégrité, liens.
- `reports/tests/test_indicator_trend.py` — calcul de tendance, conformité fréquence.

### 10.2 Vues

- Parcours complet : créer revue → ajouter décisions → clôturer → exporter.
- Garde-fou : clôture refusée si décision sans `owner` ou `due_date`.
- Snapshot : données figées après clôture (modif ultérieure d'un indicateur ne doit pas altérer l'export).

### 10.3 API

- CRUD complet sur les 4 nouveaux endpoints.
- Permissions par rôle (matrice §7).
- Export via API : vérifier en-têtes `Content-Type` et `Content-Disposition`.

### 10.4 MCP

- Chaque tool testé avec succès et refus (permission manquante).
- `generate_management_review_report` retourne un contenu non vide, bon nom de fichier.

### 10.5 Export

- Test d'intégration : DOCX généré contient les décisions, les participants, la synthèse.
- Test d'intégration : PPTX généré ne contient plus les placeholders `[A completer]`.

**Factories** (`factory-boy`) à ajouter : `ManagementReviewFactory`, `ManagementReviewParticipantFactory`, `ManagementReviewDecisionFactory`, `IsmsChangeFactory`, `StakeholderFeedbackFactory`.

---

## 11. Migration et compatibilité

### 11.1 Migrations Django

Ordre :

1. `reports/migrations/0002_management_review.py` — création des 5 tables (`ManagementReview`, `ManagementReviewParticipant`, `ManagementReviewDecision`, `IsmsChange`, `ManagementReviewComment`, `ManagementReviewTransition`).
2. `context/migrations/XXXX_stakeholder_feedback.py` — création `StakeholderFeedback`.
3. `compliance/migrations/XXXX_action_plan_originating_review.py` — ajout FK nullable.
4. `risks/migrations/XXXX_treatment_plan_originating_review.py` — ajout FK nullable.
5. `context/migrations/XXXX_objective_originating_review.py` — ajout FK nullable.
6. `accounts/migrations/XXXX_management_review_permissions.py` — data migration populant `PERMISSION_REGISTRY` et groupes système.

Toutes additives. Aucune donnée existante perdue.

### 11.2 Compatibilité avec l'export existant

L'export actuel reste **fonctionnel sans revue** : si `review=None`, l'API conserve le comportement de la v0.22 (export live avec scopes+période). Les écrans existants (`report_list.html`, `management_review_form.html`) sont conservés en tant qu'**alternative rapide** pour les utilisateurs qui ne veulent pas créer de revue persistante.

À terme (v+1), dépréciation douce : bandeau d'information recommandant de passer par `ManagementReview`.

---

## 12. CHANGELOG et README

Conformément à `CLAUDE.md` :

- **CHANGELOG.md** — ajouter sous `## [Unreleased]` :
  - `### Added` : « Persistent management review workflow (ISO 27001:2022 clause 9.3) with decisions, ISMS changes, participants, and snapshot-based auditability. »
  - `### Added` : « Stakeholder feedback module. »
  - `### Added` : « Indicator trend analysis in management review exports. »
  - `### Changed` : « Management review export now consumes persistent review data when available. »

- **README.md** — mettre à jour :
  - Tableau des fonctionnalités (colonne Reports : + Management reviews).
  - Tableau des MCP tools : ajouter les 14 nouveaux tools.
  - Tech stack : aucune nouvelle dépendance (python-pptx, python-docx déjà présents).

---

## 13. Critères d'acceptation (Definition of Done)

La feature est considérée livrée quand **tous** les critères suivants sont vérifiés :

### 13.1 Fonctionnels

- [ ] Créer, éditer, transitionner, clôturer, annuler une `ManagementReview` depuis l'UI.
- [ ] Ajouter participants (internes et externes), décisions, changements SMSI.
- [ ] Promouvoir une décision en `ComplianceActionPlan` via bouton inline ; le plan créé porte `originating_review` et `originating_decision`.
- [ ] Créer des `StakeholderFeedback` indépendamment d'une revue.
- [ ] L'export DOCX/PPTX d'une revue `closed` contient : décisions, changements SMSI, participants, synthèse, prochaine revue — zéro placeholder `[A completer]`.
- [ ] La tendance des indicateurs apparaît dans la section 4b.
- [ ] Clôture interdite si une décision est incomplète (message d'erreur clair).
- [ ] Les données d'une revue `closed` sont gelées (ne varient pas avec modifications ultérieures en base).

### 13.2 Techniques

- [ ] Tous les modèles utilisent `BaseModel` ou `ScopedModel` selon pertinence.
- [ ] `HistoricalRecords` sur tous les nouveaux modèles métier.
- [ ] API DRF complète avec permissions, pagination, filtres.
- [ ] MCP tools exposés avec docstrings et `@require_perm`.
- [ ] Migration data populant permissions et groupes sans écraser l'existant.
- [ ] 100% des chaînes UI traduites FR, `compilemessages` OK, pas de doublon `msgid`.
- [ ] Rendu correct mobile + dark mode sur toutes les nouvelles pages.
- [ ] Stepper horizontal utilisé pour le workflow de la revue.
- [ ] Layout 2 colonnes (pas d'onglets) sur la page détail.
- [ ] Couverture de tests pytest ≥ 80% sur les nouveaux fichiers.

### 13.3 Auditabilité

- [ ] `HistoricalRecords` permet de retrouver qui a modifié quoi et quand sur la revue, les décisions, les changements SMSI.
- [ ] `snapshot_data` d'une revue close est horodaté et immuable (testé par régression).
- [ ] Un auditeur externe (rôle `Auditeur`) peut visualiser toute revue close sans pouvoir la modifier.
- [ ] L'export produit à T+N est identique à l'export produit au moment de la clôture (pour une revue `closed`).

---

## 14. Hors périmètre (pour une v+1)

- Signatures électroniques qualifiées (eIDAS) intégrées — restent manuelles dans le DOCX.
- Modèle `Policy` formalisé (actuellement `IsmsChange.affected_policies` = texte libre).
- Rappels automatiques par mail des participants avant la revue.
- Modèles de revue préconfigurés par industrie/certification.
- Export PDF (réutilisation du pipeline `reportlab` éventuellement).
- Tableau de bord « Conformité au processus de revue de direction » (fréquence respectée, délais d'approbation).

---

## 15. Estimation

| Lot | Effort (j.h) |
|---|---|
| Modèles + migrations + admin | 3 |
| Vues UI + templates + workflow stepper | 6 |
| Formulaires et validations | 2 |
| Export DOCX/PPTX enrichi + tendance indicateurs + snapshot | 4 |
| API DRF | 2 |
| MCP tools | 2 |
| `StakeholderFeedback` (modèle, UI, API, MCP) | 2 |
| Permissions + groupes + data migration | 1 |
| Tests (unitaires, intégration, API, MCP) | 4 |
| i18n + traductions FR | 1 |
| Documentation (README, CHANGELOG) | 0,5 |
| **Total** | **~27,5 jours** |

---

_Fin du document._
