from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import string
import random
import uuid


class Library(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=12, unique=True, blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_libraries"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = "LIB-" + uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} [{self.code}]"


class LibraryMembership(models.Model):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("member", "Member"),
    ]
    library = models.ForeignKey(
        "Library", on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_users",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    must_change_password = models.BooleanField(default=True)

    class Meta:
        unique_together = ("library", "user")

    def __str__(self):
        return f"{self.user.email} - {self.library.name} ({self.role})"


class StudentExtra(models.Model):
    genchoice = [
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
        "Library", on_delete=models.CASCADE, related_name="students"
    )
    name = models.CharField(max_length=30, null=True, blank=True)
    enrollment = models.CharField(max_length=40, unique=True)
    address = models.CharField(max_length=40, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(
        max_length=10, choices=genchoice, default="Female", blank=True
    )
    photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} [{self.enrollment}]"

    @property
    def get_name(self):
        return self.name


class Book(models.Model):
    catchoice = [
        ("Education", "Education"),
        ("History", "History"),
        ("Novel", "Novel"),
        ("Fiction", "Fiction"),
        ("Thriller/Mystery", "Thriller/Mystery"),
        ("Romance", "Romance"),
        ("Scifi", "Sci-Fi"),
        ("Poetry", "Poetry"),
        ("Adventure", "Adventure"),
        ("Religion", "Religion & Spirituality"),
    ]

    langchoice = [
        ("English", "English"),
        ("Urdu", "Urdu"),
    ]

    library = models.ForeignKey(
        "Library", on_delete=models.CASCADE, related_name="books"
    )
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    author = models.CharField(max_length=40)
    category = models.CharField(max_length=30, choices=catchoice, default="Education")
    language = models.CharField(max_length=30, choices=langchoice, default="English")

    def __str__(self):
        return f"{self.name} [{self.quantity}]"


def get_expiry():
    return datetime.today() + timedelta(days=15)


class IssuedBook(models.Model):
    # Use ForeignKey for better relationships
    student = models.ForeignKey(
        StudentExtra, on_delete=models.CASCADE, null=True, blank=True
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)

    # Keep existing fields for backward compatibility
    enrollment = models.CharField(max_length=30)
    book_name = models.CharField(
        max_length=200, blank=True
    )  # Store book name separately

    issuedate = models.DateField(auto_now=True)
    expirydate = models.DateField(default=get_expiry)
    return_date = models.DateField(default=get_expiry)
    returned = models.BooleanField(default=False)  # Track if book is returned

    def __str__(self):
        return f"{self.enrollment} - {self.book_name}"

    def save(self, *args, **kwargs):
        # Auto-fill enrollment and book_name if foreign keys are provided
        if self.student and not self.enrollment:
            self.enrollment = self.student.enrollment
        if self.book and not self.book_name:
            self.book_name = self.book.name
        super().save(*args, **kwargs)


class AdminProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="admin_profile"
    )
    library = models.ForeignKey(
        "Library", on_delete=models.SET_NULL, null=True, blank=True
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to="admin_photos/", null=True, blank=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


def get_expiry():
    """Default return/expiry date: 14 days from today.
    Referenced by migrations 0010 and 0024 — do NOT remove."""
    return date.today() + timedelta(days=14)


def generate_library_code():
    """Generate a unique 6-character alphanumeric code, e.g. LIB-A3X9KZ."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "LIB-" + "".join(random.choices(chars, k=6))
        if not Library.objects.filter(code=code).exists():
            return code
