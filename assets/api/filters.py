import django_filters

from assets.models import (
    AssetDependency,
    AssetGroup,
    EssentialAsset,
    Supplier,
    SupportAsset,
)


class EssentialAssetFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")
    owner = django_filters.UUIDFilter(field_name="owner_id")
    confidentiality_level = django_filters.NumberFilter()
    confidentiality_level__gte = django_filters.NumberFilter(
        field_name="confidentiality_level", lookup_expr="gte"
    )
    integrity_level__gte = django_filters.NumberFilter(
        field_name="integrity_level", lookup_expr="gte"
    )
    availability_level__gte = django_filters.NumberFilter(
        field_name="availability_level", lookup_expr="gte"
    )
    has_supporting_assets = django_filters.BooleanFilter(
        method="filter_has_supporting_assets"
    )

    class Meta:
        model = EssentialAsset
        fields = {
            "type": ["exact"],
            "category": ["exact"],
            "status": ["exact"],
            "personal_data": ["exact"],
            "data_classification": ["exact"],
        }

    def filter_has_supporting_assets(self, queryset, name, value):
        if value:
            return queryset.filter(dependencies_as_essential__isnull=False).distinct()
        return queryset.filter(dependencies_as_essential__isnull=True)


class SupportAssetFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")
    owner = django_filters.UUIDFilter(field_name="owner_id")
    end_of_life_before = django_filters.DateFilter(
        field_name="end_of_life_date", lookup_expr="lte"
    )
    inherited_confidentiality__gte = django_filters.NumberFilter(
        field_name="inherited_confidentiality", lookup_expr="gte"
    )
    inherited_integrity__gte = django_filters.NumberFilter(
        field_name="inherited_integrity", lookup_expr="gte"
    )
    inherited_availability__gte = django_filters.NumberFilter(
        field_name="inherited_availability", lookup_expr="gte"
    )
    is_orphan = django_filters.BooleanFilter(method="filter_is_orphan")
    group = django_filters.UUIDFilter(field_name="groups__id")

    class Meta:
        model = SupportAsset
        fields = {
            "type": ["exact"],
            "category": ["exact"],
            "status": ["exact"],
            "exposure_level": ["exact"],
            "environment": ["exact"],
        }

    def filter_is_orphan(self, queryset, name, value):
        if value:
            return queryset.filter(dependencies_as_support__isnull=True)
        return queryset.filter(dependencies_as_support__isnull=False).distinct()


class AssetDependencyFilter(django_filters.FilterSet):
    essential_asset = django_filters.UUIDFilter(field_name="essential_asset_id")
    support_asset = django_filters.UUIDFilter(field_name="support_asset_id")

    class Meta:
        model = AssetDependency
        fields = {
            "dependency_type": ["exact"],
            "criticality": ["exact"],
            "is_single_point_of_failure": ["exact"],
        }


class AssetGroupFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")

    class Meta:
        model = AssetGroup
        fields = {
            "type": ["exact"],
            "status": ["exact"],
        }


class SupplierFilter(django_filters.FilterSet):
    scope = django_filters.UUIDFilter(field_name="scope_id")
    owner = django_filters.UUIDFilter(field_name="owner_id")
    contract_end_before = django_filters.DateFilter(
        field_name="contract_end_date", lookup_expr="lte"
    )

    class Meta:
        model = Supplier
        fields = {
            "type": ["exact"],
            "criticality": ["exact"],
            "status": ["exact"],
        }
