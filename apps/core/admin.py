"""
Admin registrations for core app models.
"""

from django.contrib import admin
from .models import Library, AdminProfile


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "owner", "created_at"]
    search_fields = ["name", "code"]
    readonly_fields = ["code", "created_at"]


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "library", "phone"]
    search_fields = ["user__username"]
