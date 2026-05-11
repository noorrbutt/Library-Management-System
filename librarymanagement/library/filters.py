# library/filters.py
import django_filters
from apps.books.models import Book
from apps.students.models import StudentExtra


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


class StudentFilter(django_filters.FilterSet):
    gender = django_filters.ChoiceFilter(
        field_name="gender", choices=StudentExtra.GENDER_CHOICES, empty_label="Genders"
    )

    class Meta:
        model = StudentExtra
        fields = ["gender"]
