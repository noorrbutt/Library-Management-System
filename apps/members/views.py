from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from .models import LibraryMembership
from apps.core.models import Library, AdminProfile
from django.contrib import messages
import json
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
import logging
import re
from django.contrib.auth import update_session_auth_hash

logger = logging.getLogger(__name__)


# -------------------- MEMBER MANAGEMENT VIEWS --------------------


@login_required
def add_member(request):
    library_id = request.session.get("current_library_id") or request.session.get(
        "library_id"
    )
    library = get_object_or_404(Library, id=library_id)
    if request.user != library.owner:
        messages.error(request, "Only the library owner can manage members.")
        return redirect("dashboard")

    if request.method == "POST" and request.POST.get("add_member"):
        email = request.POST.get("email", "").strip().lower()
        username = request.POST.get("username", "").strip()

        # ── Validate inputs ──────────────────────────────────────────
        if not email or "@" not in email:
            messages.error(request, "Please enter a valid email address.")
            return redirect("add_member")

        if not username:
            messages.error(request, "Please enter a username for the new member.")
            return redirect("add_member")

        # Username validation: alphanumeric + underscores only

        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            messages.error(
                request, "Username may only contain letters, numbers and underscores."
            )
            return redirect("add_member")

        # ── Check if username already taken ─────────────────────────
        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                f"The username '{username}' is already taken. Please choose a different one.",
            )
            return redirect("add_member")

        # ── Try to find existing user by email ──────────────────────
        existing_user = User.objects.filter(email=email).first()

        if existing_user:
            # User exists — check if already a member of THIS library
            if LibraryMembership.objects.filter(
                library=library, user=existing_user
            ).exists():
                messages.error(
                    request,
                    f"'{existing_user.username}' ({email}) is already a member of this library.",
                )
                return redirect("add_member")

            # Add them as a member (they keep their existing credentials)
            AdminProfile.objects.get_or_create(user=existing_user)
            LibraryMembership.objects.create(
                library=library,
                user=existing_user,
                added_by=request.user,
                role="member",
                must_change_password=False,  # They already know their password
            )
            messages.success(
                request,
                f"'{existing_user.username}' ({email}) has been added to this library. "
                f"They can log in using their existing credentials.",
            )

        else:
            # ── Create brand-new user with the exact username entered ──
            temp_password = User.objects.make_random_password(length=10)

            new_user = User.objects.create(
                email=email,
                username=username,  # Exactly what the owner typed — no auto-generation
                password=make_password(temp_password),
            )

            AdminProfile.objects.get_or_create(user=new_user)
            LibraryMembership.objects.create(
                library=library,
                user=new_user,
                added_by=request.user,
                role="member",
                must_change_password=True,
            )

            messages.success(
                request,
                f"Member added. Username: {username}  |  Temporary password: {temp_password}"
                f" — Share these credentials with {email} securely.",
            )

        return redirect("view_members")

    return render(
        request,
        "library/add_member.html",
        {
            "library": library,
            "memberships": LibraryMembership.objects.filter(library=library),
        },
    )


@login_required
def view_members(request):
    library_id = request.session.get("current_library_id") or request.session.get(
        "library_id"
    )
    library = get_object_or_404(Library, id=library_id)
    if request.user != library.owner:
        messages.error(request, "Only the library owner can manage members.")
        return redirect("dashboard")

    memberships = (
        LibraryMembership.objects.filter(library=library)
        .select_related("user", "added_by")
        .order_by("-joined_at")
    )

    return render(
        request,
        "library/view_members.html",
        {
            "memberships": memberships,
            "library": library,
        },
    )


@login_required
def force_password_change(request):
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


@login_required
def remove_member(request):
    library_id = request.session.get("current_library_id") or request.session.get(
        "library_id"
    )
    library = get_object_or_404(Library, id=library_id)
    if request.user != library.owner:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    membership_id = request.POST.get("membership_id")
    membership = get_object_or_404(LibraryMembership, id=membership_id, library=library)
    if membership.user == library.owner:
        messages.error(request, "Cannot remove the library owner.")
        return redirect("view_members")

    membership.delete()
    messages.success(request, f"Removed {membership.user.email} from library.")
    return redirect("view_members")
