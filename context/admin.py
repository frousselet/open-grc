from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Activity,
    Issue,
    Objective,
    Responsibility,
    Role,
    Scope,
    Site,
    Stakeholder,
    StakeholderExpectation,
    SwotAnalysis,
    SwotItem,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "created_at")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")


@admin.register(Scope)
class ScopeAdmin(SimpleHistoryAdmin):
    list_display = ("name", "version", "status", "effective_date", "review_date", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("included_sites", "excluded_sites", "tags")


@admin.register(Site)
class SiteAdmin(SimpleHistoryAdmin):
    list_display = ("name", "type", "status", "parent_site", "is_approved", "created_at")
    list_filter = ("type", "status")
    search_fields = ("name", "description", "address")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("tags",)


@admin.register(Issue)
class IssueAdmin(SimpleHistoryAdmin):
    list_display = ("name", "type", "category", "impact_level", "status", "trend")
    list_filter = ("type", "category", "impact_level", "status", "trend")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "related_stakeholders", "tags")


class StakeholderExpectationInline(admin.TabularInline):
    model = StakeholderExpectation
    extra = 1
    readonly_fields = ("id",)


@admin.register(Stakeholder)
class StakeholderAdmin(SimpleHistoryAdmin):
    list_display = (
        "name", "type", "category", "influence_level", "interest_level", "status",
    )
    list_filter = ("type", "category", "influence_level", "interest_level", "status")
    search_fields = ("name", "description", "contact_name")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "tags")
    inlines = [StakeholderExpectationInline]


@admin.register(Objective)
class ObjectiveAdmin(SimpleHistoryAdmin):
    list_display = (
        "reference", "name", "category", "type", "status",
        "progress_percentage", "owner", "target_date",
    )
    list_filter = ("category", "type", "status", "measurement_frequency")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "related_issues", "related_stakeholders", "tags")


class SwotItemInline(admin.TabularInline):
    model = SwotItem
    extra = 1
    readonly_fields = ("id",)


@admin.register(SwotAnalysis)
class SwotAnalysisAdmin(SimpleHistoryAdmin):
    list_display = ("name", "analysis_date", "status", "validated_by", "validated_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "tags")
    inlines = [SwotItemInline]


class ResponsibilityInline(admin.TabularInline):
    model = Responsibility
    extra = 1
    readonly_fields = ("id",)


@admin.register(Role)
class RoleAdmin(SimpleHistoryAdmin):
    list_display = ("name", "type", "status", "is_mandatory", "compliance_alert")
    list_filter = ("type", "status", "is_mandatory")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "assigned_users", "tags")
    inlines = [ResponsibilityInline]

    @admin.display(description="Alerte conformité")
    def compliance_alert(self, obj):
        return obj.compliance_alert or "—"


@admin.register(Activity)
class ActivityAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "name", "type", "criticality", "owner", "status")
    list_filter = ("type", "criticality", "status")
    search_fields = ("reference", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("scopes", "related_stakeholders", "related_objectives", "tags")
