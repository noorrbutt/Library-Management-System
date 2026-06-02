from django import forms
from .models import Book
from apps.students.models import StudentExtra
from datetime import date, timedelta


class BookForm(forms.ModelForm):
    category = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "lms-input",
                "list": "category-options",
                "placeholder": "Select or type a category",
                "autocomplete": "off",
            }
        ),
    )
    language = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "lms-input",
                "list": "language-options",
                "placeholder": "Select or type a language",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Book
        fields = ["name", "quantity", "author", "category", "language"]


class IssuedBookForm(forms.Form):
    book = forms.ModelChoiceField(
        queryset=Book.objects.filter(quantity__gt=0),
        empty_label="Select Book",
        label="Book Name",
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    student = forms.ModelChoiceField(
        queryset=StudentExtra.objects.all(),
        empty_label="Select Student",
        label="Student",
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Return Date",
    )

    def __init__(self, library, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # compute default return date at form instantiation (fixes class-level evaluation bug)
        self.fields["return_date"].initial = date.today() + timedelta(days=15)
        self.fields["book"].queryset = Book.objects.filter(
            library=library, quantity__gt=0
        )
        self.fields["student"].queryset = StudentExtra.objects.filter(library=library)
        self.fields["book"].label_from_instance = (
            lambda obj: f"{obj.name} (Available: {obj.quantity})"
        )
        self.fields["student"].label_from_instance = (
            lambda obj: f"{obj.name} - {obj.enrollment}"
        )
