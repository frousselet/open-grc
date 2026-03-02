from dataclasses import dataclass, field

from django.db.models import Count, Q

from assets.constants import RedundancyLevel, DICLevel
from assets.models import (
    AssetDependency,
    SiteAssetDependency,
    SiteSupplierDependency,
    SupplierDependency,
)
from context.constants import Criticality

HIGH_CRITICALITY = [Criticality.HIGH, Criticality.CRITICAL]
NO_REDUNDANCY = [RedundancyLevel.NONE, ""]


@dataclass
class SpofResult:
    """Summary of a single SPOF detection run."""

    dependency_id: str
    dependency_str: str
    rules: list[str] = field(default_factory=list)
    is_spof: bool = False


class SpofDetector:
    """Analyse the dependency graph and detect Single Points of Failure.

    Each ``detect_*`` method returns a list of SpofResult for one dependency
    type.  ``detect_all`` merges them into a dict summary.  ``apply``
    additionally bulk-updates the ``is_single_point_of_failure`` boolean on
    every dependency.
    """

    def __init__(self, scope=None):
        self.scope = scope

    # ── public API ──────────────────────────────────────────

    def detect_all(self) -> dict:
        """Dry-run: compute SPOF flags without touching the database."""
        asset = self._detect_asset_deps()
        supplier = self._detect_supplier_deps()
        site_asset = self._detect_site_asset_deps()
        site_supplier = self._detect_site_supplier_deps()

        return {
            "asset_dependencies": [self._result_to_dict(r) for r in asset],
            "supplier_dependencies": [self._result_to_dict(r) for r in supplier],
            "site_asset_dependencies": [self._result_to_dict(r) for r in site_asset],
            "site_supplier_dependencies": [self._result_to_dict(r) for r in site_supplier],
            "total_spof": sum(
                r.is_spof for r in asset + supplier + site_asset + site_supplier
            ),
        }

    def apply(self) -> dict:
        """Detect SPOFs and bulk-update the database.  Returns a change summary."""
        changes = {
            "asset_dependencies": self._apply_model(AssetDependency, self._detect_asset_deps),
            "supplier_dependencies": self._apply_model(SupplierDependency, self._detect_supplier_deps),
            "site_asset_dependencies": self._apply_model(SiteAssetDependency, self._detect_site_asset_deps),
            "site_supplier_dependencies": self._apply_model(SiteSupplierDependency, self._detect_site_supplier_deps),
        }
        dep_keys = list(changes.keys())
        changes["total_spof"] = sum(changes[k]["spof_count"] for k in dep_keys)
        changes["total_changed"] = sum(changes[k]["changed"] for k in dep_keys)
        return changes

    # ── detection rules ─────────────────────────────────────

    def _detect_asset_deps(self) -> list[SpofResult]:
        """Rules 1 & 2 on AssetDependency."""
        qs = self._scoped_qs(AssetDependency, scope_path="essential_asset__scopes")
        qs = qs.select_related("essential_asset", "support_asset").annotate(
            fan_in_count=Count(
                "support_asset__dependencies_as_support",
            ),
        )
        results = []
        for dep in qs:
            r = SpofResult(
                dependency_id=str(dep.id),
                dependency_str=str(dep),
            )
            # Rule 1: no redundancy + high/critical criticality
            if dep.redundancy_level in NO_REDUNDANCY and dep.criticality in HIGH_CRITICALITY:
                r.rules.append("no_redundancy_high_criticality")
            # Rule 2: high fan-in (support asset serves multiple essential assets) + no redundancy
            if dep.fan_in_count > 1 and dep.redundancy_level in NO_REDUNDANCY:
                r.rules.append("high_fan_in")
            r.is_spof = len(r.rules) > 0
            results.append(r)
        return results

    def _detect_supplier_deps(self) -> list[SpofResult]:
        """Rule 3 on SupplierDependency."""
        qs = self._scoped_qs(SupplierDependency, scope_path="support_asset__scopes")
        qs = qs.select_related("support_asset", "supplier").annotate(
            redundant_supplier_count=Count(
                "support_asset__supplier_dependencies",
                filter=Q(
                    support_asset__supplier_dependencies__redundancy_level__in=[
                        RedundancyLevel.PARTIAL,
                        RedundancyLevel.FULL,
                    ],
                ),
            ),
        )
        results = []
        for dep in qs:
            r = SpofResult(
                dependency_id=str(dep.id),
                dependency_str=str(dep),
            )
            # Rule 3: sole supplier with no redundant alternative + high criticality
            if dep.redundant_supplier_count == 0 and dep.criticality in HIGH_CRITICALITY:
                r.rules.append("sole_supplier_high_criticality")
            r.is_spof = len(r.rules) > 0
            results.append(r)
        return results

    def _detect_site_asset_deps(self) -> list[SpofResult]:
        """Rule 4 on SiteAssetDependency."""
        qs = self._scoped_qs(SiteAssetDependency, scope_path="support_asset__scopes")
        qs = qs.select_related("support_asset", "site").annotate(
            site_count=Count("support_asset__site_dependencies"),
        )
        results = []
        for dep in qs:
            r = SpofResult(
                dependency_id=str(dep.id),
                dependency_str=str(dep),
            )
            # Rule 4: single site + high inherited availability
            if dep.site_count == 1 and dep.support_asset.inherited_availability >= DICLevel.HIGH:
                r.rules.append("single_site_high_availability")
            r.is_spof = len(r.rules) > 0
            results.append(r)
        return results

    def _detect_site_supplier_deps(self) -> list[SpofResult]:
        """Rule 5 on SiteSupplierDependency."""
        qs = self._scoped_qs(SiteSupplierDependency, scope_path=None)
        qs = qs.select_related("site", "supplier").annotate(
            supplier_count=Count("site__supplier_dependencies"),
        )
        results = []
        for dep in qs:
            r = SpofResult(
                dependency_id=str(dep.id),
                dependency_str=str(dep),
            )
            # Rule 5: sole supplier for a site + high criticality
            if dep.supplier_count == 1 and dep.criticality in HIGH_CRITICALITY:
                r.rules.append("sole_site_supplier_high_criticality")
            r.is_spof = len(r.rules) > 0
            results.append(r)
        return results

    # ── helpers ──────────────────────────────────────────────

    def _scoped_qs(self, model, scope_path=None):
        qs = model.objects.all()
        if self.scope and scope_path:
            qs = qs.filter(**{scope_path: self.scope})
        return qs

    def _apply_model(self, model, detect_fn) -> dict:
        """Apply detection results for a single model via bulk_update."""
        results = detect_fn()
        spof_ids = {r.dependency_id for r in results if r.is_spof}
        all_ids = {r.dependency_id for r in results}
        non_spof_ids = all_ids - spof_ids

        changed = 0
        # Set SPOF = True where detected
        to_set = model.objects.filter(
            id__in=spof_ids, is_single_point_of_failure=False,
        )
        changed += to_set.update(is_single_point_of_failure=True)

        # Clear SPOF = False where no longer detected
        to_clear = model.objects.filter(
            id__in=non_spof_ids, is_single_point_of_failure=True,
        )
        changed += to_clear.update(is_single_point_of_failure=False)

        return {
            "total": len(results),
            "spof_count": len(spof_ids),
            "changed": changed,
        }

    @staticmethod
    def _result_to_dict(r: SpofResult) -> dict:
        return {
            "id": r.dependency_id,
            "label": r.dependency_str,
            "rules": r.rules,
            "is_spof": r.is_spof,
        }
