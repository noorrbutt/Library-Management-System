"""
Comprehensive tests for core app: Library and AdminProfile models, services, views, and admin.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse, resolve
from apps.core.models import Library, AdminProfile
from apps.members.models import LibraryMembership
from apps.core.services import create_library_with_owner


class LibraryModelTests(TestCase):
    """Tests for Library model."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass")

    def test_library_str_representation(self):
        """Test __str__ returns name and code."""
        lib = Library.objects.create(name="Test Library", owner=self.user)
        self.assertIn("Test Library", str(lib))
        self.assertIn(lib.code, str(lib))
        self.assertEqual(str(lib), f"Test Library [{lib.code}]")

    def test_library_code_auto_generation(self):
        """Test code is auto-generated on save."""
        lib = Library(name="Auto Code Lib", owner=self.user)
        self.assertFalse(lib.code)
        lib.save()
        self.assertTrue(lib.code)
        self.assertTrue(lib.code.startswith("LIB-"))
        self.assertEqual(len(lib.code), 10)  # LIB- (4) + 6 hex chars

    def test_library_code_unique_constraint(self):
        """Test code is unique."""
        lib1 = Library.objects.create(name="Lib1", owner=self.user)
        code1 = lib1.code
        lib2 = Library.objects.create(name="Lib2", owner=self.user)
        code2 = lib2.code
        self.assertNotEqual(code1, code2)

    def test_library_code_not_regenerated_on_update(self):
        """Test code is not regenerated when updating library."""
        lib = Library.objects.create(name="Original", owner=self.user)
        original_code = lib.code
        lib.name = "Updated"
        lib.save()
        lib.refresh_from_db()
        self.assertEqual(lib.code, original_code)

    def test_library_owner_fk(self):
        """Test owner is ForeignKey to User."""
        lib = Library.objects.create(name="Test", owner=self.user)
        self.assertEqual(lib.owner, self.user)

    def test_library_cascade_delete_with_owner(self):
        """Test library is deleted when owner is deleted."""
        lib = Library.objects.create(name="Test", owner=self.user)
        lib_id = lib.id
        self.user.delete()
        self.assertFalse(Library.objects.filter(id=lib_id).exists())

    def test_library_meta_app_label(self):
        """Test meta app_label is 'library'."""
        self.assertEqual(Library._meta.app_label, "library")

    def test_library_created_at_auto_now_add(self):
        """Test created_at is auto-populated."""
        lib = Library.objects.create(name="Test", owner=self.user)
        self.assertIsNotNone(lib.created_at)


class AdminProfileModelTests(TestCase):
    """Tests for AdminProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.user)

    def test_admin_profile_str_representation(self):
        """Test __str__ includes username."""
        profile = AdminProfile.objects.create(user=self.user, library=self.lib)
        self.assertIn("admin", str(profile))
        self.assertIn("Profile", str(profile))
        self.assertEqual(str(profile), "Profile: admin")

    def test_admin_profile_one_to_one_user(self):
        """Test AdminProfile is OneToOne with User."""
        profile = AdminProfile.objects.create(user=self.user, library=self.lib)
        self.assertEqual(profile.user, self.user)
        # Verify OneToOne by checking we can access via related_name
        self.assertEqual(self.user.admin_profile, profile)

    def test_admin_profile_library_fk(self):
        """Test library is ForeignKey."""
        profile = AdminProfile.objects.create(user=self.user, library=self.lib)
        self.assertEqual(profile.library, self.lib)

    def test_admin_profile_library_null_allowed(self):
        """Test library can be null."""
        profile = AdminProfile.objects.create(user=self.user, library=None)
        self.assertIsNone(profile.library)

    def test_admin_profile_cascade_with_user(self):
        """Test profile is deleted when user is deleted."""
        profile = AdminProfile.objects.create(user=self.user, library=self.lib)
        profile_id = profile.id
        self.user.delete()
        self.assertFalse(AdminProfile.objects.filter(id=profile_id).exists())

    def test_admin_profile_optional_fields(self):
        """Test optional fields can be blank."""
        profile = AdminProfile.objects.create(user=self.user, library=self.lib)
        self.assertEqual(profile.phone, "")
        self.assertEqual(profile.address, "")
        self.assertIsNone(profile.date_of_birth)
        self.assertFalse(profile.photo)

    def test_admin_profile_meta_app_label(self):
        """Test meta app_label is 'library'."""
        self.assertEqual(AdminProfile._meta.app_label, "library")


class CreateLibraryWithOwnerServiceTests(TestCase):
    """Tests for create_library_with_owner service."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass")

    def test_create_library_happy_path(self):
        """Test creating a library with owner."""
        result = create_library_with_owner(self.user, "My Library")

        self.assertIn("library", result)
        self.assertIn("admin_profile", result)
        self.assertIn("membership", result)

        library = result["library"]
        self.assertEqual(library.name, "My Library")
        self.assertEqual(library.owner, self.user)
        self.assertTrue(library.code)

    def test_create_library_creates_admin_profile(self):
        """Test AdminProfile is created/updated."""
        result = create_library_with_owner(self.user, "Lib1")
        profile = result["admin_profile"]
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.library, result["library"])

    def test_create_library_adds_to_admin_group(self):
        """Test user is added to ADMIN group."""
        result = create_library_with_owner(self.user, "Lib1")
        admin_group = Group.objects.get(name="ADMIN")
        self.assertTrue(self.user.groups.filter(name="ADMIN").exists())

    def test_create_library_creates_membership(self):
        """Test LibraryMembership with owner role is created."""
        result = create_library_with_owner(self.user, "Lib1")
        membership = result["membership"]
        self.assertEqual(membership.library, result["library"])
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.role, "owner")
        self.assertEqual(membership.added_by, self.user)
        self.assertFalse(membership.must_change_password)

    def test_create_library_idempotent_admin_profile(self):
        """Test creating twice doesn't create duplicate AdminProfile."""
        result1 = create_library_with_owner(self.user, "Lib1")
        lib1_id = result1["library"].id

        result2 = create_library_with_owner(self.user, "Lib2")
        lib2_id = result2["library"].id

        # Should have 2 libraries
        self.assertEqual(Library.objects.filter(owner=self.user).count(), 2)
        # But only 1 AdminProfile (latest library)
        self.assertEqual(AdminProfile.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.user.admin_profile.library.id, lib2_id)


class CoreViewsAuthTests(TestCase):
    """Tests for core views authentication."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.user)
        AdminProfile.objects.create(user=self.user, library=self.lib)
        LibraryMembership.objects.create(
            library=self.lib, user=self.user, role="owner", added_by=self.user
        )

    def test_library_required_decorator_unauthenticated(self):
        """Test @library_required redirects unauthenticated to login."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("adminlogin", response.url)

    def test_library_required_decorator_authenticated_with_library(self):
        """Test @library_required allows authenticated user with library."""
        self.client.login(username="admin", password="testpass")
        self.client.session["current_library_id"] = self.lib.id
        self.client.session.save()

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_library_required_decorator_no_library(self):
        """Test @library_required redirects when user has no library."""
        user2 = User.objects.create_user(username="user2", password="testpass")
        self.client.login(username="user2", password="testpass")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("adminsignup", response.url)

    def test_dashboard_view_returns_200(self):
        """Test dashboard returns 200 for authorized user."""
        self.client.login(username="admin", password="testpass")
        self.client.session["current_library_id"] = self.lib.id
        self.client.session.save()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_userprofile_view_requires_login(self):
        """Test userprofile requires login."""
        response = self.client.get(reverse("userprofile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())


class CoreURLsTests(TestCase):
    """Tests for core app URL patterns."""

    def test_dashboard_url_resolves(self):
        """Test dashboard URL resolves to correct view."""
        resolver = resolve(reverse("dashboard"))
        self.assertEqual(resolver.func.__name__, "dashboard_view")

    def test_userprofile_url_resolves(self):
        """Test userprofile URL resolves to correct view."""
        resolver = resolve(reverse("userprofile"))
        self.assertEqual(resolver.func.__name__, "userprofile_view")

    def test_adminclick_url_resolves(self):
        """Test adminclick URL resolves to correct view."""
        resolver = resolve(reverse("adminclick"))
        self.assertEqual(resolver.func.__name__, "adminclick_view")


class CoreAdminRegistrationTests(TestCase):
    """Tests for core admin registrations."""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass"
        )
        self.user = User.objects.create_user(username="owner", password="testpass")
        self.lib = Library.objects.create(name="Test Lib", owner=self.user)

    def test_library_registered_in_admin(self):
        """Test Library appears in admin site."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get("/admin/library/library/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Lib", response.content.decode())

    def test_admin_profile_registered_in_admin(self):
        """Test AdminProfile appears in admin site."""
        profile = AdminProfile.objects.create(user=self.user, library=self.lib)
        self.client.login(username="admin", password="adminpass")
        response = self.client.get("/admin/library/adminprofile/")
        self.assertEqual(response.status_code, 200)

    def test_library_list_display_contains_name(self):
        """Test Library admin list shows name."""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get("/admin/library/library/")
        content = response.content.decode()
        self.assertIn("Test Lib", content)
