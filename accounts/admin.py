from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import AccessLog, Group, Permission, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "job_title", "department", "phone")}),
        ("Préférences", {"fields": ("language", "timezone")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Sécurité", {"fields": ("failed_login_attempts", "locked_until", "password_changed_at")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login", "password_changed_at")
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2"),
        }),
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system", "user_count", "permission_count")
    list_filter = ("is_system",)
    search_fields = ("name",)
    filter_horizontal = ("permissions", "users", "allowed_scopes")

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = "Utilisateurs"

    def permission_count(self, obj):
        return obj.permissions.count()
    permission_count.short_description = "Permissions"


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "name", "module", "feature", "action", "is_system")
    list_filter = ("module", "action", "is_system")
    search_fields = ("codename", "name")
    readonly_fields = ("codename", "name", "module", "feature", "action", "is_system")


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "email_attempted", "event_type", "ip_address", "failure_reason")
    list_filter = ("event_type", "failure_reason")
    search_fields = ("email_attempted", "ip_address")
    readonly_fields = ("timestamp", "user", "email_attempted", "event_type", "ip_address", "user_agent", "failure_reason", "metadata")
    date_hierarchy = "timestamp"
