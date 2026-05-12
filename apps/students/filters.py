# apps/students/filters.py
import django_filters
from .models import StudentExtra


class StudentFilter(django_filters.FilterSet):
    gender = django_filters.ChoiceFilter(
        field_name="gender", choices=StudentExtra.GENDER_CHOICES, empty_label="Genders"
    )

    class Meta:
        model = StudentExtra
        fields = ["gender"]
