"""
Admin registrations for books app models.
"""

from django.contrib import admin
from .models import Book, IssuedBook


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["name", "author", "category", "language", "quantity", "library"]
    search_fields = ["name", "author"]
    list_filter = ["category", "language"]


@admin.register(IssuedBook)
class IssuedBookAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "book_name", "issuedate", "return_date", "returned"]
    list_filter = ["returned"]
