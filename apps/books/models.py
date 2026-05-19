from django.db import models
from datetime import datetime, timedelta
from apps.core.models import Library
from apps.students.models import StudentExtra


class Book(models.Model):
    CATEGORY_CHOICES = [
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

    LANGUAGE_CHOICES = [
        ("English", "English"),
        ("Urdu", "Urdu"),
    ]

    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="books")
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    author = models.CharField(max_length=40)
    category = models.CharField(max_length=50, default="Education")
    language = models.CharField(max_length=30, default="English")

    class Meta:
        app_label = "library"

    def __str__(self):
        return f"{self.name} [{self.quantity}]"


def get_expiry():
    return datetime.today() + timedelta(days=15)


class IssuedBook(models.Model):
    # ForeignKey for better relationships
    student = models.ForeignKey(
        StudentExtra, on_delete=models.CASCADE, null=True, blank=True
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)

    enrollment = models.CharField(max_length=30)
    book_name = models.CharField(max_length=200, blank=True)

    issuedate = models.DateField(auto_now=True)
    expirydate = models.DateField(default=get_expiry)
    return_date = models.DateField(default=get_expiry)
    returned = models.BooleanField(default=False)  # Track if book is returned

    class Meta:
        app_label = "library"

    def __str__(self):
        return f"{self.enrollment} - {self.book_name}"

    def save(self, *args, **kwargs):
        # Auto-fill enrollment and book_name if foreign keys are provided
        if self.student and not self.enrollment:
            self.enrollment = self.student.enrollment
        if self.book and not self.book_name:
            self.book_name = self.book.name
        super().save(*args, **kwargs)
