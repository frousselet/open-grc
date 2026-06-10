# Site

`context.models.site.Site`

Lieu physique couvert par le SMSI (siège social, datacenter, bureau, usine, entrepôt, site distant). Sert de conteneur géographique pour les biens supports et les fournisseurs, et permet la cartographie « actifs / fournisseurs par site ».

## Pourquoi un modèle dédié plutôt qu'un `SupportAsset` de type site

Les sites étaient initialement modélisables aussi bien comme entités à part qu'à travers le type `site` de `SupportAsset` (avec ses sous-catégories `datacenter` / `office` / `remote_site` / `cloud_region` / `other_site`). Cette double modélisation a été retirée (issue #30, migrations `context.0028` + `assets.0029`). Décision : un site n'est pas un bien support, c'est un conteneur de biens supports. La distinction est désormais :

| Modèle | Sert à... |
|---|---|
| `Site` | décrire un lieu physique (adresse, hiérarchie, périmètres rattachés) |
| `SupportAsset` | décrire un actif technique ou humain (avec propriétaire, niveaux DIC, cycle de vie, etc.) |
| `SiteAssetDependency` | rattacher un bien support à son site d'hébergement |
| `SiteSupplierDependency` | rattacher un fournisseur à un site qu'il dessert |

Le type `site` de `SupportAsset` n'existe plus. Les rangées existantes ont été automatiquement converties en `Site` au moment de la migration ; les biens supports qui hébergeaient ces sites doivent être rerattachés via `SiteAssetDependency`.

## Champs

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-généré | Identifiant unique |
| `reference` | string | auto-généré `SITE-N`, unique | Référence métier |
| `scopes` | relation | M2M -> Scope | Périmètres SMSI rattachés (RG-01). Un site peut couvrir plusieurs périmètres (cas multi-filiales partageant un même datacenter). |
| `name` | string | requis, max 255 | Nom du site (ex. « Siège Lyon Part-Dieu », « Datacenter Bron ») |
| `type` | enum | requis, défaut `other` | `headquarters`, `office`, `factory`, `warehouse`, `datacenter`, `remote`, `other` |
| `address` | text | optionnel | Adresse postale, plan, indications d'accès |
| `description` | text | optionnel | Description libre |
| `parent_site` | relation | FK -> Site, optionnel | Hiérarchie de sites (groupe -> filiale -> site). Cycles rejetés par `clean()`. |
| `status` | enum | requis, défaut `draft` | `draft`, `active`, `archived` |
| `tags` | relation | M2M -> Tag | Étiquettes libres |
| `is_approved` | boolean | défaut `false` | Site validé par un approbateur |
| `approved_by` | relation | FK -> User, optionnel | Approbateur |
| `approved_at` | datetime | optionnel | Date d'approbation |
| `version` | int | auto-incrémenté | Bumpé à chaque modification majeure |
| `created_by` | relation | FK -> User | Créateur |
| `created_at` | datetime | auto | Date de création |
| `updated_at` | datetime | auto | Date de dernière modification |

## Énumération `type`

- `headquarters` : siège social
- `office` : bureau / locaux administratifs
- `factory` : usine / site de production
- `warehouse` : entrepôt / centre logistique
- `datacenter` : datacenter (en propre ou colocation). Inclut désormais les anciennes valeurs `cloud_region` des biens supports, qui sont versées dans cette catégorie par la migration `assets.0029` à défaut d'une entrée dédiée.
- `remote` : site distant, télétravail organisé, site secondaire
- `other` : autre cas

Les libellés affichés sont localisés via la couche i18n (`.po`). Les anciennes valeurs françaises (`siege`, `bureau`, `usine`, `entrepot`, `site_distant`, `autre`) ont été renommées en anglais par la migration `context.0027` (issue #31).

## Hiérarchie

`parent_site` permet de modéliser un arbre : Groupe -> Filiale -> Site -> Bâtiment. La règle `clean()` détecte et rejette les cycles. Il n'y a pas de contrainte de profondeur ni de contrainte de cohérence entre les périmètres d'un parent et de ses enfants : un site enfant peut appartenir à un périmètre que son parent n'a pas (cas multi-filiales partageant un site).

## Relations dépendances

### `SiteAssetDependency` (rattachement Site <- SupportAsset)

`assets.models.site_dependency.SiteAssetDependency`

Un bien support (serveur, équipement réseau, etc.) est hébergé ou localisé sur un site. La relation porte sa propre référence (`SADP-N`), un type de dépendance, une criticité et un drapeau `is_single_point_of_failure` calculé automatiquement.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto-généré `SADP-N`, unique | |
| `site` | FK -> Site | requis | Site qui héberge l'actif |
| `support_asset` | FK -> SupportAsset | requis | Bien support hébergé |
| `dependency_type` | enum | requis | `located_at`, `hosted_at`, `deployed_at`, `other` |
| `criticality` | enum | requis | `low`, `medium`, `high`, `critical` |
| `description` | text | optionnel | |
| `is_single_point_of_failure` | boolean | lecture seule | Calculé par le service de détection des SPOF (M2 §3.3 RS-07) |
| `redundancy_level` | enum | optionnel | `none`, `partial`, `full` |

### `SiteSupplierDependency` (rattachement Site <- Supplier)

`assets.models.site_dependency.SiteSupplierDependency`

Un fournisseur dessert / opère / maintient un site.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK | |
| `reference` | string | auto-généré `SSDP-N`, unique | |
| `site` | FK -> Site | requis | Site desservi |
| `supplier` | FK -> Supplier | requis | Fournisseur intervenant sur le site |
| `dependency_type` | enum | requis | `provides`, `hosts`, `manages`, `develops`, `supports`, `licenses`, `maintains`, `other` |
| `criticality` | enum | requis | `low`, `medium`, `high`, `critical` |
| `description` | text | optionnel | |
| `is_single_point_of_failure` | boolean | lecture seule | Calculé par le service de détection des SPOF |
| `redundancy_level` | enum | optionnel | `none`, `partial`, `full` |

## Règles de gestion

| ID | Règle |
|---|---|
| RG-SITE-01 | Un site peut être rattaché à un ou plusieurs `Scope`. Un site sans périmètre est valide (site transverse). |
| RG-SITE-02 | La hiérarchie `parent_site` ne tolère pas de cycle. Détecté à `clean()`. |
| RG-SITE-03 | Le `status` est libre : un site peut être `active` simultanément à d'autres sites (la règle RG-02 du module Contexte a été retirée pour cause de hiérarchie multi-périmètres). |
| RG-SITE-04 | `is_single_point_of_failure` sur les dépendances de site est calculé par le service `assets.services.spof_detection`. La valeur fournie en écriture est ignorée. |

## Endpoints

### REST

- `GET /api/v1/context/sites/` : liste avec filtres `type`, `status`, `parent_site_id`
- `POST /api/v1/context/sites/`
- `GET /api/v1/context/sites/<uuid>/`
- `PUT/PATCH /api/v1/context/sites/<uuid>/`
- `DELETE /api/v1/context/sites/<uuid>/`
- `POST /api/v1/context/sites/<uuid>/approve/`
- Les `SiteAssetDependency` et `SiteSupplierDependency` ont leurs propres routes sous `/api/v1/assets/site-asset-dependencies/` et `/api/v1/assets/site-supplier-dependencies/`.

### MCP

- `list_sites` / `get_site` / `create_site` / `update_site` / `delete_site` / `approve_site` / `batch_create_sites`
- `list_site_asset_dependencys` / `create_site_asset_dependency` / ...
- `list_site_supplier_dependencys` / `create_site_supplier_dependency` / ...

## Permissions

| Codename | Description |
|---|---|
| `context.site.read` | Lire les sites |
| `context.site.create` | Créer un site |
| `context.site.update` | Modifier un site |
| `context.site.delete` | Supprimer un site |
| `context.site.approve` | Approuver un site |

## Migration

Les rangées historiques `SupportAsset[type=site]` ont été converties en `Site` par la migration `assets.0029`. Le mapping appliqué :

| Ancienne `SupportAsset.category` | Nouveau `Site.type` |
|---|---|
| `datacenter` | `datacenter` |
| `office` | `office` |
| `remote_site` | `remote` |
| `cloud_region` | `datacenter` |
| `other_site` | `other` |

Les autres champs du bien support (propriétaire, DIC, dates de cycle de vie, etc.) ne sont pas transférés vers Site, qui ne les modélise pas. Les `AssetDependency` qui pointaient sur ces biens supports ont été supprimées par cascade : il faut les recréer en `SiteAssetDependency` côté `Site` si la relation a un sens.

## Références

- [SupportAsset](support-asset.md), [AssetDependency](asset-dependency.md), [Supplier](#m2-assets-supplier-mdtbd) (fournisseur, spec à venir, issue [#35](https://github.com/frousselet/cairn/issues/35))
- Migrations : `context.0027` (rename FR -> EN), `context.0028` (scopes M2M), `assets.0029` (drop site type + conversion)
- Issues : [#30](https://github.com/frousselet/cairn/issues/30) (cette spec), [#31](https://github.com/frousselet/cairn/issues/31) (rename FR -> EN)
