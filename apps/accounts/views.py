from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from apps.books.models import Book, IssuedBook
from apps.students.models import StudentExtra
from apps.members.models import LibraryMembership
from apps.core.models import Library, AdminProfile
from django.contrib import messages
import json
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.views import View
from django.views.generic import FormView
from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver
import logging
import re
from django.contrib.auth import update_session_auth_hash

logger = logging.getLogger(__name__)


@receiver(social_account_added)
def add_social_user_to_admin_group(request, sociallogin, **kwargs):
    user = sociallogin.user
    admin_group, _ = Group.objects.get_or_create(name="ADMIN")
    admin_group.user_set.add(user)


# -------------------- ROLE CHECK --------------------


def is_admin(user):
    return user.groups.filter(name="ADMIN").exists()


class AdminLoginView(View):
    """
    Credential-first login flow.
    Step 1: authenticate username/password.
    Step 2: if user belongs to one library, auto-login.
    Step 3: if user belongs to multiple libraries, show filtered picker.
    """

    template_name = "library/adminlogin.html"

    def _clear_pending_login_session(self, request):
        request.session.pop("pending_user_id", None)
        request.session.pop("eligible_library_ids", None)

    def _render_login(self, request, extra_context=None):
        from .forms import AdminLoginForm

        context = {"form": AdminLoginForm()}
        if extra_context:
            context.update(extra_context)
        return render(request, self.template_name, context)

    def _get_eligible_libraries(self, user):
        return (
            Library.objects.filter(Q(owner=user) | Q(memberships__user=user))
            .distinct()
            .order_by("-created_at")
        )

    def _ensure_admin_profile_and_membership(self, user, library):
        if library.owner == user:
            if not is_admin(user):
                return False, "You do not have admin privileges."

            admin_profile, _ = AdminProfile.objects.get_or_create(user=user)
            if admin_profile.library is None or admin_profile.library != library:
                admin_profile.library = library
                admin_profile.save()
                logger.debug(
                    "adminlogin: linked admin profile %s to library %s",
                    admin_profile.id,
                    library.id,
                )

            LibraryMembership.objects.get_or_create(
                library=library,
                user=user,
                defaults={
                    "role": "owner",
                    "added_by": user,
                    "must_change_password": False,
                },
            )
            return True, None

        if not LibraryMembership.objects.filter(library=library, user=user).exists():
            return False, "You do not have access to this library."

        try:
            user.admin_profile
        except AdminProfile.DoesNotExist:
            AdminProfile.objects.create(user=user)

        return True, None

    def _login_user_to_library(self, request, user, library):
        success, error_message = self._ensure_admin_profile_and_membership(
            user, library
        )
        if not success:
            self._clear_pending_login_session(request)
            messages.error(request, error_message)
            return self._render_login(request)

        is_owner = library.owner == user
        request.session["current_library_id"] = library.id
        request.session["library_id"] = library.id
        request.session["current_library_name"] = library.name
        request.session["is_library_owner"] = is_owner
        auth_login(request, user)
        self._clear_pending_login_session(request)
        logger.debug("adminlogin: authenticated and logged in user %s", user.username)
        messages.success(request, f"Welcome back! Logged into {library.name}.")
        return redirect("dashboard")

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")

        self._clear_pending_login_session(request)
        return self._render_login(request)

    def post(self, request):
        pending_user_id = request.session.get("pending_user_id")
        selected_library = request.POST.get("selected_library")

        if pending_user_id:
            if not selected_library:
                eligible_library_ids = request.session.get("eligible_library_ids", [])
                eligible_libraries = Library.objects.filter(
                    id__in=eligible_library_ids
                ).order_by("-created_at")
                messages.error(
                    request, "Please select one of your libraries to continue."
                )
                return self._render_login(
                    request,
                    {
                        "eligible_libraries": eligible_libraries,
                        "multi_library_message": "You belong to multiple libraries. Please select one to continue.",
                    },
                )

            try:
                user = User.objects.get(id=pending_user_id)
            except User.DoesNotExist:
                self._clear_pending_login_session(request)
                messages.error(
                    request, "Unable to continue login. Please sign in again."
                )
                return self._render_login(request)

            try:
                library_id = int(selected_library)
            except (TypeError, ValueError):
                self._clear_pending_login_session(request)
                messages.error(request, "Invalid library selection.")
                return self._render_login(request)

            eligible_library_ids = request.session.get("eligible_library_ids", [])
            if library_id not in eligible_library_ids:
                self._clear_pending_login_session(request)
                messages.error(request, "Invalid library selection.")
                return self._render_login(request)

            try:
                library = Library.objects.get(id=library_id)
            except Library.DoesNotExist:
                self._clear_pending_login_session(request)
                messages.error(request, "Selected library not found.")
                return self._render_login(request)

            return self._login_user_to_library(request, user, library)

        username = request.POST.get("username")
        password = request.POST.get("password")
        self._clear_pending_login_session(request)

        if not username or not password:
            messages.error(request, "Please enter your username and password.")
            return self._render_login(request)

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Invalid username or password.")
            return self._render_login(request)

        library_qs = self._get_eligible_libraries(user)
        library_count = library_qs.count()

        if library_count == 0:
            messages.error(
                request,
                "Your account is not associated with any library. Contact your library owner.",
            )
            return self._render_login(request)

        if library_count == 1:
            return self._login_user_to_library(request, user, library_qs.first())

        eligible_libraries = list(library_qs)
        request.session["pending_user_id"] = user.id
        request.session["eligible_library_ids"] = [lib.id for lib in eligible_libraries]

        return self._render_login(
            request,
            {
                "eligible_libraries": eligible_libraries,
                "multi_library_message": "You belong to multiple libraries. Please select one to continue.",
            },
        )


def adminsignup_view(request):
    """Handle admin signup for creating a new library."""
    from apps.core.services import create_library_with_owner

    # --- GOOGLE / already-logged-in path ---
    if request.user.is_authenticated:
        from .forms import CreateLibraryNameForm

        form = CreateLibraryNameForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                user = request.user
                library_name = form.cleaned_data["library_name"]

                # Use service layer
                result = create_library_with_owner(user, library_name)
                library = result["library"]

                # Set session keys
                request.session["library_id"] = library.id
                request.session["current_library_id"] = library.id
                request.session["current_library_name"] = library.name
                request.session["is_library_owner"] = True

                messages.success(
                    request, f"Library '{library.name}' created successfully!"
                )
                return redirect("dashboard")
            except Exception as e:
                logger.exception("adminsignup google-user exception")
                messages.error(request, f"An error occurred: {str(e)}")

        return render(
            request, "library/adminsignup.html", {"form": form, "google_user": True}
        )

    # --- Normal email/password signup path ---
    from .forms import CreateLibraryForm

    form = CreateLibraryForm()
    if request.method == "POST":
        form = CreateLibraryForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                )
                library_name = form.cleaned_data["library_name"]

                # Use service layer
                result = create_library_with_owner(user, library_name)
                library = result["library"]

                # Set session keys
                auth_login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )
                request.session["library_id"] = library.id
                request.session["current_library_id"] = library.id
                request.session["current_library_name"] = library.name
                request.session["is_library_owner"] = True

                messages.success(
                    request, f"Library '{library.name}' created successfully!"
                )
                return redirect("dashboard")
            except Exception as e:
                logger.exception("adminsignup exception")
                messages.error(request, f"An error occurred: {str(e)}")

    return render(request, "library/adminsignup.html", {"form": form})


# -------------------- AFTER LOGIN --------------------


def afterlogin_view(request):
    """
    Redirect after successful social login (Google OAuth, etc).
    If user has a library, go to dashboard.
    If not, go to create library.
    """
    if not request.user.is_authenticated:
        return redirect("adminlogin")

    if not is_admin(request.user):
        # Add non-admin social users to ADMIN group
        admin_group, _ = Group.objects.get_or_create(name="ADMIN")
        admin_group.user_set.add(request.user)

    # Check if user has a library
    from apps.core.views import get_user_library

    library = get_user_library(request.user)

    if library:
        admin_profile, _ = AdminProfile.objects.get_or_create(user=request.user)
        if admin_profile.library is None:
            admin_profile.library = library
            admin_profile.save()

        request.session["current_library_id"] = library.id
        request.session["library_id"] = library.id
        request.session["current_library_name"] = library.name
        request.session["is_library_owner"] = request.user == library.owner
        # User has a library, go to dashboard
        messages.success(request, f"Welcome back to {library.name}!")
        return redirect("dashboard")
    else:
        # User doesn't have a library, go to create one
        messages.info(request, "Let's create your library!")
        return redirect("adminsignup")


@login_required
def force_password_change(request):
    """Force password change for new members."""
    library_id = request.session.get("current_library_id") or request.session.get(
        "library_id"
    )
    membership = LibraryMembership.objects.filter(
        user=request.user, library_id=library_id
    ).first()
    if not membership or not membership.must_change_password:
        return redirect("dashboard")

    if request.method == "POST":
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        if new_password == confirm_password and len(new_password) >= 6:
            request.user.set_password(new_password)
            request.user.save()
            membership.must_change_password = False
            membership.save()
            auth_login(request, request.user)
            messages.success(request, "Password changed successfully.")
            return redirect("dashboard")
        messages.error(request, "Passwords must match and be at least 6 characters.")

    return render(
        request, "library/force_password_change.html", {"membership": membership}
    )
