from django.test import TestCase
from django.contrib.auth.models import User
from apps.core.models import Library, AdminProfile


class LibraryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')

    def test_str(self):
        library = Library.objects.create(name='Test Library', owner=self.user)
        self.assertEqual(str(library), f"Test Library [{library.code}]")

    def test_save_generates_code(self):
        library = Library(name='Test Library', owner=self.user)
        library.save()
        self.assertTrue(library.code.startswith('LIB-'))
        self.assertEqual(len(library.code), 10)  # LIB- + 6 chars

    def test_meta_app_label(self):
        self.assertEqual(Library._meta.app_label, 'library')


class AdminProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='12345')
        self.library = Library.objects.create(name='Test Lib', owner=self.user)

    def test_str(self):
        profile = AdminProfile.objects.create(user=self.user, library=self.library)
        self.assertEqual(str(profile), "Profile: admin")

    def test_meta_app_label(self):
        self.assertEqual(AdminProfile._meta.app_label, 'library')