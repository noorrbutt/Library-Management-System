from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from apps.core.models import Library
from apps.members.models import LibraryMembership


class LibraryMembershipModelTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='12345')
        self.member = User.objects.create_user(username='member', password='12345')
        self.library = Library.objects.create(name='Test Library', owner=self.owner)

    def test_str(self):
        membership = LibraryMembership.objects.create(
            library=self.library,
            user=self.member,
            role='member'
        )
        self.assertEqual(str(membership), f"{self.member.email} - Test Library (member)")

    def test_meta_app_label(self):
        self.assertEqual(LibraryMembership._meta.app_label, 'library')

    def test_unique_together(self):
        LibraryMembership.objects.create(
            library=self.library,
            user=self.member
        )
        with self.assertRaises(IntegrityError):
            LibraryMembership.objects.create(
                library=self.library,
                user=self.member
            )

    def test_role_choices_uppercase(self):
        self.assertTrue(hasattr(LibraryMembership, 'ROLE_CHOICES'))
        self.assertIsInstance(LibraryMembership.ROLE_CHOICES, list)