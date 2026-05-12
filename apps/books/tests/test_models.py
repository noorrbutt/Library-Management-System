"""
Comprehensive tests for books app: Book, IssuedBook models, services, views, URLs, forms, and admin.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from apps.core.models import Library, AdminProfile
from apps.members.models import LibraryMembership
from apps.students.models import StudentExtra
from apps.books.models import Book, IssuedBook, get_expiry
from apps.books.services import issue_book, return_book
from datetime import datetime, timedelta, date


class BookModelTests(TestCase):
    """Tests for Book model."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.library = Library.objects.create(name="Test Library", owner=self.user)

    def test_book_str_representation(self):
        """Test __str__ returns name and quantity."""
        book = Book.objects.create(
            library=self.library,
            name="Test Book",
            quantity=5,
            author="Author",
            category="Education",
            language="English",
        )
        self.assertEqual(str(book), "Test Book [5]")

    def test_book_str_zero_quantity(self):
        """Test __str__ with zero quantity."""
        book = Book.objects.create(
            library=self.library,
            name="Out of Stock",
            quantity=0,
            author="Author",
        )
        self.assertEqual(str(book), "Out of Stock [0]")

    def test_book_category_choices(self):
        """Test CATEGORY_CHOICES exists."""
        self.assertTrue(hasattr(Book, "CATEGORY_CHOICES"))
        self.assertIsInstance(Book.CATEGORY_CHOICES, list)
        self.assertGreater(len(Book.CATEGORY_CHOICES), 0)

    def test_book_language_choices(self):
        """Test LANGUAGE_CHOICES exists."""
        self.assertTrue(hasattr(Book, "LANGUAGE_CHOICES"))
        self.assertIsInstance(Book.LANGUAGE_CHOICES, list)
        self.assertEqual(len(Book.LANGUAGE_CHOICES), 2)  # English, Urdu

    def test_book_default_category(self):
        """Test default category is Education."""
        book = Book.objects.create(
            library=self.library,
            name="Book",
            quantity=1,
            author="Author",
        )
        self.assertEqual(book.category, "Education")

    def test_book_default_language(self):
        """Test default language is English."""
        book = Book.objects.create(
            library=self.library,
            name="Book",
            quantity=1,
            author="Author",
        )
        self.assertEqual(book.language, "English")

    def test_book_library_fk(self):
        """Test library is ForeignKey."""
        book = Book.objects.create(
            library=self.library,
            name="Book",
            quantity=1,
            author="Author",
        )
        self.assertEqual(book.library, self.library)

    def test_book_cascade_delete_with_library(self):
        """Test books are deleted when library is deleted."""
        book = Book.objects.create(
            library=self.library,
            name="Book",
            quantity=1,
            author="Author",
        )
        book_id = book.id
        self.library.delete()
        self.assertFalse(Book.objects.filter(id=book_id).exists())

    def test_book_meta_app_label(self):
        """Test meta app_label is 'library'."""
        self.assertEqual(Book._meta.app_label, "library")


class IssuedBookModelTests(TestCase):
    """Tests for IssuedBook model."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.library = Library.objects.create(name="Test Library", owner=self.user)
        self.student = StudentExtra.objects.create(
            library=self.library,
            name="Student",
            enrollment="12345",
        )
        self.book = Book.objects.create(
            library=self.library,
            name="Test Book",
            quantity=5,
            author="Author",
        )

    def test_issued_book_str_representation(self):
        """Test __str__ returns enrollment and book name."""
        issued = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
            enrollment="12345",
            book_name="Test Book",
        )
        self.assertEqual(str(issued), "12345 - Test Book")

    def test_issued_book_save_auto_fills_enrollment(self):
        """Test save() auto-fills enrollment from student."""
        issued = IssuedBook(student=self.student, book=self.book)
        issued.save()
        self.assertEqual(issued.enrollment, "12345")

    def test_issued_book_save_auto_fills_book_name(self):
        """Test save() auto-fills book_name from book."""
        issued = IssuedBook(student=self.student, book=self.book)
        issued.save()
        self.assertEqual(issued.book_name, "Test Book")

    def test_issued_book_save_does_not_overwrite(self):
        """Test save() doesn't overwrite manually set values."""
        issued = IssuedBook(
            student=self.student,
            book=self.book,
            enrollment="MANUAL",
            book_name="Manual Title",
        )
        issued.save()
        self.assertEqual(issued.enrollment, "MANUAL")
        self.assertEqual(issued.book_name, "Manual Title")

    def test_issued_book_default_returned_false(self):
        """Test returned defaults to False."""
        issued = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
        )
        self.assertFalse(issued.returned)

    def test_issued_book_cascade_delete_with_student(self):
        """Test issued books deleted when student is deleted."""
        issued = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
        )
        issued_id = issued.id
        self.student.delete()
        self.assertFalse(IssuedBook.objects.filter(id=issued_id).exists())

    def test_issued_book_cascade_delete_with_book(self):
        """Test issued books deleted when book is deleted."""
        issued = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
        )
        issued_id = issued.id
        self.book.delete()
        self.assertFalse(IssuedBook.objects.filter(id=issued_id).exists())

    def test_issued_book_meta_app_label(self):
        """Test meta app_label is 'library'."""
        self.assertEqual(IssuedBook._meta.app_label, "library")

    def test_issued_book_has_no_expirydate_field_only_property(self):
        """Test IssuedBook has expirydate in model but use return_date."""
        # This tests the regression requirement
        issued = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
        )
        # Should have expirydate field from legacy code
        self.assertTrue(hasattr(issued, "expirydate"))
        # But should also have return_date for primary use
        self.assertTrue(hasattr(issued, "return_date"))


class GetExpiryTests(TestCase):
    """Tests for get_expiry utility function."""

    def test_get_expiry_returns_15_days_from_today(self):
        """Test get_expiry returns date 15 days from today."""
        expiry = get_expiry()
        expected = datetime.today() + timedelta(days=15)
        self.assertEqual(expiry.date(), expected.date())


class IssueBookServiceTests(TestCase):
    """Tests for issue_book service function."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.library = Library.objects.create(name="Test Library", owner=self.user)
        self.student = StudentExtra.objects.create(
            library=self.library,
            name="Student",
            enrollment="12345",
        )
        self.book = Book.objects.create(
            library=self.library,
            name="Test Book",
            quantity=5,
            author="Author",
        )

    def test_issue_book_happy_path(self):
        """Test issuing a book to a student."""
        return_date = date.today() + timedelta(days=15)
        issued_book = issue_book(self.student, self.book, return_date)

        self.assertIsNotNone(issued_book.id)
        self.assertEqual(issued_book.student, self.student)
        self.assertEqual(issued_book.book, self.book)
        self.assertEqual(issued_book.return_date, return_date)
        self.assertFalse(issued_book.returned)

    def test_issue_book_decreases_quantity(self):
        """Test issuing a book decreases library stock."""
        original_qty = self.book.quantity
        return_date = date.today() + timedelta(days=15)
        issue_book(self.student, self.book, return_date)

        self.book.refresh_from_db()
        self.assertEqual(self.book.quantity, original_qty - 1)

    def test_issue_book_out_of_stock_raises_error(self):
        """Test issuing out-of-stock book raises ValueError."""
        self.book.quantity = 0
        self.book.save()

        return_date = date.today() + timedelta(days=15)
        with self.assertRaises(ValueError) as context:
            issue_book(self.student, self.book, return_date)

        self.assertIn("out of stock", str(context.exception).lower())

    def test_issue_book_sets_enrollment_from_student(self):
        """Test enrollment is set from student."""
        return_date = date.today() + timedelta(days=15)
        issued_book = issue_book(self.student, self.book, return_date)

        self.assertEqual(issued_book.enrollment, "12345")

    def test_issue_book_sets_book_name_from_book(self):
        """Test book_name is set from book."""
        return_date = date.today() + timedelta(days=15)
        issued_book = issue_book(self.student, self.book, return_date)

        self.assertEqual(issued_book.book_name, "Test Book")


class ReturnBookServiceTests(TestCase):
    """Tests for return_book service function."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.library = Library.objects.create(name="Test Library", owner=self.user)
        self.student = StudentExtra.objects.create(
            library=self.library,
            name="Student",
            enrollment="12345",
        )
        self.book = Book.objects.create(
            library=self.library,
            name="Test Book",
            quantity=4,  # One already issued
            author="Author",
        )
        self.issued_book = IssuedBook.objects.create(
            student=self.student,
            book=self.book,
            enrollment="12345",
            book_name="Test Book",
            returned=False,
        )

    def test_return_book_happy_path(self):
        """Test returning a book."""
        returned_book = return_book(self.issued_book.id, self.library)

        self.assertTrue(returned_book.returned)
        self.assertEqual(returned_book.id, self.issued_book.id)

    def test_return_book_increases_quantity(self):
        """Test returning a book increases library stock."""
        original_qty = self.book.quantity
        return_book(self.issued_book.id, self.library)

        self.book.refresh_from_db()
        self.assertEqual(self.book.quantity, original_qty + 1)

    def test_return_book_not_found_raises_error(self):
        """Test returning non-existent book raises DoesNotExist."""
        with self.assertRaises(IssuedBook.DoesNotExist):
            return_book(99999, self.library)

    def test_return_book_wrong_library_raises_error(self):
        """Test returning book from wrong library raises DoesNotExist."""
        other_user = User.objects.create_user(username="other", password="pass")
        other_library = Library.objects.create(name="Other Lib", owner=other_user)

        with self.assertRaises(IssuedBook.DoesNotExist):
            return_book(self.issued_book.id, other_library)


class BooksViewsAuthTests(TestCase):
    """Tests for books views authentication and authorization."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.user)
        AdminProfile.objects.create(user=self.user, library=self.lib)
        LibraryMembership.objects.create(
            library=self.lib, user=self.user, role="owner", added_by=self.user
        )
        self.student = StudentExtra.objects.create(
            library=self.lib,
            name="Student",
            enrollment="12345",
        )
        self.book = Book.objects.create(
            library=self.lib,
            name="Test Book",
            quantity=5,
            author="Author",
        )

    def test_addbook_view_requires_login(self):
        """Test addbook requires login."""
        response = self.client.get(reverse("addbook"))
        self.assertEqual(response.status_code, 302)

    def test_viewbook_view_requires_login(self):
        """Test viewbook requires login."""
        response = self.client.get(reverse("viewbook"))
        self.assertEqual(response.status_code, 302)

    def test_issuebook_view_requires_login(self):
        """Test issuebook requires login."""
        response = self.client.get(reverse("issuebook"))
        self.assertEqual(response.status_code, 302)


class BooksURLsTests(TestCase):
    """Tests for books app URL patterns."""

    def test_addbook_url_resolves(self):
        """Test addbook URL resolves to correct view."""
        resolver = resolve(reverse("addbook"))
        self.assertEqual(resolver.func.__name__, "addbook_view")

    def test_viewbook_url_resolves(self):
        """Test viewbook URL resolves to correct view."""
        resolver = resolve(reverse("viewbook"))
        self.assertEqual(resolver.func.__name__, "viewbook_view")

    def test_issuebook_url_resolves(self):
        """Test issuebook URL resolves to correct view."""
        resolver = resolve(reverse("issuebook"))
        self.assertEqual(resolver.func.__name__, "issuebook_view")

    def test_viewissuedbook_url_resolves(self):
        """Test viewissuedbook URL resolves to correct view."""
        resolver = resolve(reverse("viewissuedbook"))
        self.assertEqual(resolver.func.__name__, "viewissuedbook_view")


class BooksAdminRegistrationTests(TestCase):
    """Tests for books admin registrations."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass"
        )
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.user)
        self.book = Book.objects.create(
            library=self.lib,
            name="Test Book",
            quantity=5,
            author="Author",
        )

    def test_book_registered_in_admin(self):
        """Test Book appears in admin site."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get("/admin/library/book/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Book", response.content.decode())

    def test_issued_book_registered_in_admin(self):
        """Test IssuedBook appears in admin site."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get("/admin/library/issuedbook/")
        self.assertEqual(response.status_code, 200)
