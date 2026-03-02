import pytest
from io import StringIO

from django.core.management import call_command

from assets.constants import (
    DICLevel,
    RedundancyLevel,
    SiteAssetDependencyType,
    SiteSupplierDependencyType,
)
from assets.models import SiteAssetDependency, SiteSupplierDependency
from assets.services.spof_detection import SpofDetector
from assets.tests.factories import (
    DependencyFactory,
    EssentialAssetFactory,
    SupplierDependencyFactory,
    SupplierFactory,
    SupportAssetFactory,
)
from context.constants import Criticality
from context.models import Site
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


# ── Helpers ─────────────────────────────────────────────────


def _make_site(name="Site A"):
    """Create a Site with auto-generated reference."""
    return Site.objects.create(name=name)


def _make_site_asset_dep(support_asset, site, **kwargs):
    defaults = {
        "dependency_type": SiteAssetDependencyType.LOCATED_AT,
        "criticality": Criticality.HIGH,
    }
    defaults.update(kwargs)
    return SiteAssetDependency.objects.create(
        support_asset=support_asset, site=site, **defaults
    )


def _make_site_supplier_dep(site, supplier, **kwargs):
    defaults = {
        "dependency_type": SiteSupplierDependencyType.MAINTAINED_BY,
        "criticality": Criticality.HIGH,
    }
    defaults.update(kwargs)
    return SiteSupplierDependency.objects.create(
        site=site, supplier=supplier, **defaults
    )


# ── Rule 1: no redundancy + high criticality ───────────────


class TestRule1NoRedundancyHighCriticality:

    def test_no_redundancy_critical_is_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        results = SpofDetector().detect_all()
        asset_deps = results["asset_dependencies"]
        match = [d for d in asset_deps if d["id"] == str(dep.id)]
        assert len(match) == 1
        assert match[0]["is_spof"] is True
        assert "no_redundancy_high_criticality" in match[0]["rules"]

    def test_no_redundancy_high_is_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.HIGH,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is True

    def test_no_redundancy_low_not_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.LOW,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False

    def test_no_redundancy_medium_not_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.MEDIUM,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False

    def test_full_redundancy_critical_not_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.FULL,
            criticality=Criticality.CRITICAL,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False

    def test_partial_redundancy_high_not_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.PARTIAL,
            criticality=Criticality.HIGH,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False

    def test_empty_redundancy_critical_is_spof(self):
        """Empty string redundancy_level (blank default) also triggers rule 1."""
        dep = DependencyFactory(
            redundancy_level="",
            criticality=Criticality.CRITICAL,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is True


# ── Rule 2: high fan-in ────────────────────────────────────


class TestRule2HighFanIn:

    def test_multiple_essential_assets_no_redundancy_is_spof(self):
        sa = SupportAssetFactory()
        ea1 = EssentialAssetFactory()
        ea2 = EssentialAssetFactory()
        ea3 = EssentialAssetFactory()
        dep1 = DependencyFactory(essential_asset=ea1, support_asset=sa, redundancy_level="", criticality=Criticality.LOW)
        DependencyFactory(essential_asset=ea2, support_asset=sa, redundancy_level="", criticality=Criticality.LOW)
        DependencyFactory(essential_asset=ea3, support_asset=sa, redundancy_level="", criticality=Criticality.LOW)
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep1.id)]
        assert match[0]["is_spof"] is True
        assert "high_fan_in" in match[0]["rules"]

    def test_single_essential_asset_not_spof_for_rule2(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory()
        dep = DependencyFactory(essential_asset=ea, support_asset=sa, redundancy_level="", criticality=Criticality.LOW)
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        # Not SPOF from rule 2 (no high fan-in), and not from rule 1 (low criticality)
        assert match[0]["is_spof"] is False

    def test_high_fan_in_with_redundancy_not_spof(self):
        sa = SupportAssetFactory()
        ea1 = EssentialAssetFactory()
        ea2 = EssentialAssetFactory()
        dep = DependencyFactory(
            essential_asset=ea1, support_asset=sa,
            redundancy_level=RedundancyLevel.FULL, criticality=Criticality.LOW,
        )
        DependencyFactory(
            essential_asset=ea2, support_asset=sa,
            redundancy_level=RedundancyLevel.FULL, criticality=Criticality.LOW,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False


# ── Rule 3: sole supplier ──────────────────────────────────


class TestRule3SoleSupplier:

    def test_sole_supplier_critical_is_spof(self):
        dep = SupplierDependencyFactory(
            criticality=Criticality.CRITICAL,
            redundancy_level=RedundancyLevel.NONE,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["supplier_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is True
        assert "sole_supplier_high_criticality" in match[0]["rules"]

    def test_multiple_suppliers_with_redundancy_not_spof(self):
        sa = SupportAssetFactory()
        sup1 = SupplierFactory()
        sup2 = SupplierFactory()
        dep1 = SupplierDependencyFactory(
            support_asset=sa, supplier=sup1,
            criticality=Criticality.CRITICAL,
            redundancy_level=RedundancyLevel.NONE,
        )
        SupplierDependencyFactory(
            support_asset=sa, supplier=sup2,
            criticality=Criticality.CRITICAL,
            redundancy_level=RedundancyLevel.FULL,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["supplier_dependencies"] if d["id"] == str(dep1.id)]
        # dep1 itself has no redundancy, but the support_asset has an alternative supplier with FULL redundancy
        assert match[0]["is_spof"] is False

    def test_sole_supplier_low_criticality_not_spof(self):
        dep = SupplierDependencyFactory(
            criticality=Criticality.LOW,
            redundancy_level=RedundancyLevel.NONE,
        )
        results = SpofDetector().detect_all()
        match = [d for d in results["supplier_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False


# ── Rule 4: single site ────────────────────────────────────


class TestRule4SingleSite:

    def test_single_site_high_availability_is_spof(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory(availability_level=DICLevel.HIGH)
        DependencyFactory(essential_asset=ea, support_asset=sa)
        sa.refresh_from_db()
        assert sa.inherited_availability >= DICLevel.HIGH

        site = _make_site()
        dep = _make_site_asset_dep(sa, site)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is True
        assert "single_site_high_availability" in match[0]["rules"]

    def test_multiple_sites_not_spof(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory(availability_level=DICLevel.CRITICAL)
        DependencyFactory(essential_asset=ea, support_asset=sa)
        sa.refresh_from_db()

        site1 = _make_site("Site A")
        site2 = _make_site("Site B")
        dep1 = _make_site_asset_dep(sa, site1)
        _make_site_asset_dep(sa, site2)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_asset_dependencies"] if d["id"] == str(dep1.id)]
        assert match[0]["is_spof"] is False

    def test_single_site_low_availability_low_criticality_not_spof(self):
        sa = SupportAssetFactory()
        # No essential asset linked → inherited availability stays at NEGLIGIBLE
        # Low criticality → rule 4b doesn't trigger either
        site = _make_site()
        dep = _make_site_asset_dep(sa, site, criticality=Criticality.LOW,
                                   redundancy_level=RedundancyLevel.NONE)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False

    def test_single_site_no_redundancy_critical_is_spof(self):
        """Rule 4b: single site + no redundancy + critical criticality → SPOF,
        even without high inherited availability."""
        sa = SupportAssetFactory()
        site = _make_site()
        dep = _make_site_asset_dep(sa, site, criticality=Criticality.CRITICAL,
                                   redundancy_level=RedundancyLevel.NONE)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is True
        assert "single_site_no_redundancy_high_criticality" in match[0]["rules"]

    def test_single_site_with_full_redundancy_critical_not_spof(self):
        """Full redundancy prevents rule 4b even with critical criticality."""
        sa = SupportAssetFactory()
        site = _make_site()
        dep = _make_site_asset_dep(sa, site, criticality=Criticality.CRITICAL,
                                   redundancy_level=RedundancyLevel.FULL)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_asset_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False


# ── Rule 5: sole site supplier ─────────────────────────────


class TestRule5SoleSiteSupplier:

    def test_sole_supplier_for_site_critical_is_spof(self):
        site = _make_site()
        supplier = SupplierFactory()
        dep = _make_site_supplier_dep(site, supplier, criticality=Criticality.CRITICAL)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_supplier_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is True
        assert "sole_site_supplier_high_criticality" in match[0]["rules"]

    def test_multiple_suppliers_for_site_not_spof(self):
        site = _make_site()
        sup1 = SupplierFactory()
        sup2 = SupplierFactory()
        dep1 = _make_site_supplier_dep(site, sup1, criticality=Criticality.CRITICAL)
        _make_site_supplier_dep(site, sup2, criticality=Criticality.CRITICAL)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_supplier_dependencies"] if d["id"] == str(dep1.id)]
        assert match[0]["is_spof"] is False

    def test_sole_supplier_low_criticality_not_spof(self):
        site = _make_site()
        supplier = SupplierFactory()
        dep = _make_site_supplier_dep(site, supplier, criticality=Criticality.LOW)
        results = SpofDetector().detect_all()
        match = [d for d in results["site_supplier_dependencies"] if d["id"] == str(dep.id)]
        assert match[0]["is_spof"] is False


# ── Apply ───────────────────────────────────────────────────


class TestApply:

    def test_apply_sets_spof_flags(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        assert dep.is_single_point_of_failure is False
        results = SpofDetector().apply()
        assert results["total_spof"] >= 1
        dep.refresh_from_db()
        assert dep.is_single_point_of_failure is True

    def test_apply_clears_old_spof(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.FULL,
            criticality=Criticality.LOW,
            is_single_point_of_failure=True,  # manually set
        )
        SpofDetector().apply()
        dep.refresh_from_db()
        assert dep.is_single_point_of_failure is False

    def test_apply_returns_change_summary(self):
        DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        results = SpofDetector().apply()
        assert "total_spof" in results
        assert "total_changed" in results
        assert "asset_dependencies" in results
        assert results["asset_dependencies"]["spof_count"] >= 1

    def test_apply_idempotent(self):
        DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        results1 = SpofDetector().apply()
        assert results1["total_changed"] >= 1
        results2 = SpofDetector().apply()
        assert results2["total_changed"] == 0


# ── detect_all format ───────────────────────────────────────


class TestDetectAllFormat:

    def test_returns_expected_keys(self):
        results = SpofDetector().detect_all()
        assert "asset_dependencies" in results
        assert "supplier_dependencies" in results
        assert "site_asset_dependencies" in results
        assert "site_supplier_dependencies" in results
        assert "total_spof" in results

    def test_empty_database_returns_zeros(self):
        results = SpofDetector().detect_all()
        assert results["total_spof"] == 0
        assert results["asset_dependencies"] == []
        assert results["supplier_dependencies"] == []

    def test_total_spof_counts_correctly(self):
        DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        SupplierDependencyFactory(
            criticality=Criticality.CRITICAL,
            redundancy_level=RedundancyLevel.NONE,
        )
        results = SpofDetector().detect_all()
        assert results["total_spof"] == 2


# ── Scope filtering ────────────────────────────────────────


class TestScopeFiltering:

    def test_scope_filters_asset_deps(self):
        scope_a = ScopeFactory(name="Scope A")
        scope_b = ScopeFactory(name="Scope B")
        ea_a = EssentialAssetFactory(scope=scope_a)
        ea_b = EssentialAssetFactory(scope=scope_b)
        sa_a = SupportAssetFactory()
        sa_b = SupportAssetFactory()
        DependencyFactory(
            essential_asset=ea_a, support_asset=sa_a,
            redundancy_level=RedundancyLevel.NONE, criticality=Criticality.CRITICAL,
        )
        DependencyFactory(
            essential_asset=ea_b, support_asset=sa_b,
            redundancy_level=RedundancyLevel.NONE, criticality=Criticality.CRITICAL,
        )
        results_a = SpofDetector(scope=scope_a).detect_all()
        assert len(results_a["asset_dependencies"]) == 1
        results_all = SpofDetector().detect_all()
        assert len(results_all["asset_dependencies"]) == 2


# ── Management command ──────────────────────────────────────


class TestManagementCommand:

    def test_dry_run_does_not_change_db(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        out = StringIO()
        call_command("detect_spof", stdout=out)
        dep.refresh_from_db()
        assert dep.is_single_point_of_failure is False
        assert "Dry-run" in out.getvalue()

    def test_apply_changes_db(self):
        dep = DependencyFactory(
            redundancy_level=RedundancyLevel.NONE,
            criticality=Criticality.CRITICAL,
        )
        out = StringIO()
        call_command("detect_spof", "--apply", stdout=out)
        dep.refresh_from_db()
        assert dep.is_single_point_of_failure is True
        assert "applied" in out.getvalue().lower()

    def test_invalid_scope_shows_error(self):
        err = StringIO()
        call_command("detect_spof", "--scope", "nonexistent", stderr=err)
        assert "not found" in err.getvalue().lower()
