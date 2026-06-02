from django.shortcuts import render, redirect
from apps.core.views import library_required
from django.http import JsonResponse
from .models import LibraryMembership
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


# -------------------- MEMBER MANAGEMENT VIEWS --------------------
@library_required
def add_member(request):
    """Add a new member to the library."""
    from .services import add_member_to_library

    library = request.library
    if request.user != library.owner:
        messages.error(request, "Only the library owner can manage members.")
        return redirect("dashboard")

    if request.method == "POST" and request.POST.get("add_member"):
        email = request.POST.get("email", "").strip().lower()
        username = request.POST.get("username", "").strip()

        try:
            result = add_member_to_library(request.user, library, email, username)
            user = result["user"]
            is_new = result["is_new"]
            temp_password = result["temp_password"]

            if is_new:
                messages.success(
                    request,
                    f"Member added. Username: {username}  |  Temporary password: {temp_password}"
                    f" — Share these credentials with {email} securely.",
                )
            else:
                messages.success(
                    request,
                    f"'{user.username}' ({email}) has been added to this library. "
                    f"They can log in using their existing credentials.",
                )
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, str(e))

        return redirect("add_member")

    return render(
        request,
        "library/add_member.html",
        {
            "library": library,
            "memberships": LibraryMembership.objects.filter(library=library),
        },
    )


@library_required
def view_members(request):
    """View all members of the library."""
    library = request.library
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

@library_required
def remove_member(request):
    """Remove a member from the library."""
    library = request.library
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
