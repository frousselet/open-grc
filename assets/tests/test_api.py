import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from assets.tests.factories import (
    DependencyFactory,
    EssentialAssetFactory,
    SupplierDependencyFactory,
    SupplierFactory,
    SupplierTypeFactory,
    SupportAssetFactory,
)

pytestmark = pytest.mark.django_db


def _data(response):
    """Extract response payload, handling the StandardJSONRenderer wrapper."""
    body = response.json()
    if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
        return body["data"]
    return body


# ── EssentialAsset ViewSet ──────────────────────────────────


class TestEssentialAssetViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        EssentialAssetFactory.create_batch(2)
        response = self.client.get("/api/v1/assets/essential-assets/")
        assert response.status_code == 200
        assert len(_data(response)) >= 2

    def test_retrieve(self):
        ea = EssentialAssetFactory(name="Customer DB")
        response = self.client.get(f"/api/v1/assets/essential-assets/{ea.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Customer DB"

    def test_create(self):
        response = self.client.post(
            "/api/v1/assets/essential-assets/",
            {
                "name": "HR Data",
                "type": "information",
                "category": "strategic_data",
                "owner": str(self.user.pk),
                "confidentiality_level": 3,
                "integrity_level": 2,
                "availability_level": 2,
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        assert _data(response)["name"] == "HR Data"

    def test_update(self):
        ea = EssentialAssetFactory()
        response = self.client.patch(
            f"/api/v1/assets/essential-assets/{ea.pk}/",
            {"name": "Updated Asset"},
            format="json",
        )
        assert response.status_code == 200
        assert _data(response)["name"] == "Updated Asset"

    def test_delete(self):
        ea = EssentialAssetFactory()
        response = self.client.delete(f"/api/v1/assets/essential-assets/{ea.pk}/")
        assert response.status_code == 204

    def test_supporting_assets_action(self):
        ea = EssentialAssetFactory()
        sa = SupportAssetFactory()
        DependencyFactory(essential_asset=ea, support_asset=sa)
        response = self.client.get(
            f"/api/v1/assets/essential-assets/{ea.pk}/supporting-assets/"
        )
        assert response.status_code == 200
        assert len(_data(response)) >= 1

    def test_dependencies_action(self):
        ea = EssentialAssetFactory()
        response = self.client.get(
            f"/api/v1/assets/essential-assets/{ea.pk}/dependencies/"
        )
        assert response.status_code == 200

    def test_valuations_get(self):
        ea = EssentialAssetFactory()
        response = self.client.get(
            f"/api/v1/assets/essential-assets/{ea.pk}/valuations/"
        )
        assert response.status_code == 200

    def test_valuations_post(self):
        ea = EssentialAssetFactory()
        response = self.client.post(
            f"/api/v1/assets/essential-assets/{ea.pk}/valuations/",
            {
                "essential_asset": str(ea.pk),
                "evaluated_by": str(self.user.pk),
                "evaluation_date": "2025-01-15",
                "confidentiality_level": 3,
                "integrity_level": 3,
                "availability_level": 2,
                "justification": "Critical data",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_dashboard_action(self):
        EssentialAssetFactory()
        response = self.client.get(
            "/api/v1/assets/essential-assets/dashboard/"
        )
        assert response.status_code == 200
        data = _data(response)
        assert "total" in data
        assert "by_type" in data
        assert "by_status" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/assets/essential-assets/")
        assert response.status_code in (401, 403)


# ── SupportAsset ViewSet ────────────────────────────────────


class TestSupportAssetViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        SupportAssetFactory.create_batch(2)
        response = self.client.get("/api/v1/assets/support-assets/")
        assert response.status_code == 200

    def test_retrieve(self):
        sa = SupportAssetFactory(name="Web Server")
        response = self.client.get(f"/api/v1/assets/support-assets/{sa.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Web Server"

    def test_create(self):
        response = self.client.post(
            "/api/v1/assets/support-assets/",
            {
                "name": "New Server",
                "type": "hardware",
                "category": "server",
                "owner": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        sa = SupportAssetFactory()
        response = self.client.patch(
            f"/api/v1/assets/support-assets/{sa.pk}/",
            {"name": "Updated Server"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        sa = SupportAssetFactory()
        response = self.client.delete(f"/api/v1/assets/support-assets/{sa.pk}/")
        assert response.status_code == 204

    def test_essential_assets_action(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory()
        DependencyFactory(essential_asset=ea, support_asset=sa)
        response = self.client.get(
            f"/api/v1/assets/support-assets/{sa.pk}/essential-assets/"
        )
        assert response.status_code == 200
        assert len(_data(response)) >= 1

    def test_dependencies_action(self):
        sa = SupportAssetFactory()
        response = self.client.get(
            f"/api/v1/assets/support-assets/{sa.pk}/dependencies/"
        )
        assert response.status_code == 200

    def test_inherited_dic_action(self):
        sa = SupportAssetFactory()
        ea = EssentialAssetFactory(
            confidentiality_level=3,
            integrity_level=2,
            availability_level=1,
        )
        DependencyFactory(essential_asset=ea, support_asset=sa)
        response = self.client.get(
            f"/api/v1/assets/support-assets/{sa.pk}/inherited-dic/"
        )
        assert response.status_code == 200
        data = _data(response)
        assert "sources" in data
        assert len(data["sources"]) >= 1

    def test_children_action(self):
        parent = SupportAssetFactory()
        SupportAssetFactory(parent_asset=parent)
        response = self.client.get(
            f"/api/v1/assets/support-assets/{parent.pk}/children/"
        )
        assert response.status_code == 200

    def test_tree_action(self):
        response = self.client.get("/api/v1/assets/support-assets/tree/")
        assert response.status_code == 200

    def test_end_of_life_action(self):
        response = self.client.get("/api/v1/assets/support-assets/end-of-life/")
        assert response.status_code == 200

    def test_dashboard_action(self):
        SupportAssetFactory()
        response = self.client.get("/api/v1/assets/support-assets/dashboard/")
        assert response.status_code == 200
        data = _data(response)
        assert "total" in data
        assert "by_type" in data
        assert "orphan_count" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/assets/support-assets/")
        assert response.status_code in (401, 403)


# ── AssetDependency ViewSet ─────────────────────────────────


class TestAssetDependencyViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        DependencyFactory.create_batch(2)
        response = self.client.get("/api/v1/assets/dependencies/")
        assert response.status_code == 200

    def test_retrieve(self):
        dep = DependencyFactory()
        response = self.client.get(f"/api/v1/assets/dependencies/{dep.pk}/")
        assert response.status_code == 200

    def test_create(self):
        ea = EssentialAssetFactory()
        sa = SupportAssetFactory()
        response = self.client.post(
            "/api/v1/assets/dependencies/",
            {
                "essential_asset": str(ea.pk),
                "support_asset": str(sa.pk),
                "dependency_type": "runs_on",
                "criticality": "high",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        dep = DependencyFactory()
        response = self.client.patch(
            f"/api/v1/assets/dependencies/{dep.pk}/",
            {"criticality": "low"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        dep = DependencyFactory()
        response = self.client.delete(f"/api/v1/assets/dependencies/{dep.pk}/")
        assert response.status_code == 204

    def test_spof_action(self):
        dep = DependencyFactory()
        dep.is_single_point_of_failure = True
        dep.save()
        response = self.client.get("/api/v1/assets/dependencies/spof/")
        assert response.status_code == 200

    def test_detect_spof_get(self):
        response = self.client.get("/api/v1/assets/dependencies/detect-spof/")
        assert response.status_code == 200

    def test_detect_spof_post(self):
        response = self.client.post("/api/v1/assets/dependencies/detect-spof/")
        assert response.status_code == 200

    def test_graph_action(self):
        DependencyFactory()
        response = self.client.get("/api/v1/assets/dependencies/graph/")
        assert response.status_code == 200
        data = _data(response)
        assert "nodes" in data
        assert "edges" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/assets/dependencies/")
        assert response.status_code in (401, 403)


# ── AssetGroup ViewSet ──────────────────────────────────────


class TestAssetGroupViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        response = self.client.get("/api/v1/assets/groups/")
        assert response.status_code == 200

    def test_create(self):
        response = self.client.post(
            "/api/v1/assets/groups/",
            {
                "name": "Server Group",
                "type": "hardware",
                "owner": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201

    def test_retrieve(self):
        from assets.models import AssetGroup

        grp = AssetGroup.objects.create(
            name="G1", type="hardware", owner=self.user
        )
        response = self.client.get(f"/api/v1/assets/groups/{grp.pk}/")
        assert response.status_code == 200

    def test_update(self):
        from assets.models import AssetGroup

        grp = AssetGroup.objects.create(
            name="Old", type="hardware", owner=self.user
        )
        response = self.client.patch(
            f"/api/v1/assets/groups/{grp.pk}/",
            {"name": "New"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        from assets.models import AssetGroup

        grp = AssetGroup.objects.create(
            name="Del", type="hardware", owner=self.user
        )
        response = self.client.delete(f"/api/v1/assets/groups/{grp.pk}/")
        assert response.status_code == 204

    def test_members_get(self):
        from assets.models import AssetGroup

        grp = AssetGroup.objects.create(
            name="MG", type="hardware", owner=self.user
        )
        sa = SupportAssetFactory()
        grp.members.add(sa)
        response = self.client.get(f"/api/v1/assets/groups/{grp.pk}/members/")
        assert response.status_code == 200
        assert len(_data(response)) >= 1

    def test_members_post(self):
        from assets.models import AssetGroup

        grp = AssetGroup.objects.create(
            name="MP", type="hardware", owner=self.user
        )
        sa = SupportAssetFactory()
        response = self.client.post(
            f"/api/v1/assets/groups/{grp.pk}/members/",
            {"asset_ids": [str(sa.pk)]},
            format="json",
        )
        assert response.status_code == 200
        assert sa in grp.members.all()

    def test_remove_member(self):
        from assets.models import AssetGroup

        grp = AssetGroup.objects.create(
            name="RM", type="hardware", owner=self.user
        )
        sa = SupportAssetFactory()
        grp.members.add(sa)
        response = self.client.delete(
            f"/api/v1/assets/groups/{grp.pk}/members/{sa.pk}/"
        )
        assert response.status_code == 204
        assert sa not in grp.members.all()

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/assets/groups/")
        assert response.status_code in (401, 403)


# ── Supplier ViewSet ────────────────────────────────────────


class TestSupplierViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        SupplierFactory.create_batch(2)
        response = self.client.get("/api/v1/assets/suppliers/")
        assert response.status_code == 200

    def test_retrieve(self):
        s = SupplierFactory(name="Vendor A")
        response = self.client.get(f"/api/v1/assets/suppliers/{s.pk}/")
        assert response.status_code == 200
        assert _data(response)["name"] == "Vendor A"

    def test_create(self):
        st = SupplierTypeFactory()
        response = self.client.post(
            "/api/v1/assets/suppliers/",
            {
                "name": "New Vendor",
                "type": str(st.pk),
                "criticality": "high",
                "owner": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        s = SupplierFactory()
        response = self.client.patch(
            f"/api/v1/assets/suppliers/{s.pk}/",
            {"name": "Updated Vendor"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        s = SupplierFactory()
        response = self.client.delete(f"/api/v1/assets/suppliers/{s.pk}/")
        assert response.status_code == 204

    def test_archive_action(self):
        s = SupplierFactory()
        response = self.client.post(
            f"/api/v1/assets/suppliers/{s.pk}/archive/"
        )
        assert response.status_code == 200
        assert _data(response)["status"] == "archived"

    def test_requirements_get(self):
        s = SupplierFactory()
        response = self.client.get(
            f"/api/v1/assets/suppliers/{s.pk}/requirements/"
        )
        assert response.status_code == 200

    def test_requirements_post(self):
        s = SupplierFactory()
        response = self.client.post(
            f"/api/v1/assets/suppliers/{s.pk}/requirements/",
            {
                "supplier": str(s.pk),
                "title": "SLA 99.9%",
                "description": "Uptime requirement",
                "compliance_status": "not_assessed",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_dashboard_action(self):
        SupplierFactory()
        response = self.client.get("/api/v1/assets/suppliers/dashboard/")
        assert response.status_code == 200
        data = _data(response)
        assert "total" in data
        assert "by_type" in data
        assert "by_criticality" in data

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/assets/suppliers/")
        assert response.status_code in (401, 403)


# ── SupplierDependency ViewSet ──────────────────────────────


class TestSupplierDependencyViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        SupplierDependencyFactory()
        response = self.client.get("/api/v1/assets/supplier-dependencies/")
        assert response.status_code == 200

    def test_retrieve(self):
        sd = SupplierDependencyFactory()
        response = self.client.get(
            f"/api/v1/assets/supplier-dependencies/{sd.pk}/"
        )
        assert response.status_code == 200

    def test_create(self):
        sa = SupportAssetFactory()
        s = SupplierFactory()
        response = self.client.post(
            "/api/v1/assets/supplier-dependencies/",
            {
                "support_asset": str(sa.pk),
                "supplier": str(s.pk),
                "dependency_type": "provides",
                "criticality": "medium",
            },
            format="json",
        )
        assert response.status_code == 201

    def test_update(self):
        sd = SupplierDependencyFactory()
        response = self.client.patch(
            f"/api/v1/assets/supplier-dependencies/{sd.pk}/",
            {"criticality": "low"},
            format="json",
        )
        assert response.status_code == 200

    def test_delete(self):
        sd = SupplierDependencyFactory()
        response = self.client.delete(
            f"/api/v1/assets/supplier-dependencies/{sd.pk}/"
        )
        assert response.status_code == 204

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get("/api/v1/assets/supplier-dependencies/")
        assert response.status_code in (401, 403)


# ── BUG 1: Supplier.type FK resolution ────────────────────


class TestSupplierTypeFKResolution:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)

    def test_create_supplier_with_type_id(self):
        st = SupplierTypeFactory(name="Cloud Provider")
        response = self.client.post(
            "/api/v1/assets/suppliers/",
            {
                "name": "AWS",
                "type": st.pk,
                "owner": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        data = _data(response)
        assert data["type"] == st.pk

    def test_create_supplier_with_null_type(self):
        response = self.client.post(
            "/api/v1/assets/suppliers/",
            {
                "name": "Acme Corp",
                "type": None,
                "owner": str(self.user.pk),
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        assert _data(response)["type"] is None


# ── BUG 2: SupplierDependency.dependency_type choices ──────


class TestSupplierDependencyTypeChoices:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.sa = SupportAssetFactory()
        self.supplier = SupplierFactory()

    def _create_dep(self, dep_type):
        return self.client.post(
            "/api/v1/assets/supplier-dependencies/",
            {
                "support_asset": str(self.sa.pk),
                "supplier": str(self.supplier.pk),
                "dependency_type": dep_type,
                "criticality": "medium",
            },
            format="json",
        )

    def test_provides(self):
        response = self._create_dep("provides")
        assert response.status_code == 201, response.json()

    def test_hosts(self):
        response = self._create_dep("hosts")
        assert response.status_code == 201, response.json()

    def test_other_still_works(self):
        response = self._create_dep("other")
        assert response.status_code == 201, response.json()

    def test_maintains(self):
        response = self._create_dep("maintains")
        assert response.status_code == 201, response.json()


# ── Batch create endpoints ─────────────────────────────────


class TestBatchCreateEssentialAssets:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/assets/essential-assets/batch/"

    def test_batch_create_success(self):
        items = [
            {
                "name": f"Asset {i}",
                "type": "information",
                "category": "strategic_data",
                "owner": str(self.user.pk),
                "confidentiality_level": 2,
                "integrity_level": 2,
                "availability_level": 2,
            }
            for i in range(5)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["total"] == 5
        assert data["created"] == 5
        assert data["errors"] == 0
        assert data["status"] == "completed"

    def test_batch_create_partial_error(self):
        items = [
            {
                "name": "Valid Asset",
                "type": "information",
                "category": "strategic_data",
                "owner": str(self.user.pk),
                "confidentiality_level": 2,
                "integrity_level": 2,
                "availability_level": 2,
            },
            {
                # Missing required field 'name'
                "type": "information",
                "category": "strategic_data",
                "owner": str(self.user.pk),
            },
            {
                "name": "Another Valid Asset",
                "type": "information",
                "category": "strategic_data",
                "owner": str(self.user.pk),
                "confidentiality_level": 3,
                "integrity_level": 3,
                "availability_level": 3,
            },
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 2
        assert data["errors"] == 1
        assert data["status"] == "completed_with_errors"

    def test_batch_create_exceeds_limit(self):
        items = [{"name": f"A{i}"} for i in range(101)]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 400

    def test_batch_create_empty_list(self):
        response = self.client.post(self.url, {"items": []}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["total"] == 0
        assert data["created"] == 0
        assert data["errors"] == 0

    def test_batch_create_permission_denied(self):
        non_admin = UserFactory(is_superuser=False)
        client = APIClient()
        client.force_authenticate(user=non_admin)
        items = [
            {
                "name": "Asset",
                "type": "information",
                "category": "strategic_data",
                "owner": str(non_admin.pk),
                "confidentiality_level": 2,
                "integrity_level": 2,
                "availability_level": 2,
            }
        ]
        response = client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 403


class TestBatchCreateSuppliers:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_superuser=True)
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/assets/suppliers/batch/"

    def test_batch_create_suppliers(self):
        st = SupplierTypeFactory(name="SaaS")
        items = [
            {
                "name": f"Supplier {i}",
                "type": st.pk,
                "owner": str(self.user.pk),
            }
            for i in range(3)
        ]
        response = self.client.post(self.url, {"items": items}, format="json")
        assert response.status_code == 200
        body = response.json()
        data = body.get("data", body)
        assert data["created"] == 3
        assert data["errors"] == 0
