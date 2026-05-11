from django import forms
from .models import StudentExtra


class StudentExtraForm(forms.ModelForm):
    """Form for admin to add students manually"""

    class Meta:
        model = StudentExtra
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
            if StudentExtra.objects.filter(
                library=self.library, enrollment=enrollment
            ).exists():
                raise forms.ValidationError(
                    "This enrollment number already exists in this library."
                )
        return enrollment
