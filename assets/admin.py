from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    AssetDependency,
    AssetGroup,
    AssetValuation,
    EssentialAsset,
    SupportAsset,
)


class AssetValuationInline(admin.TabularInline):
    model = AssetValuation
    extra = 0
    readonly_fields = ("id", "created_at")


class EssentialDependencyInline(admin.TabularInline):
    model = AssetDependency
    fk_name = "essential_asset"
    extra = 0
    readonly_fields = ("id",)


class SupportDependencyInline(admin.TabularInline):
    model = AssetDependency
    fk_name = "support_asset"
    extra = 0
    readonly_fields = ("id",)


@admin.register(EssentialAsset)
class EssentialAssetAdmin(SimpleHistoryAdmin):
    list_display = (
        "reference", "name", "type", "category", "owner",
        "confidentiality_level", "integrity_level", "availability_level",
        "status",
    )
    list_filter = ("type", "category", "status", "data_classification", "personal_data")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("related_activities",)
    inlines = [EssentialDependencyInline, AssetValuationInline]


@admin.register(SupportAsset)
class SupportAssetAdmin(SimpleHistoryAdmin):
    list_display = (
        "reference", "name", "type", "category", "owner",
        "inherited_confidentiality", "inherited_integrity", "inherited_availability",
        "environment", "status", "end_of_life_date",
    )
    list_filter = ("type", "category", "status", "environment", "exposure_level")
    search_fields = ("reference", "name", "description", "hostname", "ip_address")
    readonly_fields = (
        "id", "created_at", "updated_at",
        "inherited_confidentiality", "inherited_integrity", "inherited_availability",
    )
    inlines = [SupportDependencyInline]


@admin.register(AssetDependency)
class AssetDependencyAdmin(SimpleHistoryAdmin):
    list_display = (
        "essential_asset", "support_asset", "dependency_type",
        "criticality", "is_single_point_of_failure",
    )
    list_filter = ("dependency_type", "criticality", "is_single_point_of_failure")
    search_fields = (
        "essential_asset__reference", "essential_asset__name",
        "support_asset__reference", "support_asset__name",
    )
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AssetGroup)
class AssetGroupAdmin(SimpleHistoryAdmin):
    list_display = ("name", "type", "scope", "owner", "status", "member_count")
    list_filter = ("type", "status")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("members",)

    @admin.display(description="Membres")
    def member_count(self, obj):
        return obj.members.count()


@admin.register(AssetValuation)
class AssetValuationAdmin(admin.ModelAdmin):
    list_display = (
        "essential_asset", "evaluation_date",
        "confidentiality_level", "integrity_level", "availability_level",
        "evaluated_by",
    )
    list_filter = ("evaluation_date",)
    search_fields = ("essential_asset__reference", "essential_asset__name")
    readonly_fields = ("id", "created_at")
