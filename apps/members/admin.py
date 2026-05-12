"""
Admin registrations for members app models.
"""

from django.contrib import admin
from .models import LibraryMembership


@admin.register(LibraryMembership)
class LibraryMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "library", "role", "joined_at"]
    list_filter = ["role"]
    search_fields = ["user__username", "library__name"]
