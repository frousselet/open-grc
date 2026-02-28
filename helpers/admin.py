from django.contrib import admin

from .models import HelpContent


@admin.register(HelpContent)
class HelpContentAdmin(admin.ModelAdmin):
    list_display = ("key", "language", "title", "updated_at")
    list_filter = ("language",)
    search_fields = ("key", "title", "body")
    ordering = ("key", "language")
