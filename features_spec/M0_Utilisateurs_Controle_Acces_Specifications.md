# Module 0 — Gestion des Utilisateurs et Contrôle d'Accès

## Spécifications fonctionnelles et techniques

**Version :** 1.0
**Date :** 27 février 2026
**Statut :** Draft

---

## 1. Présentation générale

### 1.1 Objectif du module

Le module **Gestion des Utilisateurs et Contrôle d'Accès** constitue le socle transversal de l'application Open GRC. Il assure l'authentification des utilisateurs, la gestion de leurs profils, et le contrôle d'accès granulaire à l'ensemble des fonctionnalités de la plateforme via un modèle RBAC (Role-Based Access Control) basé sur des groupes de permissions.

Ce module est entièrement administrable depuis l'interface Open GRC. L'accès à l'interface d'administration Django est réservé aux utilisateurs disposant d'une permission spécifique et n'est pas nécessaire pour la gestion courante des utilisateurs.

### 1.2 Périmètre fonctionnel

Le module couvre cinq sous-domaines :

1. Authentification (login/mot de passe, futur SSO)
2. Gestion des utilisateurs (CRUD, profils, statuts)
3. Gestion des groupes (regroupements logiques de permissions)
4. Gestion des permissions (RBAC granulaire par feature et par action CRUD)
5. Journalisation des accès et des actions d'administration

### 1.3 Dépendances avec les autres modules

| Module cible | Nature de la dépendance |
|---|---|
| Tous les modules | Chaque module consomme les permissions définies ici pour contrôler l'accès à ses fonctionnalités |
| Contexte et Organisation | Les rôles GRC (Module 1) sont distincts des groupes d'accès applicatifs mais peuvent être liés à des utilisateurs |
| Notifications | Les préférences de notification sont rattachées au profil utilisateur |

### 1.4 Principes directeurs

- **Autonomie complète via l'interface Open GRC :** toute la gestion des utilisateurs, groupes et permissions se fait depuis l'application, sans recourir à l'admin Django.
- **Admin Django réservée :** l'accès à l'interface d'administration Django est contrôlé par une permission dédiée, destinée exclusivement aux opérations techniques avancées (debug, configuration bas niveau).
- **Extensibilité de l'authentification :** l'architecture est conçue pour intégrer ultérieurement des mécanismes SSO (SAML 2.0, OIDC) sans impact majeur sur le modèle de données.
- **Granularité maximale :** chaque feature de chaque module dispose de 4 permissions élémentaires (create, read, update, delete), attribuées exclusivement via des groupes.

---

## 2. Modèle de données

### 2.1 Entité : User (Utilisateur)

Représente un utilisateur de la plateforme Open GRC.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `email` | string | requis, unique, format email | Adresse email (identifiant de connexion) |
| `first_name` | string | requis, max 150 | Prénom |
| `last_name` | string | requis, max 150 | Nom de famille |
| `display_name` | string | calculé ou surchargé, max 255 | Nom d'affichage (`first_name last_name` par défaut) |
| `job_title` | string | optionnel, max 255 | Fonction / poste |
| `department` | string | optionnel, max 255 | Direction / service |
| `phone` | string | optionnel, max 50 | Numéro de téléphone |
| `avatar` | image | optionnel | Photo de profil |
| `password` | string | requis, hashé | Mot de passe (bcrypt/argon2) |
| `is_active` | boolean | requis, défaut true | Compte actif |
| `is_staff` | boolean | requis, défaut false | Accès à l'interface d'administration Django |
| `groups` | relation | M2M → Group | Groupes d'appartenance |
| `language` | enum | requis, défaut `fr` | Langue d'interface préférée (`fr`, `en`) |
| `timezone` | string | requis, défaut `Europe/Paris` | Fuseau horaire |
| `notification_preferences` | json | optionnel | Préférences de notification (email, in-app) |
| `last_login` | datetime | auto | Date de dernière connexion |
| `password_changed_at` | datetime | auto | Date du dernier changement de mot de passe |
| `failed_login_attempts` | integer | auto, défaut 0 | Nombre de tentatives de connexion échouées consécutives |
| `locked_until` | datetime | optionnel | Date de fin de verrouillage du compte |
| `created_by` | relation | FK → User, optionnel | Créateur du compte (null si auto-inscription) |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

> Note : Le champ `email` est l'identifiant unique de connexion. Il remplace le champ `username` par défaut de Django.

### 2.2 Entité : Group (Groupe)

Représente un groupe de permissions. Les droits d'accès sont attribués exclusivement via les groupes, jamais directement à un utilisateur.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `name` | string | requis, unique, max 255 | Nom du groupe |
| `description` | text | optionnel | Description du groupe et de sa vocation |
| `is_system` | boolean | requis, défaut false | Groupe système (non modifiable, non supprimable) |
| `permissions` | relation | M2M → Permission | Permissions associées |
| `users` | relation | M2M → User | Utilisateurs membres |
| `created_by` | relation | FK → User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

### 2.3 Entité : Permission (Permission)

Représente une permission élémentaire sur une feature d'un module. Les permissions sont générées par le système et ne sont pas créées manuellement.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `codename` | string | requis, unique, max 255 | Code technique (ex. `context.scope.create`) |
| `name` | string | requis, max 255 | Libellé lisible (ex. « Créer un périmètre ») |
| `module` | string | requis, max 100 | Module d'appartenance (ex. `context`, `assets`) |
| `feature` | string | requis, max 100 | Feature concernée (ex. `scope`, `essential_asset`) |
| `action` | enum | requis | `create`, `read`, `update`, `delete` |
| `description` | text | optionnel | Description détaillée de la permission |
| `is_system` | boolean | requis, défaut true | Permission système (non supprimable) |

> Note : Le format du `codename` suit la convention `{module}.{feature}.{action}`. Les permissions sont auto-générées à partir du registre des modules.

### 2.4 Entité : SpecialPermission (Permission spéciale)

Certaines permissions ne suivent pas le modèle CRUD standard et couvrent des actions transversales ou spécifiques.

| Codename | Description |
|---|---|
| `system.admin_django.access` | Afficher le bouton d'accès et accéder à l'interface d'administration Django |
| `system.users.manage` | Gérer les utilisateurs (créer, modifier, désactiver) |
| `system.groups.manage` | Gérer les groupes et affecter des permissions |
| `system.audit_trail.read` | Consulter le journal d'audit global |
| `system.config.manage` | Accéder à la configuration globale de l'application |
| `system.webhooks.manage` | Gérer les webhooks |
| `system.notifications.manage` | Gérer les modèles de notifications |

> Ces permissions spéciales sont créées en tant qu'enregistrements `Permission` avec `module = system` et sont traitées de la même manière que les permissions CRUD par le moteur d'autorisation.

### 2.5 Entité : Session (Session utilisateur)

Représente une session active d'un utilisateur authentifié.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `user_id` | relation | FK → User, requis | Utilisateur |
| `token_jti` | string | requis, unique | Identifiant unique du JWT (JTI claim) |
| `ip_address` | string | requis | Adresse IP de connexion |
| `user_agent` | string | optionnel | User-agent du navigateur/client |
| `created_at` | datetime | auto | Date de création (connexion) |
| `expires_at` | datetime | requis | Date d'expiration |
| `revoked_at` | datetime | optionnel | Date de révocation (déconnexion explicite) |
| `is_active` | boolean | requis, défaut true | Session active |

### 2.6 Entité : AccessLog (Journal des accès)

Enregistre chaque événement d'authentification pour la traçabilité et la détection d'anomalies.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `timestamp` | datetime | auto | Horodatage UTC |
| `user_id` | relation | FK → User, optionnel | Utilisateur (null si login échoué sur un compte inexistant) |
| `email_attempted` | string | requis | Email utilisé pour la tentative |
| `event_type` | enum | requis | `login_success`, `login_failed`, `logout`, `token_refresh`, `password_change`, `password_reset_request`, `password_reset_complete`, `account_locked`, `account_unlocked` |
| `ip_address` | string | requis | Adresse IP |
| `user_agent` | string | optionnel | User-agent |
| `failure_reason` | string | optionnel | Raison de l'échec (ex. `invalid_password`, `account_locked`, `account_inactive`) |
| `metadata` | json | optionnel | Données complémentaires |

---

## 3. Règles de gestion

### 3.1 Règles d'authentification

| ID | Règle |
|---|---|
| RA-01 | L'authentification s'effectue par **email + mot de passe**. L'email est l'identifiant unique de connexion (insensible à la casse). |
| RA-02 | Les mots de passe doivent respecter une politique paramétrable. Par défaut : minimum 12 caractères, au moins une majuscule, une minuscule, un chiffre et un caractère spécial. |
| RA-03 | Les mots de passe sont stockés hashés via un algorithme robuste (Argon2 recommandé, bcrypt acceptable). |
| RA-04 | Après **5 tentatives de connexion échouées** consécutives, le compte est verrouillé pendant **15 minutes**. Ces seuils sont paramétrables. |
| RA-05 | Un token **JWT** est émis à la connexion réussie. Le token d'accès a une durée de vie de **30 minutes**, le token de rafraîchissement de **7 jours**. Ces durées sont paramétrables. |
| RA-06 | Le token de rafraîchissement est **rotatif** : chaque utilisation émet un nouveau couple access/refresh et invalide l'ancien refresh. |
| RA-07 | La déconnexion explicite révoque le token de rafraîchissement côté serveur (blacklist). |
| RA-08 | Un utilisateur peut consulter et révoquer ses **sessions actives** depuis son profil. |
| RA-09 | Un administrateur peut forcer la déconnexion de toutes les sessions d'un utilisateur. |
| RA-10 | Le changement de mot de passe invalide toutes les sessions actives de l'utilisateur sauf la session courante. |

### 3.2 Règles de gestion des mots de passe

| ID | Règle |
|---|---|
| RP-01 | L'utilisateur peut changer son mot de passe depuis son profil (nécessite le mot de passe actuel). |
| RP-02 | La procédure de **réinitialisation de mot de passe** envoie un lien unique par email, valide pendant **1 heure**. |
| RP-03 | L'historique des **5 derniers mots de passe** est conservé (hashé). L'utilisateur ne peut pas réutiliser un mot de passe récent. |
| RP-04 | Un administrateur peut forcer la réinitialisation du mot de passe d'un utilisateur. L'utilisateur reçoit un email avec un lien de réinitialisation. L'administrateur ne voit jamais le mot de passe en clair. |
| RP-05 | Une **durée de vie maximale** du mot de passe est paramétrable (défaut : 90 jours). À expiration, l'utilisateur est invité à changer son mot de passe à la prochaine connexion. |

### 3.3 Règles de gestion des utilisateurs

| ID | Règle |
|---|---|
| RU-01 | La création, modification et désactivation des utilisateurs se fait exclusivement depuis l'interface **Open GRC** (pas depuis l'admin Django). |
| RU-02 | Un utilisateur ne peut pas être supprimé s'il est référencé comme propriétaire, créateur ou responsable dans un autre module. Dans ce cas, seule la **désactivation** (`is_active = false`) est possible. |
| RU-03 | Un utilisateur désactivé ne peut plus se connecter. Ses sessions actives sont immédiatement révoquées. |
| RU-04 | Un utilisateur peut modifier son propre profil (nom, prénom, téléphone, avatar, langue, fuseau horaire, préférences de notification) sans permission spécifique. |
| RU-05 | Seuls les utilisateurs disposant de la permission `system.users.manage` peuvent créer, modifier ou désactiver d'autres utilisateurs. |
| RU-06 | Le champ `is_staff` (accès à l'admin Django) ne peut être modifié que par un utilisateur disposant de la permission `system.admin_django.access`. |
| RU-07 | Il doit exister à tout instant au moins **un utilisateur actif** disposant de la permission `system.users.manage`. Le système empêche la désactivation ou le retrait de groupe qui violerait cette règle. |

### 3.4 Règles de gestion des groupes et permissions

| ID | Règle |
|---|---|
| RG-01 | Les **permissions sont attribuées exclusivement via les groupes**, jamais directement à un utilisateur. |
| RG-02 | Un utilisateur peut appartenir à **plusieurs groupes**. Ses permissions effectives sont l'**union** des permissions de tous ses groupes. |
| RG-03 | Les **groupes système** (`is_system = true`) sont créés à l'installation et ne peuvent être ni modifiés, ni supprimés, ni renommés. Leurs permissions peuvent toutefois être consultées. |
| RG-04 | Les groupes personnalisés (non système) peuvent être créés, modifiés et supprimés par les utilisateurs disposant de la permission `system.groups.manage`. |
| RG-05 | La suppression d'un groupe est interdite s'il contient encore des utilisateurs. Les utilisateurs doivent d'abord être retirés ou réaffectés. |
| RG-06 | Les **permissions sont générées automatiquement** par le système à partir du registre des modules et features. Elles ne peuvent pas être créées ou supprimées manuellement. |
| RG-07 | Chaque feature de chaque module génère exactement **4 permissions** : `create`, `read`, `update`, `delete`. Les permissions spéciales (§2.4) sont ajoutées manuellement au registre. |
| RG-08 | Toute modification d'un groupe (ajout/retrait de permission, ajout/retrait de membre) génère une entrée dans le journal d'audit. |
| RG-09 | Le bouton d'accès à l'**admin Django** n'est visible dans l'interface que pour les utilisateurs disposant de la permission `system.admin_django.access`. |

---

## 4. Groupes système par défaut

Les groupes suivants sont créés à l'installation de l'application et ne peuvent pas être supprimés.

### 4.1 Super Administrateur

| Propriété | Valeur |
|---|---|
| Nom | `Super Administrateur` |
| `is_system` | true |
| Permissions | **Toutes les permissions** (y compris `system.admin_django.access`) |
| Vocation | Administration technique complète de la plateforme |

### 4.2 Administrateur

| Propriété | Valeur |
|---|---|
| Nom | `Administrateur` |
| `is_system` | true |
| Permissions | Toutes les permissions **sauf** `system.admin_django.access` |
| Vocation | Administration fonctionnelle complète |

### 4.3 RSSI / DPO

| Propriété | Valeur |
|---|---|
| Nom | `RSSI / DPO` |
| `is_system` | true |
| Permissions | Toutes les permissions `*.read`, `*.create`, `*.update` + `*.export` + `*.audit_trail.read` (pas de `*.delete` ni de `system.config.manage`) |
| Vocation | Pilotage du dispositif GRC |

### 4.4 Auditeur

| Propriété | Valeur |
|---|---|
| Nom | `Auditeur` |
| `is_system` | true |
| Permissions | Toutes les permissions `*.read` + `*.export` + `*.audit_trail.read` |
| Vocation | Consultation et audit de la plateforme |

### 4.5 Contributeur

| Propriété | Valeur |
|---|---|
| Nom | `Contributeur` |
| `is_system` | true |
| Permissions | Toutes les permissions `*.read`, `*.create`, `*.update` (pas de `*.delete` ni d'accès système) |
| Vocation | Contribution au contenu GRC |

### 4.6 Lecteur

| Propriété | Valeur |
|---|---|
| Nom | `Lecteur` |
| `is_system` | true |
| Permissions | Toutes les permissions `*.read` uniquement |
| Vocation | Consultation seule |

---

## 5. Registre des permissions

### 5.1 Convention de nommage

Chaque permission suit le format : `{module}.{feature}.{action}`

- **module** : identifiant du module (`context`, `assets`, `risks`, `compliance`, `measures`, `suppliers`, `audits`, `incidents`, `training`, `system`)
- **feature** : identifiant de la feature au sein du module
- **action** : `create`, `read`, `update`, `delete`

### 5.2 Permissions par module

#### Module Contexte et Organisation (`context`)

| Feature | create | read | update | delete |
|---|---|---|---|---|
| `scope` | `context.scope.create` | `context.scope.read` | `context.scope.update` | `context.scope.delete` |
| `scope_approve` | — | — | `context.scope_approve.update` | — |
| `issue` | `context.issue.create` | `context.issue.read` | `context.issue.update` | `context.issue.delete` |
| `stakeholder` | `context.stakeholder.create` | `context.stakeholder.read` | `context.stakeholder.update` | `context.stakeholder.delete` |
| `expectation` | `context.expectation.create` | `context.expectation.read` | `context.expectation.update` | `context.expectation.delete` |
| `objective` | `context.objective.create` | `context.objective.read` | `context.objective.update` | `context.objective.delete` |
| `swot` | `context.swot.create` | `context.swot.read` | `context.swot.update` | `context.swot.delete` |
| `swot_validate` | — | — | `context.swot_validate.update` | — |
| `role` | `context.role.create` | `context.role.read` | `context.role.update` | `context.role.delete` |
| `role_assign` | — | — | `context.role_assign.update` | — |
| `activity` | `context.activity.create` | `context.activity.read` | `context.activity.update` | `context.activity.delete` |
| `config` | — | `context.config.read` | `context.config.update` | — |
| `export` | — | `context.export.read` | — | — |
| `audit_trail` | — | `context.audit_trail.read` | — | — |

#### Module Gestion des Actifs (`assets`)

| Feature | create | read | update | delete |
|---|---|---|---|---|
| `essential_asset` | `assets.essential_asset.create` | `assets.essential_asset.read` | `assets.essential_asset.update` | `assets.essential_asset.delete` |
| `essential_asset_evaluate` | — | — | `assets.essential_asset_evaluate.update` | — |
| `support_asset` | `assets.support_asset.create` | `assets.support_asset.read` | `assets.support_asset.update` | `assets.support_asset.delete` |
| `dependency` | `assets.dependency.create` | `assets.dependency.read` | `assets.dependency.update` | `assets.dependency.delete` |
| `group` | `assets.group.create` | `assets.group.read` | `assets.group.update` | `assets.group.delete` |
| `import` | `assets.import.create` | — | — | — |
| `config` | — | `assets.config.read` | `assets.config.update` | — |
| `export` | — | `assets.export.read` | — | — |
| `audit_trail` | — | `assets.audit_trail.read` | — | — |

> Note : Les modules Risques, Conformité, Mesures, Fournisseurs, Audits, Incidents et Formations suivront la même convention. Le registre complet sera établi lors de la spécification de chaque module.

#### Permissions système (`system`)

| Feature | Permissions |
|---|---|
| `admin_django` | `system.admin_django.access` |
| `users` | `system.users.create`, `system.users.read`, `system.users.update`, `system.users.delete` |
| `groups` | `system.groups.create`, `system.groups.read`, `system.groups.update`, `system.groups.delete` |
| `audit_trail` | `system.audit_trail.read` |
| `config` | `system.config.read`, `system.config.update` |
| `webhooks` | `system.webhooks.create`, `system.webhooks.read`, `system.webhooks.update`, `system.webhooks.delete` |
| `notifications` | `system.notifications.read`, `system.notifications.update` |

---

## 6. Spécifications API REST

### 6.1 Conventions générales

- **Base URL :** `/api/v1/`
- Conventions identiques aux autres modules (pagination, tri, filtrage, format de réponse).

### 6.2 Endpoints — Authentification

| Méthode | Endpoint | Description | Authentification requise |
|---|---|---|---|
| `POST` | `/auth/login` | Connexion (email + mot de passe) → retourne access + refresh tokens | Non |
| `POST` | `/auth/refresh` | Rafraîchir le token d'accès via le refresh token | Non (refresh token requis) |
| `POST` | `/auth/logout` | Déconnexion (révoque le refresh token) | Oui |
| `POST` | `/auth/password/change` | Changer son mot de passe | Oui |
| `POST` | `/auth/password/reset-request` | Demander une réinitialisation de mot de passe | Non |
| `POST` | `/auth/password/reset-confirm` | Confirmer la réinitialisation (token + nouveau mot de passe) | Non (token de réinitialisation) |
| `GET` | `/auth/me` | Profil de l'utilisateur connecté avec permissions effectives | Oui |
| `PATCH` | `/auth/me` | Modifier son propre profil | Oui |
| `GET` | `/auth/me/sessions` | Lister ses sessions actives | Oui |
| `DELETE` | `/auth/me/sessions/{session_id}` | Révoquer une session spécifique | Oui |
| `DELETE` | `/auth/me/sessions` | Révoquer toutes ses sessions (sauf la courante) | Oui |

**Payload de connexion :**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd!"
}
```

**Réponse de connexion réussie :**

```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "access_token_expires_at": "2026-02-27T15:00:00Z",
    "refresh_token_expires_at": "2026-03-06T14:30:00Z",
    "user": {
      "id": "uuid-xxx",
      "email": "user@example.com",
      "display_name": "Jean Dupont",
      "language": "fr",
      "permissions": ["context.scope.read", "context.scope.create", "..."]
    }
  }
}
```

**Réponse d'erreur de connexion :**

```json
{
  "status": "error",
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid email or password.",
    "details": {
      "remaining_attempts": 3
    }
  }
}
```

**Réponse de compte verrouillé :**

```json
{
  "status": "error",
  "error": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account is temporarily locked due to multiple failed login attempts.",
    "details": {
      "locked_until": "2026-02-27T14:45:00Z"
    }
  }
}
```

### 6.3 Endpoints — Utilisateurs

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/users` | Lister les utilisateurs (filtrable, paginé) |
| `POST` | `/users` | Créer un utilisateur |
| `GET` | `/users/{id}` | Détail d'un utilisateur |
| `PUT` | `/users/{id}` | Mise à jour complète |
| `PATCH` | `/users/{id}` | Mise à jour partielle |
| `DELETE` | `/users/{id}` | Désactiver un utilisateur (soft delete) |
| `POST` | `/users/{id}/activate` | Réactiver un utilisateur |
| `POST` | `/users/{id}/force-password-reset` | Forcer la réinitialisation du mot de passe |
| `POST` | `/users/{id}/revoke-sessions` | Révoquer toutes les sessions de l'utilisateur |
| `GET` | `/users/{id}/groups` | Lister les groupes d'un utilisateur |
| `POST` | `/users/{id}/groups` | Ajouter l'utilisateur à un ou plusieurs groupes |
| `DELETE` | `/users/{id}/groups/{group_id}` | Retirer l'utilisateur d'un groupe |
| `GET` | `/users/{id}/permissions` | Lister les permissions effectives (union des groupes) |
| `GET` | `/users/{id}/access-log` | Journal des accès de l'utilisateur |

**Paramètres de filtrage :**

- `?is_active=true|false`
- `?group_id={uuid}`
- `?search=terme` (recherche sur email, nom, prénom)
- `?department=DSI`
- `?has_permission={codename}` (utilisateurs disposant d'une permission spécifique)

### 6.4 Endpoints — Groupes

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/groups` | Lister les groupes |
| `POST` | `/groups` | Créer un groupe |
| `GET` | `/groups/{id}` | Détail d'un groupe |
| `PUT` | `/groups/{id}` | Mise à jour complète |
| `PATCH` | `/groups/{id}` | Mise à jour partielle |
| `DELETE` | `/groups/{id}` | Supprimer un groupe (si vide et non système) |
| `GET` | `/groups/{id}/permissions` | Lister les permissions du groupe |
| `POST` | `/groups/{id}/permissions` | Ajouter des permissions au groupe |
| `DELETE` | `/groups/{id}/permissions/{permission_id}` | Retirer une permission du groupe |
| `PUT` | `/groups/{id}/permissions` | Remplacer toutes les permissions du groupe |
| `GET` | `/groups/{id}/users` | Lister les utilisateurs du groupe |
| `POST` | `/groups/{id}/users` | Ajouter des utilisateurs au groupe |
| `DELETE` | `/groups/{id}/users/{user_id}` | Retirer un utilisateur du groupe |

### 6.5 Endpoints — Permissions

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/permissions` | Lister toutes les permissions (filtrable par module, feature, action) |
| `GET` | `/permissions/{id}` | Détail d'une permission |
| `GET` | `/permissions/by-module` | Permissions groupées par module puis par feature |

**Paramètres de filtrage :**

- `?module=context`
- `?feature=scope`
- `?action=create`
- `?search=terme`

### 6.6 Endpoints — Journal des accès

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/access-logs` | Journal global des accès (filtrable) |
| `GET` | `/access-logs/statistics` | Statistiques d'accès (connexions par jour, échecs, etc.) |

**Paramètres de filtrage :**

- `?user_id={uuid}`
- `?event_type=login_success|login_failed`
- `?date_from={date}&date_to={date}`
- `?ip_address={ip}`

---

## 7. Spécifications d'interface utilisateur

### 7.1 Navigation

La gestion des utilisateurs est accessible via un élément de navigation « Administration » dans le menu principal, se décomposant en sous-menus : Utilisateurs, Groupes, Journal des accès. Ce menu n'est visible que pour les utilisateurs disposant d'au moins une permission `system.*`.

Le bouton d'accès à l'admin Django est affiché **uniquement** si l'utilisateur dispose de la permission `system.admin_django.access`. Il est positionné de manière distincte (ex. icône en pied de menu ou dans un sous-menu « Avancé ») pour éviter toute confusion avec l'administration Open GRC.

### 7.2 Page de connexion

- Formulaire email + mot de passe.
- Lien « Mot de passe oublié ? » menant à la procédure de réinitialisation.
- Message d'erreur générique en cas d'échec (ne pas révéler si l'email existe ou non).
- Affichage d'un compteur de tentatives restantes après le 3ème échec.
- Message de verrouillage avec durée restante si le compte est verrouillé.
- Zone prévue pour les futurs boutons SSO (masquée tant que non configuré).

### 7.3 Vue « Mon profil »

- Affichage et modification des informations personnelles (nom, prénom, téléphone, avatar, langue, fuseau horaire).
- Section « Sécurité » : changement de mot de passe, liste des sessions actives avec possibilité de révocation.
- Section « Préférences de notification » : choix des canaux (email, in-app) par type d'événement.
- Affichage en lecture seule des groupes d'appartenance et des permissions effectives.

### 7.4 Vue « Utilisateurs »

- **Liste :** Tableau avec colonnes (Nom, Email, Fonction, Service, Groupes, Statut, Dernière connexion). Filtres sur le statut (actif/inactif), le groupe, le service. Recherche textuelle.
- **Détail / Édition :** Formulaire avec onglets :
  - *Informations :* identité, coordonnées, fonction, service.
  - *Groupes :* liste des groupes avec possibilité d'ajout/retrait.
  - *Permissions effectives :* vue consolidée (union des groupes) organisée par module, en lecture seule.
  - *Sessions :* sessions actives avec possibilité de révocation.
  - *Journal d'accès :* historique des connexions et actions d'authentification.
- **Actions :** Créer, Modifier, Désactiver/Réactiver, Forcer la réinitialisation du mot de passe, Révoquer les sessions.
- **Indicateurs :** Badge de statut (actif/inactif/verrouillé), avertissement si aucun groupe assigné.

### 7.5 Vue « Groupes »

- **Liste :** Tableau avec colonnes (Nom, Description, Système, Nombre d'utilisateurs, Nombre de permissions). Badge « Système » pour les groupes non modifiables.
- **Détail / Édition :** Formulaire avec onglets :
  - *Informations :* nom, description.
  - *Permissions :* matrice interactive organisée par module → feature → action (create/read/update/delete). Chaque case est une checkbox. Possibilité de cocher/décocher par ligne (feature) ou par colonne (action). Pour les groupes système, la matrice est en lecture seule.
  - *Utilisateurs :* liste des membres avec possibilité d'ajout/retrait.
- **Actions :** Créer, Modifier, Supprimer (si vide et non système).

### 7.6 Vue « Matrice des permissions »

- Vue transversale présentant une grille complète : **Groupes (colonnes) × Permissions (lignes)** regroupées par module/feature.
- Permet de visualiser d'un coup d'œil la répartition des droits entre les groupes.
- Mode lecture seule (la modification se fait depuis le détail de chaque groupe).

### 7.7 Vue « Journal des accès »

- **Liste :** Tableau chronologique des événements d'authentification avec colonnes (Date, Utilisateur, Type d'événement, IP, Résultat). Filtres par utilisateur, type d'événement, période, IP.
- **Statistiques :** Graphiques de connexions par jour, taux d'échec, comptes verrouillés sur la période.

---

## 8. Règles de sécurité

### 8.1 Protection contre les attaques

| Mesure | Description |
|---|---|
| Rate limiting | Limitation des tentatives de connexion : max 10 requêtes par minute par IP sur `/auth/login` |
| Verrouillage de compte | Verrouillage temporaire après N échecs consécutifs (§3.1 RA-04) |
| Protection CSRF | Token CSRF sur les formulaires (mode session) ; non applicable en mode JWT pur |
| Protection XSS | Échappement des données utilisateur, Content-Security-Policy stricte |
| Transport sécurisé | HTTPS obligatoire en production |
| Cookies sécurisés | Flags `HttpOnly`, `Secure`, `SameSite=Strict` sur les cookies de session/refresh |
| Rotation des tokens | Refresh token rotatif avec invalidation de l'ancien (§3.1 RA-06) |

### 8.2 Politique de mots de passe par défaut

| Paramètre | Valeur par défaut | Paramétrable |
|---|---|---|
| Longueur minimale | 12 caractères | Oui |
| Majuscule requise | Oui | Oui |
| Minuscule requise | Oui | Oui |
| Chiffre requis | Oui | Oui |
| Caractère spécial requis | Oui | Oui |
| Historique (non-réutilisation) | 5 derniers mots de passe | Oui |
| Durée de vie maximale | 90 jours | Oui |
| Tentatives avant verrouillage | 5 | Oui |
| Durée de verrouillage | 15 minutes | Oui |

### 8.3 Préparation pour le SSO (futur)

L'architecture est conçue pour intégrer ultérieurement des fournisseurs d'identité externes :

| Protocole | Usage prévu |
|---|---|
| **SAML 2.0** | Intégration avec les IdP d'entreprise (ADFS, Azure AD, Okta) |
| **OpenID Connect (OIDC)** | Intégration avec les fournisseurs OAuth2/OIDC (Google, Azure AD, Keycloak) |

Points d'attention pour le futur :

- Le modèle `User` prévoit un champ extensible pour stocker l'identifiant externe (`external_id`, `identity_provider`).
- Le flux d'authentification est découplé via une couche d'abstraction (authentication backend Django) permettant d'ajouter des backends SSO sans modifier le modèle utilisateur.
- La page de connexion prévoit une zone dédiée aux boutons SSO.
- Le provisionnement automatique des utilisateurs (JIT provisioning) et le mapping de groupes depuis les claims SAML/OIDC seront spécifiés dans une version ultérieure.

---

## 9. Journalisation et traçabilité

### 9.1 Audit Trail

Les actions d'administration suivantes sont tracées dans le journal d'audit global :

| Action | Description |
|---|---|
| `user.create` | Création d'un utilisateur |
| `user.update` | Modification d'un profil utilisateur |
| `user.deactivate` | Désactivation d'un utilisateur |
| `user.activate` | Réactivation d'un utilisateur |
| `user.force_password_reset` | Réinitialisation forcée du mot de passe |
| `user.revoke_sessions` | Révocation des sessions d'un utilisateur |
| `group.create` | Création d'un groupe |
| `group.update` | Modification d'un groupe |
| `group.delete` | Suppression d'un groupe |
| `group.permission_add` | Ajout de permission(s) à un groupe |
| `group.permission_remove` | Retrait de permission(s) d'un groupe |
| `group.user_add` | Ajout d'un utilisateur à un groupe |
| `group.user_remove` | Retrait d'un utilisateur d'un groupe |

### 9.2 Journal des accès

Le journal des accès (AccessLog, §2.6) est distinct du journal d'audit et se concentre sur les événements d'authentification. Sa rétention est paramétrable (défaut : 2 ans).

### 9.3 Rétention

- Journal d'audit des actions d'administration : 7 ans (paramétrable).
- Journal des accès (authentification) : 2 ans (paramétrable).

---

## 10. Notifications

| Événement | Destinataires | Canal |
|---|---|---|
| Compte créé | Utilisateur concerné | Email |
| Mot de passe réinitialisé (par un administrateur) | Utilisateur concerné | Email |
| Compte désactivé | Utilisateur concerné | Email |
| Compte réactivé | Utilisateur concerné | Email |
| Mot de passe expirant (7 jours avant) | Utilisateur concerné | In-app, email |
| Compte verrouillé après tentatives échouées | Utilisateur concerné + Administrateurs | In-app (admin), email (utilisateur) |
| Connexion depuis une nouvelle adresse IP | Utilisateur concerné | Email (optionnel, paramétrable) |
| Ajout/retrait d'un groupe | Utilisateur concerné | In-app |

---

## 11. Considérations techniques

### 11.1 Backend d'authentification Django

Le module s'appuie sur le système d'authentification de Django avec les adaptations suivantes :

- **Custom User Model** : le modèle `User` étend `AbstractBaseUser` avec `email` comme identifiant au lieu de `username`.
- **Authentication Backend** : un backend personnalisé gère l'authentification par email/mot de passe et permet l'ajout futur de backends SSO.
- **Permission Backend** : un backend personnalisé résout les permissions via les groupes (et non via les permissions directes `user_permissions` de Django).

### 11.2 Gestion des tokens JWT

- Bibliothèque recommandée : `djangorestframework-simplejwt`.
- Le token d'accès contient les claims : `user_id`, `email`, `exp`, `iat`, `jti`.
- Le token d'accès **ne contient pas** les permissions (elles sont trop volumineuses et peuvent changer entre deux émissions). Les permissions sont vérifiées côté serveur à chaque requête.
- Le token de rafraîchissement est stocké en base (table `Session`) pour permettre la révocation.

### 11.3 Multi-tenant

Chaque utilisateur est rattaché à un tenant (`tenant_id`). Un utilisateur ne peut voir et gérer que les utilisateurs et groupes de son propre tenant. Les groupes système sont dupliqués par tenant à l'initialisation.

### 11.4 Performances

- La résolution des permissions effectives d'un utilisateur (union des groupes) est mise en cache avec un TTL de **5 minutes**, invalidé lors de toute modification de groupe ou d'appartenance.
- La vérification des permissions sur chaque requête API doit s'exécuter en moins de **5 ms** (lecture depuis le cache).
- La page de connexion doit répondre en moins de **500 ms** en incluant le hash du mot de passe.

### 11.5 Webhooks

Événements spécifiques :

- `system.user.created`, `updated`, `deactivated`, `activated`
- `system.group.created`, `updated`, `deleted`
- `system.group.permissions_changed`
- `system.group.members_changed`
- `system.auth.login_success`, `login_failed`, `account_locked`

---

## 12. Critères d'acceptation

### 12.1 Authentification

- [ ] La connexion par email + mot de passe fonctionne et retourne un couple JWT access/refresh
- [ ] Le rafraîchissement du token fonctionne avec rotation du refresh token
- [ ] La déconnexion révoque effectivement le refresh token
- [ ] Le verrouillage de compte se déclenche après N échecs consécutifs
- [ ] Le déverrouillage automatique fonctionne après la durée paramétrée
- [ ] La réinitialisation de mot de passe par email fonctionne (demande + confirmation)
- [ ] Le changement de mot de passe invalide les autres sessions
- [ ] L'historique des mots de passe empêche la réutilisation

### 12.2 Gestion des utilisateurs

- [ ] Le CRUD complet des utilisateurs fonctionne depuis l'interface Open GRC
- [ ] La désactivation d'un utilisateur révoque ses sessions et empêche la connexion
- [ ] Un utilisateur peut modifier son propre profil
- [ ] La contrainte d'au moins un administrateur actif est respectée
- [ ] L'admin Django n'est pas nécessaire pour la gestion courante

### 12.3 Groupes et permissions

- [ ] Les permissions sont attribuées exclusivement via les groupes
- [ ] Les permissions effectives d'un utilisateur sont l'union de ses groupes
- [ ] Les groupes système ne sont pas modifiables ni supprimables
- [ ] Les groupes personnalisés supportent le CRUD complet
- [ ] La matrice des permissions est consultable et les permissions modifiables via l'interface
- [ ] Chaque feature dispose de 4 permissions CRUD fonctionnelles
- [ ] Le contrôle d'accès est effectif sur chaque endpoint API et chaque vue

### 12.4 Admin Django

- [ ] Le bouton d'accès à l'admin Django n'est visible que pour les utilisateurs avec `system.admin_django.access`
- [ ] Le champ `is_staff` ne peut être modifié que par un utilisateur disposant de `system.admin_django.access`
- [ ] L'accès à l'URL `/admin/` est bloqué pour les utilisateurs sans la permission

### 12.5 Sécurité

- [ ] Les mots de passe respectent la politique définie
- [ ] Le rate limiting est actif sur les endpoints d'authentification
- [ ] Les tokens sont révocables (sessions, déconnexion)
- [ ] Le journal des accès enregistre tous les événements d'authentification
- [ ] Le journal d'audit enregistre toutes les actions d'administration

### 12.6 Performance

- [ ] La vérification des permissions s'exécute en moins de 5 ms (cache)
- [ ] La résolution des permissions effectives est correctement mise en cache et invalidée

---

*Fin des spécifications du Module 0 — Gestion des Utilisateurs et Contrôle d'Accès*
