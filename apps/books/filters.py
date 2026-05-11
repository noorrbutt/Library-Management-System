# apps/books/filters.py
import django_filters
from .models import Book


class BookFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(
        field_name="category",
        choices=Book.CATEGORY_CHOICES,
        empty_label="All Categories",
    )
    language = django_filters.ChoiceFilter(
        field_name="language",
        choices=Book.LANGUAGE_CHOICES,
        empty_label="All Languages",
    )

    class Meta:
        model = Book
        fields = ["category", "language"]
