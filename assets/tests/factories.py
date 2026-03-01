import factory

from accounts.tests.factories import UserFactory
from assets.constants import (
    DependencyType,
    DICLevel,
    EssentialAssetCategory,
    EssentialAssetType,
    SupplierCriticality,
    SupplierDependencyType,
    SupportAssetCategory,
    SupportAssetType,
)
from assets.models.dependency import AssetDependency
from assets.models.essential_asset import EssentialAsset
from assets.models.supplier import (
    Supplier,
    SupplierDependency,
    SupplierRequirement,
    SupplierRequirementReview,
    SupplierType,
)
from assets.models.support_asset import SupportAsset
from context.constants import Criticality
from context.tests.factories import ScopeFactory


class EssentialAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EssentialAsset

    scope = factory.SubFactory(ScopeFactory)
    reference = factory.Sequence(lambda n: f"EA-{n:03d}")
    name = factory.Sequence(lambda n: f"Essential Asset {n}")
    type = EssentialAssetType.INFORMATION
    category = EssentialAssetCategory.STRATEGIC_DATA
    owner = factory.SubFactory(UserFactory)
    confidentiality_level = DICLevel.MEDIUM
    integrity_level = DICLevel.MEDIUM
    availability_level = DICLevel.MEDIUM


class SupportAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupportAsset

    scope = factory.SubFactory(ScopeFactory)
    reference = factory.Sequence(lambda n: f"SA-{n:03d}")
    name = factory.Sequence(lambda n: f"Support Asset {n}")
    type = SupportAssetType.HARDWARE
    category = SupportAssetCategory.SERVER
    owner = factory.SubFactory(UserFactory)


class DependencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetDependency

    essential_asset = factory.SubFactory(EssentialAssetFactory)
    support_asset = factory.SubFactory(SupportAssetFactory)
    dependency_type = DependencyType.RUNS_ON
    criticality = Criticality.HIGH


class SupplierTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierType

    name = factory.Sequence(lambda n: f"Supplier Type {n}")


class SupplierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Supplier

    scope = factory.SubFactory(ScopeFactory)
    reference = factory.Sequence(lambda n: f"SUPP-{n:03d}")
    name = factory.Sequence(lambda n: f"Supplier {n}")
    type = factory.SubFactory(SupplierTypeFactory)
    criticality = SupplierCriticality.MEDIUM
    owner = factory.SubFactory(UserFactory)


class SupplierRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierRequirement

    supplier = factory.SubFactory(SupplierFactory)
    title = factory.Sequence(lambda n: f"Requirement {n}")
    description = "Test requirement description"


class SupplierRequirementReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierRequirementReview

    supplier_requirement = factory.SubFactory(SupplierRequirementFactory)
    review_date = factory.LazyFunction(lambda: __import__("datetime").date.today())
    reviewer = factory.SubFactory(UserFactory)
    result = "compliant"
    comment = "Reviewed and found compliant."


class SupplierDependencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SupplierDependency

    support_asset = factory.SubFactory(SupportAssetFactory)
    supplier = factory.SubFactory(SupplierFactory)
    dependency_type = SupplierDependencyType.PROVIDED_BY
    criticality = Criticality.HIGH
