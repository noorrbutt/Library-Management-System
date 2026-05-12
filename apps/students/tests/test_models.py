from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from apps.core.models import Library
from apps.students.models import StudentExtra


class StudentExtraModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="12345")
        self.library = Library.objects.create(name="Test Library", owner=self.user)

    def test_str(self):
        student = StudentExtra.objects.create(
            user=self.user,
            library=self.library,
            name="Student Name",
            enrollment="12345",
        )
        self.assertEqual(str(student), "Student Name [12345]")

    def test_meta_app_label(self):
        self.assertEqual(StudentExtra._meta.app_label, "library")

    def test_unique_together(self):
        StudentExtra.objects.create(library=self.library, enrollment="12345")
        with self.assertRaises(IntegrityError):
            StudentExtra.objects.create(library=self.library, enrollment="12345")

    def test_gender_choices_uppercase(self):
        self.assertTrue(hasattr(StudentExtra, "GENDER_CHOICES"))
        self.assertIsInstance(StudentExtra.GENDER_CHOICES, list)
