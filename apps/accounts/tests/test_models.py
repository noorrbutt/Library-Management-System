from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse, resolve



class AccountsViewTests(TestCase):
    def test_adminlogin_get_returns_200(self):
        response = self.client.get(reverse("adminlogin"))
        self.assertEqual(response.status_code, 200)

    def test_adminsignup_get_returns_200(self):
        response = self.client.get(reverse("adminsignup"))
        self.assertEqual(response.status_code, 200)

    def test_afterlogin_redirects_unauthenticated_to_adminlogin(self):
        response = self.client.get(reverse("afterlogin"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("adminlogin"), response.url)

    def test_force_password_change_redirects_when_no_change_required(self):
        user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        library = None
        from apps.core.models import Library
        from apps.members.models import LibraryMembership

        library = Library.objects.create(name="Test Library", owner=user)
        LibraryMembership.objects.create(
            library=library,
            user=user,
            role="member",
            must_change_password=False,
        )

        self.client.force_login(user)
        session = self.client.session
        session["current_library_id"] = library.id
        session.save()

        response = self.client.get(reverse("force_password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)

    def test_adminlogin_url_resolves_to_adminloginview(self):
        resolver = resolve(reverse("adminlogin"))
        self.assertEqual(resolver.func.view_class.__name__, "AdminLoginView")

    def test_adminsignup_url_resolves_to_adminsignup_view(self):
        resolver = resolve(reverse("adminsignup"))
        self.assertEqual(resolver.func.__name__, "adminsignup_view")

    def test_afterlogin_url_resolves_to_afterlogin_view(self):
        resolver = resolve(reverse("afterlogin"))
        self.assertEqual(resolver.func.__name__, "afterlogin_view")
