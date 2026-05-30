from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from apps.books.models import Book, IssuedBook
from apps.students.models import StudentExtra
from apps.members.models import LibraryMembership
from apps.core.models import Library, AdminProfile
import json
from django.db.models import Count
import logging
from django.contrib.auth import update_session_auth_hash
import functools

logger = logging.getLogger(__name__)


# -------------------- LIBRARY CONTEXT HELPERS --------------------


def get_user_library(user):
    """
    Get the library owned by the user (admin).
    Returns None if user is not an admin or has no library.
    """
    if not user.is_authenticated:
        return None
    try:
        return Library.objects.get(owner=user)
    except Library.DoesNotExist:
        return None
    except Library.MultipleObjectsReturned:
        # Should never happen, but return the first one
        return Library.objects.filter(owner=user).first()


def library_required(view_func):
    """
    Decorator to ensure the logged-in user has a library.
    Redirects to library creation page if not.
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("adminlogin")

        library = None
        library_id = request.session.get("current_library_id") or request.session.get(
            "library_id"
        )
        if library_id:
            try:
                library = Library.objects.get(id=library_id)
                if request.user != library.owner:
                    membership_exists = LibraryMembership.objects.filter(
                        library=library, user=request.user
                    ).exists()
                    if not membership_exists:
                        logger.warning(
                            "library_required: user %s has no membership for library %s",
                            request.user.username,
                            library_id,
                        )
                        library = None
            except Library.DoesNotExist:
                logger.warning(
                    "library_required: session library_id %s invalid for user %s",
                    library_id,
                    request.user.username,
                )
                library = None

        if not library:
            library = get_user_library(request.user)

        if not library:
            # Admin exists but has no library - redirect to create library
            return redirect("adminsignup")
        # Attach library to request for convenience
        request.library = library
        return view_func(request, *args, **kwargs)

    return wrapper


# -------------------- BASIC VIEWS --------------------


def home_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "library/index.html")


@library_required
def dashboard_view(request):
    """
    Comprehensive dashboard displaying library statistics and metrics.
    Scoped to the current user's library only.
    """
    library = request.library
    today = date.today()
    month_start = today.replace(day=1)

    # ========== BASIC STATISTICS (LIBRARY-SCOPED) ==========
    total_books = Book.objects.filter(library=library).count()
    total_members = StudentExtra.objects.filter(library=library).count()

    # Issued books (currently not returned) in this library
    issued_books_count = IssuedBook.objects.filter(
        returned=False, book__library=library
    ).count()

    # Available books in this library
    available_books_count = Book.objects.filter(library=library, quantity__gt=0).count()

    # Overdue books in this library (past return date and not returned)
    overdue_books_count = IssuedBook.objects.filter(
        return_date__lt=today, returned=False, book__library=library
    ).count()

    # Books issued this month in this library
    books_this_month = IssuedBook.objects.filter(
        issuedate__gte=month_start,
        book__library=library,
    ).count()

    # ========== RECENT ACTIVITIES (LIBRARY-SCOPED) ==========
    recent_activities = (
        IssuedBook.objects.filter(book__library=library)
        .select_related("student", "book")
        .order_by("-issuedate")[:15]
    )

    # ========== TOP 5 MOST ISSUED BOOKS (LIBRARY-SCOPED) ==========
    top_books = (
        Book.objects.filter(library=library)
        .annotate(issue_count=Count("issuedbook"))
        .filter(issue_count__gt=0)
        .order_by("-issue_count")[:5]
    )

    # ========== MONTHLY TRENDS (Last 6 Months, LIBRARY-SCOPED) ==========
    months_data = []
    issued_trend = []
    returned_trend = []

    for i in range(5, -1, -1):  # Last 6 months
        month_date = today - timedelta(days=30 * i)
        month_start_calc = month_date.replace(day=1)

        # Calculate month end
        if month_start_calc.month == 12:
            month_end_calc = month_start_calc.replace(day=31)
        else:
            next_month = month_start_calc.replace(
                month=month_start_calc.month + 1, day=1
            )
            month_end_calc = next_month - timedelta(days=1)

        # Count issued books in this month for this library
        issued_count = IssuedBook.objects.filter(
            issuedate__gte=month_start_calc,
            issuedate__lte=month_end_calc,
            book__library=library,
        ).count()

        # Count returned books in this month for this library
        returned_count = IssuedBook.objects.filter(
            return_date__gte=month_start_calc,
            return_date__lte=month_end_calc,
            returned=True,
            book__library=library,
        ).count()

        months_data.append(month_start_calc.strftime("%b"))
        issued_trend.append(issued_count)
        returned_trend.append(returned_count)

    # ========== LOW STOCK BOOKS (LIBRARY-SCOPED) ==========
    low_stock_books = Book.objects.filter(library=library, quantity__lt=3).order_by(
        "quantity"
    )[:10]

    # ========== CATEGORY DISTRIBUTION (LIBRARY-SCOPED) ==========
    category_queryset = (
        Book.objects.filter(library=library)
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:7]
    )

    # Convert to list of dicts for JSON serialization
    category_distribution = []
    for item in category_queryset:
        category_distribution.append(
            {
                "category": item["category"] if item["category"] else "Uncategorized",
                "count": item["count"],
            }
        )

    # ========== CONTEXT DATA ==========
    context = {
        # Basic stats
        "library": library,
        "total_books": total_books,
        "available_books": available_books_count,
        "issued_books": issued_books_count,
        "total_members": total_members,
        "overdue_books": overdue_books_count,
        "books_this_month": books_this_month,
        # Activities and lists
        "recent_activities": recent_activities,
        "top_books": top_books,
        "low_stock_books": low_stock_books,
        # Chart data - JSON serialized
        "months_data": json.dumps(months_data),
        "issued_trend": json.dumps(issued_trend),
        "returned_trend": json.dumps(returned_trend),
        # Status breakdown for pie chart
        "available": available_books_count,
        "issued": issued_books_count,
        "overdue": overdue_books_count,
        # Category data - properly serialized
        "category_distribution": json.dumps(category_distribution),
    }

    return render(request, "library/dashboard.html", context)


def adminclick_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "library/adminclick.html")


# -------------------- USER PROFILE VIEWS --------------------


@library_required
def userprofile_view(request):
    """Show admin's profile and library information."""
    library = request.library
    user = request.user
    admin_profile, _ = AdminProfile.objects.get_or_create(user=user)

    context = {
        "current_user": user,
        "admin_profile": admin_profile,
        "library": library,
    }
    return render(request, "library/userprofile.html", context)


@library_required
def update_profile_view(request):
    """Update admin's profile information."""
    library = request.library
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request method."}, status=405)

    user = request.user

    try:
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        if not first_name or not last_name:
            return JsonResponse(
                {"message": "First name and last name are required."}, status=400
            )

        if not email or "@" not in email:
            return JsonResponse({"message": "Invalid email address."}, status=400)

        if User.objects.filter(email=email).exclude(id=user.id).exists():
            return JsonResponse(
                {"message": "Email address is already in use."}, status=400
            )

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        date_of_birth = request.POST.get("date_of_birth", "").strip()

        admin_profile, _ = AdminProfile.objects.get_or_create(user=user)

        if phone:
            admin_profile.phone = phone
        if address:
            admin_profile.address = address
        if date_of_birth:
            admin_profile.date_of_birth = datetime.strptime(
                date_of_birth, "%Y-%m-%d"
            ).date()

        admin_profile.save()

        return JsonResponse({"message": "Profile updated successfully."})

    except (ValueError, TypeError) as e:
        logger.exception("update_profile_view invalid request data")
        return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=400)
    except Exception as e:
        logger.exception("update_profile_view unexpected error")
        raise


@library_required
def update_library_view(request):
    """Update library information (name, etc)."""
    library = request.library
    if request.user != library.owner:
        return JsonResponse(
            {"message": "Only the library owner can update library details."},
            status=403,
        )
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request method."}, status=405)

    try:
        library_name = request.POST.get("library_name", "").strip()

        if not library_name:
            return JsonResponse({"message": "Library name is required."}, status=400)

        library.name = library_name
        library.save()

        return JsonResponse(
            {
                "message": "Library updated successfully.",
                "library_name": library.name,
            }
        )

    except (ValueError, TypeError) as e:
        logger.exception("update_library_view invalid request data")
        return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=400)
    except Exception as e:
        logger.exception("update_library_view unexpected error")
        raise


@library_required
def change_password_view(request):
    """
    Handle AJAX request to change user password.
    """
    library = request.library
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request method."}, status=405)

    user = request.user

    try:
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()

        # Validation
        if not current_password or not new_password:
            return JsonResponse(
                {"message": "All password fields are required."}, status=400
            )

        # Check current password
        if not user.check_password(current_password):
            return JsonResponse(
                {"message": "Current password is incorrect."}, status=400
            )

        # Validate new password
        if len(new_password) < 8:
            return JsonResponse(
                {"message": "Password must be at least 8 characters long."}, status=400
            )

        if current_password == new_password:
            return JsonResponse(
                {"message": "New password must be different from current password."},
                status=400,
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Update session to prevent automatic logout

        update_session_auth_hash(request, user)

        return JsonResponse({"message": "Password changed successfully."})

    except (ValueError, TypeError) as e:
        logger.exception("change_password_view invalid request data")
        return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=400)
    except Exception as e:
        logger.exception("change_password_view unexpected error")
        raise


@library_required
def upload_profile_photo_view(request):
    """Upload admin's profile photo."""
    library = request.library
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request method."}, status=405)

    try:
        if "photo" not in request.FILES:
            return JsonResponse({"message": "No photo file provided."}, status=400)

        photo = request.FILES["photo"]
        user = request.user

        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if photo.content_type not in allowed_types:
            return JsonResponse(
                {"message": "Invalid file type. Please upload an image."}, status=400
            )

        if photo.size > 5 * 1024 * 1024:
            return JsonResponse(
                {"message": "File size must be less than 5MB."}, status=400
            )

        admin_profile, _ = AdminProfile.objects.get_or_create(user=user)

        if admin_profile.photo:
            admin_profile.photo.delete()

        admin_profile.photo = photo
        admin_profile.save()

        return JsonResponse({"message": "Photo uploaded successfully."})

    except (ValueError, TypeError) as e:
        logger.exception("upload_profile_photo_view invalid file or request data")
        return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=400)
    except Exception as e:
        logger.exception("upload_profile_photo_view unexpected error")
        raise


@library_required
def remove_profile_photo(request):
    """Remove admin's profile photo."""
    library = request.library
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request method."}, status=405)

    try:
        admin_profile, _ = AdminProfile.objects.get_or_create(user=request.user)

        if admin_profile.photo:
            admin_profile.photo.delete(save=True)

        return JsonResponse({"message": "Photo removed successfully."})

    except (ValueError, TypeError) as e:
        logger.exception("remove_profile_photo invalid request data")
        return JsonResponse({"message": f"An error occurred: {str(e)}"}, status=400)
    except Exception as e:
        logger.exception("remove_profile_photo unexpected error")
        raise
