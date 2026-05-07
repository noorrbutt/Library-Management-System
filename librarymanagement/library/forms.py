from django import forms
from django.contrib.auth.models import User
from . import models
from datetime import date, timedelta


# -------------------- CREATE LIBRARY FORM --------------------
class CreateLibraryForm(forms.Form):
    library_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "e.g. City Public Library"}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Choose a username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com"})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Create a password", "id": "id_password1"}
        ),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Repeat password", "id": "id_password2"}
        ),
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


# -------------------- ADMIN LOGIN FORM --------------------
class AdminLoginForm(forms.Form):
    """Simple login form for use with AdminLoginView (library + username + password)"""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Your username"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Your password"}),
    )


# -------------------- BOOK FORMS --------------------
class BookForm(forms.ModelForm):
    class Meta:
        model = models.Book
        fields = ["name", "quantity", "author", "category", "language"]


class IssuedBookForm(forms.Form):
    default_return_date = date.today() + timedelta(days=15)

    book = forms.ModelChoiceField(
        queryset=models.Book.objects.filter(quantity__gt=0),
        empty_label="Select Book",
        label="Book Name",
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    student = forms.ModelChoiceField(
        queryset=models.StudentExtra.objects.all(),
        empty_label="Select Student",
        label="Student",
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    return_date = forms.DateField(
        initial=default_return_date,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Return Date",
    )

    def __init__(self, library, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["book"].queryset = models.Book.objects.filter(
            library=library, quantity__gt=0
        )
        self.fields["student"].queryset = models.StudentExtra.objects.filter(
            library=library
        )
        self.fields["book"].label_from_instance = (
            lambda obj: f"{obj.name} (Available: {obj.quantity})"
        )
        self.fields["student"].label_from_instance = (
            lambda obj: f"{obj.name} - {obj.enrollment}"
        )


# -------------------- STUDENT FORMS --------------------
class StudentExtraForm(forms.ModelForm):
    """Form for admin to add students manually"""

    class Meta:
        model = models.StudentExtra
        fields = ["name", "enrollment", "address", "phone", "gender"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "Full Name", "class": "form-control"}
            ),
            "enrollment": forms.TextInput(
                attrs={"placeholder": "Enrollment Number", "class": "form-control"}
            ),
            "address": forms.TextInput(
                attrs={"placeholder": "Address", "class": "form-control"}
            ),
            "phone": forms.NumberInput(
                attrs={"placeholder": "Phone Number", "class": "form-control"}
            ),
            "gender": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, library, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.library = library

    def clean_enrollment(self):
        enrollment = self.cleaned_data.get("enrollment")
        if enrollment:
            # Check if enrollment number already exists in this library
            if models.StudentExtra.objects.filter(
                library=self.library, enrollment=enrollment
            ).exists():
                raise forms.ValidationError(
                    "This enrollment number already exists in this library."
                )
        return enrollment
        return enrollment
