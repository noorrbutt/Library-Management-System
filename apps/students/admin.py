"""
Admin registrations for students app models.
"""

from django.contrib import admin
from .models import StudentExtra


@admin.register(StudentExtra)
class StudentExtraAdmin(admin.ModelAdmin):
    list_display = ["name", "enrollment", "gender", "library"]
    search_fields = ["name", "enrollment"]
    list_filter = ["gender"]
