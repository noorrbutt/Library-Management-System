from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.urls import reverse
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


class StudentCSVPDFViewTests(TestCase):
    """Tests for student CSV import/export views."""

    def setUp(self):
        self.user = User.objects.create_user(username="student", password="12345")
        self.library = Library.objects.create(name="Test Library", owner=self.user)
        self.existing_student = StudentExtra.objects.create(
            library=self.library,
            name="Existing Student",
            enrollment="12345",
        )

    def test_export_students_csv_requires_login(self):
        response = self.client.get(reverse("export_students_csv"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("adminlogin", response.url)

    def test_export_students_csv_returns_200(self):
        self.client.login(username="student", password="12345")
        response = self.client.get(reverse("export_students_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_export_students_csv_contains_student_data(self):
        self.client.login(username="student", password="12345")
        response = self.client.get(reverse("export_students_csv"))
        content = response.content.decode("utf-8")
        self.assertIn(self.existing_student.name, content)
        self.assertIn(self.existing_student.enrollment, content)

    def test_students_csv_sample_download(self):
        self.client.login(username="student", password="12345")
        response = self.client.get(reverse("students_csv_sample"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("name,enrollment,address,phone,gender", content)

    def test_import_students_get_shows_upload_form(self):
        self.client.login(username="student", password="12345")
        response = self.client.get(reverse("import_students"))
        self.assertEqual(response.status_code, 200)

    def test_import_students_step2_parses_csv(self):
        self.client.login(username="student", password="12345")
        csv_content = "name,enrollment,phone,address,gender\nNew Student,2024-CS-002,03001234567,Karachi,Male\n"
        csv_file = SimpleUploadedFile(
            "students.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse("import_students"), {"csv_file": csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertIn("csv_headers", response.context)
        self.assertIn("csv_b64", response.context)
        self.assertEqual(response.context["csv_headers"], ["name", "enrollment", "phone", "address", "gender"])
        self.assertTrue(response.context["csv_b64"])

    def test_import_students_step3_creates_students(self):
        self.client.login(username="student", password="12345")
        csv_content = "name,enrollment,phone,address,gender\nNew Student,2024-CS-003,03001234567,Lahore,Male\n"
        csv_file = SimpleUploadedFile(
            "students.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse("import_students"), {"csv_file": csv_file})
        csv_b64 = response.context["csv_b64"]

        response = self.client.post(
            reverse("import_students"),
            {
                "action": "confirm_import",
                "csv_b64": csv_b64,
                "map_name": "0",
                "map_enrollment": "1",
                "map_phone": "2",
                "map_address": "3",
                "map_gender": "4",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            StudentExtra.objects.filter(library=self.library, enrollment="2024-CS-003", name="New Student").exists()
        )

    def test_import_students_step3_skips_duplicate_enrollments(self):
        self.client.login(username="student", password="12345")
        csv_content = (
            "name,enrollment,phone,address,gender\n"
            "Another Student,2024-CS-004,03001234567,Lahore,Male\n"
            "Existing Student,12345,03001234567,Karachi,Male\n"
        )
        csv_file = SimpleUploadedFile(
            "students.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse("import_students"), {"csv_file": csv_file})
        csv_b64 = response.context["csv_b64"]

        response = self.client.post(
            reverse("import_students"),
            {
                "action": "confirm_import",
                "csv_b64": csv_b64,
                "map_name": "0",
                "map_enrollment": "1",
                "map_phone": "2",
                "map_address": "3",
                "map_gender": "4",
            },
            follow=True,
        )
        self.assertEqual(StudentExtra.objects.filter(library=self.library, enrollment="12345").count(), 1)
        self.assertEqual(StudentExtra.objects.filter(library=self.library).count(), 2)
        messages = [m.message for m in response.context["messages"]]
        self.assertTrue(any("skipped" in str(message).lower() for message in messages))
