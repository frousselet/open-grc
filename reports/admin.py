from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("name", "report_type", "status", "created_at", "created_by")
    list_filter = ("report_type", "status")
    search_fields = ("name",)
