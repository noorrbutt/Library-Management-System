"""
Comprehensive tests for members app: LibraryMembership model, services, views, URLs, and admin.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from django.db import IntegrityError
from apps.core.models import Library, AdminProfile
from apps.members.models import LibraryMembership
from apps.members.services import add_member_to_library


class LibraryMembershipModelTests(TestCase):
    """Tests for LibraryMembership model."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="testpass")
        self.member = User.objects.create_user(username="member", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.owner)

    def test_membership_str_representation(self):
        """Test __str__ includes user, library, role."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        str_repr = str(membership)
        self.assertIn(self.member.email, str_repr)
        self.assertIn("Test Lib", str_repr)
        self.assertIn("member", str_repr)

    def test_membership_role_choices(self):
        """Test role choices exist."""
        self.assertEqual(len(LibraryMembership.ROLE_CHOICES), 2)
        roles = [choice[0] for choice in LibraryMembership.ROLE_CHOICES]
        self.assertIn("owner", roles)
        self.assertIn("member", roles)

    def test_membership_unique_constraint_library_user(self):
        """Test unique_together constraint on library and user."""
        LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )

        with self.assertRaises(IntegrityError):
            LibraryMembership.objects.create(
                library=self.lib,
                user=self.member,
                role="owner",
                added_by=self.owner,
            )

    def test_membership_library_fk(self):
        """Test library is ForeignKey."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        self.assertEqual(membership.library, self.lib)

    def test_membership_user_fk(self):
        """Test user is ForeignKey."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        self.assertEqual(membership.user, self.member)

    def test_membership_added_by_fk(self):
        """Test added_by is ForeignKey to User."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        self.assertEqual(membership.added_by, self.owner)

    def test_membership_must_change_password_default_true(self):
        """Test must_change_password defaults to True."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        self.assertTrue(membership.must_change_password)

    def test_membership_cascade_delete_with_library(self):
        """Test membership deleted when library is deleted."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        membership_id = membership.id
        self.lib.delete()
        self.assertFalse(LibraryMembership.objects.filter(id=membership_id).exists())

    def test_membership_cascade_delete_with_user(self):
        """Test membership deleted when user is deleted."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        membership_id = membership.id
        self.member.delete()
        self.assertFalse(LibraryMembership.objects.filter(id=membership_id).exists())

    def test_membership_meta_app_label(self):
        """Test meta app_label is 'library'."""
        self.assertEqual(LibraryMembership._meta.app_label, "library")

    def test_membership_joined_at_auto_now_add(self):
        """Test joined_at is auto-populated."""
        membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.member,
            role="member",
            added_by=self.owner,
        )
        self.assertIsNotNone(membership.joined_at)


class AddMemberToLibraryServiceTests(TestCase):
    """Tests for add_member_to_library service."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.owner)

    def test_add_member_happy_path_new_user(self):
        """Test adding a new member."""
        result = add_member_to_library(
            self.owner,
            self.lib,
            "newmember@test.com",
            "newmember",
        )

        self.assertTrue(result["is_new"])
        self.assertIsNotNone(result["temp_password"])
        self.assertEqual(result["user"].email, "newmember@test.com")
        self.assertEqual(result["membership"].role, "member")
        self.assertTrue(result["membership"].must_change_password)

    def test_add_member_existing_user(self):
        """Test adding existing user as member."""
        existing_user = User.objects.create_user(
            username="existing",
            email="existing@test.com",
            password="pass",
        )

        result = add_member_to_library(
            self.owner,
            self.lib,
            "existing@test.com",
            "ignored_username",  # Should be ignored
        )

        self.assertFalse(result["is_new"])
        self.assertIsNone(result["temp_password"])
        self.assertEqual(result["user"], existing_user)
        self.assertFalse(result["membership"].must_change_password)

    def test_add_member_invalid_email_raises_error(self):
        """Test invalid email raises ValueError."""
        with self.assertRaises(ValueError) as context:
            add_member_to_library(self.owner, self.lib, "invalid", "username")

        self.assertIn("email", str(context.exception).lower())

    def test_add_member_empty_username_raises_error(self):
        """Test empty username raises ValueError."""
        with self.assertRaises(ValueError) as context:
            add_member_to_library(self.owner, self.lib, "test@test.com", "")

        self.assertIn("username", str(context.exception).lower())

    def test_add_member_invalid_username_chars_raises_error(self):
        """Test invalid username characters raise ValueError."""
        with self.assertRaises(ValueError) as context:
            add_member_to_library(self.owner, self.lib, "test@test.com", "bad-user!")

        self.assertIn("username", str(context.exception).lower())

    def test_add_member_username_already_taken_raises_error(self):
        """Test taken username raises ValueError."""
        User.objects.create_user(username="taken", password="pass")

        with self.assertRaises(ValueError) as context:
            add_member_to_library(self.owner, self.lib, "test@test.com", "taken")

        self.assertIn("taken", str(context.exception).lower())

    def test_add_member_already_member_raises_error(self):
        """Test adding already-member raises Exception."""
        existing_user = User.objects.create_user(
            username="existing",
            email="existing@test.com",
            password="pass",
        )
        LibraryMembership.objects.create(
            library=self.lib,
            user=existing_user,
            role="member",
            added_by=self.owner,
        )

        with self.assertRaises(Exception) as context:
            add_member_to_library(
                self.owner,
                self.lib,
                "existing@test.com",
                "another_username",
            )

        self.assertIn("already a member", str(context.exception).lower())

    def test_add_member_creates_admin_profile(self):
        """Test adding member creates AdminProfile."""
        result = add_member_to_library(
            self.owner,
            self.lib,
            "newmember@test.com",
            "newmember",
        )

        # Should create or get AdminProfile
        profile = AdminProfile.objects.get(user=result["user"])
        self.assertIsNotNone(profile)


class MembersURLsTests(TestCase):
    """Tests for members app URL patterns."""

    def test_add_member_url_resolves(self):
        """Test add_member URL resolves to correct view."""
        resolver = resolve(reverse("add_member"))
        self.assertEqual(resolver.func.__name__, "add_member")

    def test_view_members_url_resolves(self):
        """Test view_members URL resolves to correct view."""
        resolver = resolve(reverse("view_members"))
        self.assertEqual(resolver.func.__name__, "view_members")


class MembersAdminRegistrationTests(TestCase):
    """Tests for members admin registrations."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass"
        )
        self.owner = User.objects.create_user(username="owner", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.owner)
        self.membership = LibraryMembership.objects.create(
            library=self.lib,
            user=self.owner,
            role="owner",
            added_by=self.owner,
        )

    def test_library_membership_registered_in_admin(self):
        """Test LibraryMembership appears in admin site."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get("/admin/library/librarymembership/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("owner", response.content.decode())
