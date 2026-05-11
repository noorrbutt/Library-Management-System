from django.test import TestCase
from django.contrib.auth.models import User
from apps.core.models import Library
from apps.students.models import StudentExtra
from apps.books.models import Book, IssuedBook, get_expiry
from datetime import datetime, timedelta


class BookModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.library = Library.objects.create(name="Test Library", owner=self.user)

    def test_str(self):
        book = Book.objects.create(
            library=self.library,
            name="Test Book",
            quantity=5,
            author="Author",
            category="Education",
            language="English",
        )
        self.assertEqual(str(book), "Test Book [5]")

    def test_meta_app_label(self):
        self.assertEqual(Book._meta.app_label, "library")

    def test_category_choices_uppercase(self):
        self.assertTrue(hasattr(Book, "CATEGORY_CHOICES"))
        self.assertIsInstance(Book.CATEGORY_CHOICES, list)

    def test_language_choices_uppercase(self):
        self.assertTrue(hasattr(Book, "LANGUAGE_CHOICES"))
        self.assertIsInstance(Book.LANGUAGE_CHOICES, list)


class IssuedBookModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="12345")
        self.library = Library.objects.create(name="Test Library", owner=self.user)
        self.student = StudentExtra.objects.create(
            user=self.user,
            library=self.library,
            name="Student Name",
            enrollment="12345",
        )
        self.book = Book.objects.create(
            library=self.library, name="Test Book", quantity=5, author="Author"
        )

    def test_str(self):
        issued = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
            enrollment="12345",
            book_name="Test Book",
        )
        self.assertEqual(str(issued), "12345 - Test Book")

    def test_save_auto_fill(self):
        issued = IssuedBook(student=self.student, book=self.book)
        issued.save()
        self.assertEqual(issued.enrollment, "12345")
        self.assertEqual(issued.book_name, "Test Book")

    def test_meta_app_label(self):
        self.assertEqual(IssuedBook._meta.app_label, "library")


class GetExpiryTest(TestCase):
    def test_get_expiry(self):
        expiry = get_expiry()
        expected = datetime.today() + timedelta(days=15)
        self.assertEqual(expiry.date(), expected.date())
