from django.db import models
from django.contrib.auth.models import User
from apps.core.models import Library


class StudentExtra(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
    ]
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_profile",
    )
    library = models.ForeignKey(
        Library, on_delete=models.CASCADE, related_name="students"
    )
    name = models.CharField(max_length=30, null=True, blank=True)
    enrollment = models.CharField(max_length=40, db_index=True)
    address = models.CharField(max_length=40, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, default="Female", blank=True
    )
    photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "library"
        unique_together = [("enrollment", "library")]

    def __str__(self):
        display_name = self.name or 'Unnamed'
        return f'{display_name} [{self.enrollment}]'
