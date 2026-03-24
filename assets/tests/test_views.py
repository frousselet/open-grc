import pytest
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import UserFactory
from assets.constants import (
    DependencyType,
    DICLevel,
    EssentialAssetCategory,
    EssentialAssetType,
    SiteAssetDependencyType,
    SiteSupplierDependencyType,
    SupplierCriticality,
    SupplierDependencyType,
    SupportAssetCategory,
    SupportAssetType,
)
from assets.models import (
    AssetDependency,
    AssetGroup,
    EssentialAsset,
    SiteAssetDependency,
    SiteSupplierDependency,
    Supplier,
    SupplierDependency,
    SupplierType,
    SupportAsset,
)
from assets.tests.factories import (
    DependencyFactory,
    EssentialAssetFactory,
    SupplierDependencyFactory,
    SupplierFactory,
    SupplierTypeFactory,
    SupportAssetFactory,
)
from context.constants import Criticality
from context.models import Site

pytestmark = pytest.mark.django_db


# ── Helpers ──────────────────────────────────────────────────


@pytest.fixture
def superuser():
    return UserFactory(is_superuser=True)


@pytest.fixture
def client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


# ── Essential Asset Views ────────────────────────────────────


class TestEssentialAssetListView:
    def test_list_returns_200(self, client):
        EssentialAssetFactory()
        url = reverse("assets:essential-asset-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_list_contains_asset(self, client):
        asset = EssentialAssetFactory(name="Customer DB")
        url = reverse("assets:essential-asset-list")
        response = client.get(url)
        assert "Customer DB" in response.content.decode()

    def test_list_empty(self, client):
        url = reverse("assets:essential-asset-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_list_filter_by_type(self, client):
        EssentialAssetFactory(type=EssentialAssetType.INFORMATION)
        EssentialAssetFactory(
            type=EssentialAssetType.BUSINESS_PROCESS,
            category=EssentialAssetCategory.CORE_PROCESS,
        )
        url = reverse("assets:essential-asset-list")
        response = client.get(url, {"type": EssentialAssetType.INFORMATION})
        assert response.status_code == 200

    def test_list_search(self, client):
        EssentialAssetFactory(name="SearchTarget")
        url = reverse("assets:essential-asset-list")
        response = client.get(url, {"q": "SearchTarget"})
        assert response.status_code == 200


class TestEssentialAssetDetailView:
    def test_detail_returns_200(self, client):
        asset = EssentialAssetFactory()
        url = reverse("assets:essential-asset-detail", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_shows_name(self, client):
        asset = EssentialAssetFactory(name="Secret Info")
        url = reverse("assets:essential-asset-detail", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert "Secret Info" in response.content.decode()

    def test_detail_404_for_missing(self, client):
        import uuid
        url = reverse("assets:essential-asset-detail", kwargs={"pk": uuid.uuid4()})
        response = client.get(url)
        assert response.status_code == 404


class TestEssentialAssetCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:essential-asset-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client, superuser):
        url = reverse("assets:essential-asset-create")
        data = {
            "name": "New Asset",
            "type": EssentialAssetType.INFORMATION,
            "category": EssentialAssetCategory.STRATEGIC_DATA,
            "owner": superuser.pk,
            "confidentiality_level": DICLevel.MEDIUM,
            "integrity_level": DICLevel.MEDIUM,
            "availability_level": DICLevel.MEDIUM,
            "status": "identified",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert EssentialAsset.objects.filter(name="New Asset").exists()

    def test_create_post_invalid(self, client):
        url = reverse("assets:essential-asset-create")
        response = client.post(url, {})
        assert response.status_code == 200  # re-renders form with errors


class TestEssentialAssetUpdateView:
    def test_update_get_returns_200(self, client):
        asset = EssentialAssetFactory()
        url = reverse("assets:essential-asset-update", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client, superuser):
        asset = EssentialAssetFactory(owner=superuser)
        url = reverse("assets:essential-asset-update", kwargs={"pk": asset.pk})
        data = {
            "name": "Updated Asset",
            "type": asset.type,
            "category": asset.category,
            "owner": superuser.pk,
            "confidentiality_level": DICLevel.HIGH,
            "integrity_level": DICLevel.MEDIUM,
            "availability_level": DICLevel.MEDIUM,
            "status": asset.status,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        asset.refresh_from_db()
        assert asset.name == "Updated Asset"


class TestEssentialAssetDeleteView:
    def test_delete_get_returns_200(self, client):
        asset = EssentialAssetFactory()
        url = reverse("assets:essential-asset-delete", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_delete_post_removes_asset(self, client):
        asset = EssentialAssetFactory()
        url = reverse("assets:essential-asset-delete", kwargs={"pk": asset.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not EssentialAsset.objects.filter(pk=asset.pk).exists()


# ── Support Asset Views ──────────────────────────────────────


class TestSupportAssetListView:
    def test_list_returns_200(self, client):
        SupportAssetFactory()
        url = reverse("assets:support-asset-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_list_contains_asset(self, client):
        asset = SupportAssetFactory(name="Web Server")
        url = reverse("assets:support-asset-list")
        response = client.get(url)
        assert "Web Server" in response.content.decode()

    def test_list_filter_by_type(self, client):
        SupportAssetFactory(type=SupportAssetType.HARDWARE, category=SupportAssetCategory.SERVER)
        url = reverse("assets:support-asset-list")
        response = client.get(url, {"type": SupportAssetType.HARDWARE})
        assert response.status_code == 200


class TestSupportAssetDetailView:
    def test_detail_returns_200(self, client):
        asset = SupportAssetFactory()
        url = reverse("assets:support-asset-detail", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_shows_name(self, client):
        asset = SupportAssetFactory(name="DB Server")
        url = reverse("assets:support-asset-detail", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert "DB Server" in response.content.decode()


class TestSupportAssetCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:support-asset-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client, superuser):
        url = reverse("assets:support-asset-create")
        data = {
            "name": "New Server",
            "type": SupportAssetType.HARDWARE,
            "category": SupportAssetCategory.SERVER,
            "owner": superuser.pk,
            "status": "deployed",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert SupportAsset.objects.filter(name="New Server").exists()

    def test_create_post_invalid(self, client):
        url = reverse("assets:support-asset-create")
        response = client.post(url, {})
        assert response.status_code == 200


class TestSupportAssetUpdateView:
    def test_update_get_returns_200(self, client):
        asset = SupportAssetFactory()
        url = reverse("assets:support-asset-update", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client, superuser):
        asset = SupportAssetFactory(owner=superuser)
        url = reverse("assets:support-asset-update", kwargs={"pk": asset.pk})
        data = {
            "name": "Updated Server",
            "type": asset.type,
            "category": asset.category,
            "owner": superuser.pk,
            "status": asset.status,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        asset.refresh_from_db()
        assert asset.name == "Updated Server"


class TestSupportAssetDeleteView:
    def test_delete_get_returns_200(self, client):
        asset = SupportAssetFactory()
        url = reverse("assets:support-asset-delete", kwargs={"pk": asset.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_delete_post_removes_asset(self, client):
        asset = SupportAssetFactory()
        url = reverse("assets:support-asset-delete", kwargs={"pk": asset.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not SupportAsset.objects.filter(pk=asset.pk).exists()


# ── Dependency Views ─────────────────────────────────────────


class TestDependencyListView:
    def test_list_returns_200(self, client):
        DependencyFactory()
        url = reverse("assets:dependency-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_list_empty(self, client):
        url = reverse("assets:dependency-list")
        response = client.get(url)
        assert response.status_code == 200


class TestDependencyCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:dependency-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client):
        ea = EssentialAssetFactory()
        sa = SupportAssetFactory()
        url = reverse("assets:dependency-create")
        data = {
            "essential_asset": ea.pk,
            "support_asset": sa.pk,
            "dependency_type": DependencyType.RUNS_ON,
            "criticality": Criticality.HIGH,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert AssetDependency.objects.filter(
            essential_asset=ea, support_asset=sa
        ).exists()


class TestDependencyUpdateView:
    def test_update_get_returns_200(self, client):
        dep = DependencyFactory()
        url = reverse("assets:dependency-update", kwargs={"pk": dep.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client):
        dep = DependencyFactory()
        url = reverse("assets:dependency-update", kwargs={"pk": dep.pk})
        data = {
            "essential_asset": dep.essential_asset.pk,
            "support_asset": dep.support_asset.pk,
            "dependency_type": DependencyType.STORED_IN,
            "criticality": Criticality.MEDIUM,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        dep.refresh_from_db()
        assert dep.dependency_type == DependencyType.STORED_IN


class TestDependencyDeleteView:
    def test_delete_get_returns_200(self, client):
        dep = DependencyFactory()
        url = reverse("assets:dependency-delete", kwargs={"pk": dep.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_delete_post_removes_dependency(self, client):
        dep = DependencyFactory()
        url = reverse("assets:dependency-delete", kwargs={"pk": dep.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not AssetDependency.objects.filter(pk=dep.pk).exists()


# ── Group Views ──────────────────────────────────────────────


class TestGroupListView:
    def test_list_returns_200(self, client, superuser):
        AssetGroup.objects.create(
            name="Test Group", type=SupportAssetType.HARDWARE, owner=superuser
        )
        url = reverse("assets:group-list")
        response = client.get(url)
        assert response.status_code == 200


class TestGroupDetailView:
    def test_detail_returns_200(self, client, superuser):
        group = AssetGroup.objects.create(
            name="Test Group", type=SupportAssetType.HARDWARE, owner=superuser
        )
        url = reverse("assets:group-detail", kwargs={"pk": group.pk})
        response = client.get(url)
        assert response.status_code == 200


class TestGroupCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:group-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client, superuser):
        url = reverse("assets:group-create")
        data = {
            "name": "Server Group",
            "type": SupportAssetType.HARDWARE,
            "owner": superuser.pk,
            "status": "active",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert AssetGroup.objects.filter(name="Server Group").exists()


class TestGroupUpdateView:
    def test_update_get_returns_200(self, client, superuser):
        group = AssetGroup.objects.create(
            name="Old Name", type=SupportAssetType.HARDWARE, owner=superuser
        )
        url = reverse("assets:group-update", kwargs={"pk": group.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client, superuser):
        group = AssetGroup.objects.create(
            name="Old Name", type=SupportAssetType.HARDWARE, owner=superuser
        )
        url = reverse("assets:group-update", kwargs={"pk": group.pk})
        data = {
            "name": "New Name",
            "type": SupportAssetType.HARDWARE,
            "owner": superuser.pk,
            "status": "active",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        group.refresh_from_db()
        assert group.name == "New Name"


class TestGroupDeleteView:
    def test_delete_post_removes_group(self, client, superuser):
        group = AssetGroup.objects.create(
            name="Delete Me", type=SupportAssetType.HARDWARE, owner=superuser
        )
        url = reverse("assets:group-delete", kwargs={"pk": group.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not AssetGroup.objects.filter(pk=group.pk).exists()


# ── Supplier Type Views ──────────────────────────────────────


class TestSupplierTypeListView:
    def test_list_returns_200(self, client):
        SupplierTypeFactory()
        url = reverse("assets:supplier-type-list")
        response = client.get(url)
        assert response.status_code == 200


class TestSupplierTypeDetailView:
    def test_detail_returns_200(self, client):
        st = SupplierTypeFactory()
        url = reverse("assets:supplier-type-detail", kwargs={"pk": st.pk})
        response = client.get(url)
        assert response.status_code == 200


class TestSupplierTypeCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:supplier-type-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client):
        url = reverse("assets:supplier-type-create")
        data = {
            "name": "Cloud Provider",
            "description": "Cloud service providers",
            # Management form for the inline formset
            "requirements-TOTAL_FORMS": "0",
            "requirements-INITIAL_FORMS": "0",
            "requirements-MIN_NUM_FORMS": "0",
            "requirements-MAX_NUM_FORMS": "1000",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert SupplierType.objects.filter(name="Cloud Provider").exists()


class TestSupplierTypeUpdateView:
    def test_update_get_returns_200(self, client):
        st = SupplierTypeFactory()
        url = reverse("assets:supplier-type-update", kwargs={"pk": st.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client):
        st = SupplierTypeFactory()
        url = reverse("assets:supplier-type-update", kwargs={"pk": st.pk})
        data = {
            "name": "Updated Type",
            "description": "Updated description",
            "requirements-TOTAL_FORMS": "0",
            "requirements-INITIAL_FORMS": "0",
            "requirements-MIN_NUM_FORMS": "0",
            "requirements-MAX_NUM_FORMS": "1000",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        st.refresh_from_db()
        assert st.name == "Updated Type"


class TestSupplierTypeDeleteView:
    def test_delete_post_removes_type(self, client):
        st = SupplierTypeFactory()
        url = reverse("assets:supplier-type-delete", kwargs={"pk": st.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not SupplierType.objects.filter(pk=st.pk).exists()


# ── Supplier Views ───────────────────────────────────────────


class TestSupplierListView:
    def test_list_returns_200(self, client):
        SupplierFactory()
        url = reverse("assets:supplier-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_list_contains_supplier(self, client):
        supplier = SupplierFactory(name="Acme Corp")
        url = reverse("assets:supplier-list")
        response = client.get(url)
        assert "Acme Corp" in response.content.decode()

    def test_list_filter_by_status(self, client):
        SupplierFactory()
        url = reverse("assets:supplier-list")
        response = client.get(url, {"status": "active"})
        assert response.status_code == 200


class TestSupplierDetailView:
    def test_detail_returns_200(self, client):
        supplier = SupplierFactory()
        url = reverse("assets:supplier-detail", kwargs={"pk": supplier.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_shows_name(self, client):
        supplier = SupplierFactory(name="Detail Supplier")
        url = reverse("assets:supplier-detail", kwargs={"pk": supplier.pk})
        response = client.get(url)
        assert "Detail Supplier" in response.content.decode()


class TestSupplierCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:supplier-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client, superuser):
        st = SupplierTypeFactory()
        url = reverse("assets:supplier-create")
        data = {
            "name": "New Supplier",
            "type": st.pk,
            "criticality": SupplierCriticality.MEDIUM,
            "owner": superuser.pk,
            "status": "active",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Supplier.objects.filter(name="New Supplier").exists()


class TestSupplierUpdateView:
    def test_update_get_returns_200(self, client):
        supplier = SupplierFactory()
        url = reverse("assets:supplier-update", kwargs={"pk": supplier.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client, superuser):
        supplier = SupplierFactory(owner=superuser)
        url = reverse("assets:supplier-update", kwargs={"pk": supplier.pk})
        data = {
            "name": "Updated Supplier",
            "type": supplier.type.pk,
            "criticality": SupplierCriticality.HIGH,
            "owner": superuser.pk,
            "status": "active",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        supplier.refresh_from_db()
        assert supplier.name == "Updated Supplier"


class TestSupplierDeleteView:
    def test_delete_get_returns_200(self, client):
        supplier = SupplierFactory()
        url = reverse("assets:supplier-delete", kwargs={"pk": supplier.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_delete_post_removes_supplier(self, client):
        supplier = SupplierFactory()
        url = reverse("assets:supplier-delete", kwargs={"pk": supplier.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not Supplier.objects.filter(pk=supplier.pk).exists()


class TestSupplierArchiveView:
    def test_archive_sets_status_to_archived(self, client):
        supplier = SupplierFactory()
        url = reverse("assets:supplier-archive", kwargs={"pk": supplier.pk})
        response = client.post(url)
        assert response.status_code == 302
        supplier.refresh_from_db()
        assert supplier.status == "archived"


# ── Supplier Dependency Views ────────────────────────────────


class TestSupplierDependencyListView:
    def test_list_returns_200(self, client):
        SupplierDependencyFactory()
        url = reverse("assets:supplier-dependency-list")
        response = client.get(url)
        assert response.status_code == 200


class TestSupplierDependencyCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:supplier-dependency-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client):
        sa = SupportAssetFactory()
        supplier = SupplierFactory()
        url = reverse("assets:supplier-dependency-create")
        data = {
            "support_asset": sa.pk,
            "supplier": supplier.pk,
            "dependency_type": SupplierDependencyType.PROVIDED_BY,
            "criticality": Criticality.HIGH,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert SupplierDependency.objects.filter(
            support_asset=sa, supplier=supplier
        ).exists()


class TestSupplierDependencyUpdateView:
    def test_update_get_returns_200(self, client):
        dep = SupplierDependencyFactory()
        url = reverse("assets:supplier-dependency-update", kwargs={"pk": dep.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client):
        dep = SupplierDependencyFactory()
        url = reverse("assets:supplier-dependency-update", kwargs={"pk": dep.pk})
        data = {
            "support_asset": dep.support_asset.pk,
            "supplier": dep.supplier.pk,
            "dependency_type": SupplierDependencyType.MAINTAINED_BY,
            "criticality": Criticality.MEDIUM,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        dep.refresh_from_db()
        assert dep.dependency_type == SupplierDependencyType.MAINTAINED_BY


class TestSupplierDependencyDeleteView:
    def test_delete_post_removes_dependency(self, client):
        dep = SupplierDependencyFactory()
        url = reverse("assets:supplier-dependency-delete", kwargs={"pk": dep.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not SupplierDependency.objects.filter(pk=dep.pk).exists()


# ── Site Views ───────────────────────────────────────────────


class TestSiteListView:
    def test_list_returns_200(self, client, superuser):
        Site.objects.create(name="HQ", created_by=superuser)
        url = reverse("assets:site-list")
        response = client.get(url)
        assert response.status_code == 200


class TestSiteDetailView:
    def test_detail_returns_200(self, client, superuser):
        site = Site.objects.create(name="HQ", created_by=superuser)
        url = reverse("assets:site-detail", kwargs={"pk": site.pk})
        response = client.get(url)
        assert response.status_code == 200


class TestSiteCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:site-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client):
        url = reverse("assets:site-create")
        data = {
            "name": "New Site",
            "type": "siege",
            "status": "draft",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Site.objects.filter(name="New Site").exists()


class TestSiteUpdateView:
    def test_update_get_returns_200(self, client, superuser):
        site = Site.objects.create(name="Old Site", created_by=superuser)
        url = reverse("assets:site-update", kwargs={"pk": site.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_update_post_valid(self, client, superuser):
        site = Site.objects.create(name="Old Site", created_by=superuser)
        url = reverse("assets:site-update", kwargs={"pk": site.pk})
        data = {
            "name": "Updated Site",
            "type": "bureau",
            "status": "draft",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        site.refresh_from_db()
        assert site.name == "Updated Site"


class TestSiteDeleteView:
    def test_delete_post_removes_site(self, client, superuser):
        site = Site.objects.create(name="Delete Me", created_by=superuser)
        url = reverse("assets:site-delete", kwargs={"pk": site.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not Site.objects.filter(pk=site.pk).exists()


# ── Site-Asset Dependency Views ──────────────────────────────


class TestSiteAssetDependencyListView:
    def test_list_returns_200(self, client):
        url = reverse("assets:site-asset-dependency-list")
        response = client.get(url)
        assert response.status_code == 200


class TestSiteAssetDependencyCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:site-asset-dependency-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client, superuser):
        sa = SupportAssetFactory()
        site = Site.objects.create(name="DC1", created_by=superuser)
        url = reverse("assets:site-asset-dependency-create")
        data = {
            "support_asset": sa.pk,
            "site": site.pk,
            "dependency_type": SiteAssetDependencyType.LOCATED_AT,
            "criticality": Criticality.HIGH,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert SiteAssetDependency.objects.filter(
            support_asset=sa, site=site
        ).exists()


class TestSiteAssetDependencyUpdateView:
    def test_update_get_returns_200(self, client, superuser):
        sa = SupportAssetFactory()
        site = Site.objects.create(name="DC1", created_by=superuser)
        dep = SiteAssetDependency.objects.create(
            support_asset=sa, site=site,
            dependency_type=SiteAssetDependencyType.LOCATED_AT,
            criticality=Criticality.HIGH, created_by=superuser,
        )
        url = reverse("assets:site-asset-dependency-update", kwargs={"pk": dep.pk})
        response = client.get(url)
        assert response.status_code == 200


class TestSiteAssetDependencyDeleteView:
    def test_delete_post_removes_dependency(self, client, superuser):
        sa = SupportAssetFactory()
        site = Site.objects.create(name="DC1", created_by=superuser)
        dep = SiteAssetDependency.objects.create(
            support_asset=sa, site=site,
            dependency_type=SiteAssetDependencyType.LOCATED_AT,
            criticality=Criticality.HIGH, created_by=superuser,
        )
        url = reverse("assets:site-asset-dependency-delete", kwargs={"pk": dep.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not SiteAssetDependency.objects.filter(pk=dep.pk).exists()


# ── Site-Supplier Dependency Views ───────────────────────────


class TestSiteSupplierDependencyListView:
    def test_list_returns_200(self, client):
        url = reverse("assets:site-supplier-dependency-list")
        response = client.get(url)
        assert response.status_code == 200


class TestSiteSupplierDependencyCreateView:
    def test_create_get_returns_200(self, client):
        url = reverse("assets:site-supplier-dependency-create")
        response = client.get(url)
        assert response.status_code == 200

    def test_create_post_valid(self, client, superuser):
        site = Site.objects.create(name="DC1", created_by=superuser)
        supplier = SupplierFactory()
        url = reverse("assets:site-supplier-dependency-create")
        data = {
            "site": site.pk,
            "supplier": supplier.pk,
            "dependency_type": SiteSupplierDependencyType.MAINTAINED_BY,
            "criticality": Criticality.HIGH,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert SiteSupplierDependency.objects.filter(
            site=site, supplier=supplier
        ).exists()


class TestSiteSupplierDependencyDeleteView:
    def test_delete_post_removes_dependency(self, client, superuser):
        site = Site.objects.create(name="DC1", created_by=superuser)
        supplier = SupplierFactory()
        dep = SiteSupplierDependency.objects.create(
            site=site, supplier=supplier,
            dependency_type=SiteSupplierDependencyType.MAINTAINED_BY,
            criticality=Criticality.HIGH, created_by=superuser,
        )
        url = reverse("assets:site-supplier-dependency-delete", kwargs={"pk": dep.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not SiteSupplierDependency.objects.filter(pk=dep.pk).exists()


# ── Dependency Graph View ────────────────────────────────────


class TestDependencyGraphView:
    def test_graph_returns_200_empty(self, client):
        url = reverse("assets:dependency-graph")
        response = client.get(url)
        assert response.status_code == 200

    def test_graph_returns_200_with_data(self, client):
        DependencyFactory()
        SupplierDependencyFactory()
        url = reverse("assets:dependency-graph")
        response = client.get(url)
        assert response.status_code == 200


# ── Authentication required ──────────────────────────────────


class TestLoginRequired:
    def test_essential_asset_list_requires_login(self):
        c = Client()
        url = reverse("assets:essential-asset-list")
        response = c.get(url)
        assert response.status_code == 302
        assert "/login" in response.url or "/accounts/login" in response.url

    def test_support_asset_list_requires_login(self):
        c = Client()
        url = reverse("assets:support-asset-list")
        response = c.get(url)
        assert response.status_code == 302

    def test_supplier_list_requires_login(self):
        c = Client()
        url = reverse("assets:supplier-list")
        response = c.get(url)
        assert response.status_code == 302

    def test_dependency_list_requires_login(self):
        c = Client()
        url = reverse("assets:dependency-list")
        response = c.get(url)
        assert response.status_code == 302
