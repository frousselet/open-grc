import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from assets.constants import (
    DICLevel,
    EssentialAssetCategory,
    EssentialAssetType,
    SupportAssetCategory,
    SupportAssetStatus,
    SupportAssetType,
)
from assets.tests.factories import (
    DependencyFactory,
    EssentialAssetFactory,
    SupportAssetFactory,
)
from context.tests.factories import ScopeFactory

pytestmark = pytest.mark.django_db


class TestDICInheritance:
    """P0: support assets inherit max DIC from linked essential assets."""

    def test_single_dependency_inherits_dic(self):
        ea = EssentialAssetFactory(
            confidentiality_level=DICLevel.HIGH,
            integrity_level=DICLevel.LOW,
            availability_level=DICLevel.CRITICAL,
        )
        sa = SupportAssetFactory()
        DependencyFactory(essential_asset=ea, support_asset=sa)
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.HIGH
        assert sa.inherited_integrity == DICLevel.LOW
        assert sa.inherited_availability == DICLevel.CRITICAL

    def test_multiple_dependencies_take_max(self):
        sa = SupportAssetFactory()
        ea1 = EssentialAssetFactory(
            confidentiality_level=DICLevel.LOW,
            integrity_level=DICLevel.CRITICAL,
            availability_level=DICLevel.MEDIUM,
        )
        ea2 = EssentialAssetFactory(
            confidentiality_level=DICLevel.HIGH,
            integrity_level=DICLevel.LOW,
            availability_level=DICLevel.HIGH,
        )
        DependencyFactory(essential_asset=ea1, support_asset=sa)
        DependencyFactory(essential_asset=ea2, support_asset=sa)
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.HIGH
        assert sa.inherited_integrity == DICLevel.CRITICAL
        assert sa.inherited_availability == DICLevel.HIGH

    def test_delete_dependency_recalculates(self):
        sa = SupportAssetFactory()
        ea1 = EssentialAssetFactory(
            confidentiality_level=DICLevel.CRITICAL,
            integrity_level=DICLevel.CRITICAL,
            availability_level=DICLevel.CRITICAL,
        )
        ea2 = EssentialAssetFactory(
            confidentiality_level=DICLevel.LOW,
            integrity_level=DICLevel.LOW,
            availability_level=DICLevel.LOW,
        )
        dep1 = DependencyFactory(essential_asset=ea1, support_asset=sa)
        DependencyFactory(essential_asset=ea2, support_asset=sa)
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.CRITICAL

        dep1.delete()
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.LOW

    def test_no_dependency_resets_to_negligible(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory(confidentiality_level=DICLevel.HIGH)
        dep = DependencyFactory(essential_asset=ea, support_asset=sa)
        dep.delete()
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.NEGLIGIBLE

    def test_essential_asset_save_propagates_dic(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory(
            confidentiality_level=DICLevel.LOW,
            integrity_level=DICLevel.LOW,
            availability_level=DICLevel.LOW,
        )
        DependencyFactory(essential_asset=ea, support_asset=sa)
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.LOW

        ea.confidentiality_level = DICLevel.CRITICAL
        ea.save()
        sa.refresh_from_db()
        assert sa.inherited_confidentiality == DICLevel.CRITICAL


class TestSupportAssetProperties:
    def test_is_end_of_life_true(self):
        sa = SupportAssetFactory(
            status=SupportAssetStatus.ACTIVE,
            end_of_life_date=timezone.now().date() - timezone.timedelta(days=1),
        )
        assert sa.is_end_of_life is True

    def test_is_end_of_life_false_future(self):
        sa = SupportAssetFactory(
            status=SupportAssetStatus.ACTIVE,
            end_of_life_date=timezone.now().date() + timezone.timedelta(days=30),
        )
        assert sa.is_end_of_life is False

    def test_is_orphan_true(self):
        sa = SupportAssetFactory()
        assert sa.is_orphan is True

    def test_is_orphan_false(self):
        sa = SupportAssetFactory()
        DependencyFactory(support_asset=sa)
        assert sa.is_orphan is False


class TestEssentialAssetValidation:
    def test_process_with_process_category_ok(self):
        ea = EssentialAssetFactory(
            type=EssentialAssetType.BUSINESS_PROCESS,
            category=EssentialAssetCategory.CORE_PROCESS,
        )
        ea.clean()

    def test_process_with_info_category_rejected(self):
        ea = EssentialAssetFactory.build(
            type=EssentialAssetType.BUSINESS_PROCESS,
            category=EssentialAssetCategory.STRATEGIC_DATA,
        )
        with pytest.raises(ValidationError, match="process category"):
            ea.clean()

    def test_info_with_info_category_ok(self):
        ea = EssentialAssetFactory(
            type=EssentialAssetType.INFORMATION,
            category=EssentialAssetCategory.FINANCIAL_DATA,
        )
        ea.clean()

    def test_info_with_process_category_rejected(self):
        ea = EssentialAssetFactory.build(
            type=EssentialAssetType.INFORMATION,
            category=EssentialAssetCategory.CORE_PROCESS,
        )
        with pytest.raises(ValidationError, match="information category"):
            ea.clean()


class TestSupportAssetValidation:
    def test_type_category_coherence_ok(self):
        sa = SupportAssetFactory(
            type=SupportAssetType.SOFTWARE,
            category=SupportAssetCategory.DATABASE,
        )
        sa.clean()

    def test_type_category_mismatch_rejected(self):
        sa = SupportAssetFactory.build(
            type=SupportAssetType.SOFTWARE,
            category=SupportAssetCategory.SERVER,
        )
        with pytest.raises(ValidationError, match="Invalid category"):
            sa.clean()


class TestDependencyValidation:
    def test_decommissioned_asset_rejects_new_dep(self):
        sa = SupportAssetFactory(status=SupportAssetStatus.DECOMMISSIONED)
        ea = EssentialAssetFactory()
        dep = DependencyFactory.build(essential_asset=ea, support_asset=sa)
        with pytest.raises(ValidationError, match="decommissioned"):
            dep.clean()
