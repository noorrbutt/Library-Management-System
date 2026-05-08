from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from . import forms, models
from .models import Book, StudentExtra, IssuedBook, LibraryMembership
from .filters import BookFilter, StudentFilter
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

logger = logging.getLogger(__name__)


@receiver(social_account_added)
def add_social_user_to_admin_group(request, sociallogin, **kwargs):
    user = sociallogin.user
    admin_group, _ = Group.objects.get_or_create(name="ADMIN")
    admin_group.user_set.add(user)


# -------------------- ROLE CHECK --------------------


def is_admin(user):
    return user.groups.filter(name="ADMIN").exists()


# -------------------- LIBRARY CONTEXT HELPERS --------------------


def get_user_library(user):
    """
    Get the library owned by the user (admin).
    Returns None if user is not an admin or has no library.
    """
    if not user.is_authenticated:
        return None
    try:
        return models.Library.objects.get(owner=user)
    except models.Library.DoesNotExist:
        return None
    except models.Library.MultipleObjectsReturned:
        # Should never happen, but return the first one
        return models.Library.objects.filter(owner=user).first()


def library_required(view_func):
    """
    Decorator to ensure the logged-in user has a library.
    Redirects to library creation page if not.
    """

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("adminlogin")

        library = None
        library_id = request.session.get("current_library_id") or request.session.get(
            "library_id"
        )
        if library_id:
            try:
                library = models.Library.objects.get(id=library_id)
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
            except models.Library.DoesNotExist:
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
    library_id = request.session.get("current_library_id") or request.session.get(
        "library_id"
    )
    if library_id:
        try:
            fallback_library = models.Library.objects.get(id=library_id)
            if (
                request.user == fallback_library.owner
                or LibraryMembership.objects.filter(
                    library=fallback_library, user=request.user
                ).exists()
            ):
                library = fallback_library
            else:
                logger.warning(
                    "dashboard_view: session library_id %s invalid for user %s",
                    library_id,
                    request.user.username,
                )
        except models.Library.DoesNotExist:
            logger.warning(
                "dashboard_view: session library_id %s invalid for user %s",
                library_id,
                request.user.username,
            )

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

    # Books added this month in this library
    books_this_month = Book.objects.filter(
        library=library,
        id__gte=Book.objects.filter(
            library=library,
            id__in=IssuedBook.objects.filter(
                issuedate__gte=month_start, book__library=library
            ).values_list("book_id", flat=True),
        ).count(),
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


class AdminLoginView(View):
    """
    Multi-tenant admin login view that shows library selection first,
    then login form. Admin can only access their own library.
    """

    template_name = "library/adminlogin.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")

        # Show all libraries for selection
        libraries = models.Library.objects.all().order_by("-created_at")
        context = {
            "libraries": libraries,
            "form": forms.AdminLoginForm(),  # Standard Django login form
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Admin selects library and enters credentials
        library_id = request.POST.get("selected_library")
        username = request.POST.get("username")
        password = request.POST.get("password")

        print(f"adminlogin post: selected_library={library_id}, username={username}")
        logger.debug(
            "adminlogin post: selected_library=%s username=%s",
            library_id,
            username,
        )

        if not library_id or not username or not password:
            messages.error(
                request, "Please select a library and enter your credentials."
            )
            libraries = models.Library.objects.all().order_by("-created_at")
            return render(
                request,
                self.template_name,
                {
                    "libraries": libraries,
                    "form": forms.AdminLoginForm(),
                },
            )

        try:
            library = models.Library.objects.get(id=library_id)

            # Authenticate user (username/password)
            user = authenticate(request, username=username, password=password)

            if user is None:
                messages.error(request, "Invalid username or password.")
                libraries = models.Library.objects.all().order_by("-created_at")
                return render(
                    request,
                    self.template_name,
                    {
                        "libraries": libraries,
                        "form": forms.AdminLoginForm(),
                    },
                )

            is_owner = user == library.owner
            is_member = False
            if not is_owner:
                is_member = LibraryMembership.objects.filter(
                    library=library, user=user
                ).exists()

            if not is_owner and not is_member:
                messages.error(request, "You do not have access to this library.")
                libraries = models.Library.objects.all().order_by("-created_at")
                return render(
                    request,
                    self.template_name,
                    {
                        "libraries": libraries,
                        "form": forms.AdminLoginForm(),
                    },
                )

            if is_owner and not is_admin(user):
                messages.error(request, "You do not have admin privileges.")
                libraries = models.Library.objects.all().order_by("-created_at")
                return render(
                    request,
                    self.template_name,
                    {
                        "libraries": libraries,
                        "form": forms.AdminLoginForm(),
                    },
                )

            if is_owner:
                admin_profile, created = models.AdminProfile.objects.get_or_create(
                    user=user
                )
                if admin_profile.library is None or admin_profile.library != library:
                    admin_profile.library = library
                    admin_profile.save()
                    logger.debug(
                        "adminlogin: linked admin profile %s to library %s",
                        admin_profile.id,
                        library.id,
                    )
            else:
                try:
                    user.admin_profile
                except models.AdminProfile.DoesNotExist:
                    models.AdminProfile.objects.create(user=user)

            if is_owner:
                LibraryMembership.objects.get_or_create(
                    library=library,
                    user=user,
                    defaults={
                        "role": "owner",
                        "added_by": user,
                        "must_change_password": False,
                    },
                )

            request.session["current_library_id"] = library.id
            request.session["library_id"] = library.id
            request.session["current_library_name"] = library.name
            request.session["is_library_owner"] = is_owner
            auth_login(request, user)
            logger.debug(
                "adminlogin: authenticated and logged in user %s", user.username
            )
            messages.success(request, f"Welcome back! Logged into {library.name}.")
            return redirect("dashboard")

        except models.Library.DoesNotExist:
            messages.error(request, "Library not found.")
            libraries = models.Library.objects.all().order_by("-created_at")
            return render(
                request,
                self.template_name,
                {
                    "libraries": libraries,
                    "form": forms.AdminLoginForm(),
                },
            )
        except Exception as e:
            print(f"adminlogin error: {e}")
            logger.exception("adminlogin failed")
            messages.error(request, f"An error occurred: {str(e)}")
            libraries = models.Library.objects.all().order_by("-created_at")
            return render(
                request,
                self.template_name,
                {
                    "libraries": libraries,
                    "form": forms.AdminLoginForm(),
                },
            )


def adminsignup_view(request):
    # --- GOOGLE / already-logged-in path ---
    if request.user.is_authenticated:
        form = forms.CreateLibraryNameForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                user = request.user
                admin_group, _ = Group.objects.get_or_create(name="ADMIN")
                admin_group.user_set.add(user)

                admin_profile, _ = models.AdminProfile.objects.get_or_create(user=user)
                library = models.Library.objects.create(
                    name=form.cleaned_data["library_name"],
                    owner=user,
                )
                admin_profile.library = library
                admin_profile.save()

                LibraryMembership.objects.create(
                    library=library,
                    user=user,
                    role="owner",
                    added_by=user,
                    must_change_password=False,
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
                logger.exception("adminsignup google-user exception")
                messages.error(request, f"An error occurred: {str(e)}")

        return render(
            request, "library/adminsignup.html", {"form": form, "google_user": True}
        )

    # --- Normal email/password signup path ---
    form = forms.CreateLibraryForm()
    if request.method == "POST":
        form = forms.CreateLibraryForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                )
                admin_group, _ = Group.objects.get_or_create(name="ADMIN")
                admin_group.user_set.add(user)
                admin_profile = models.AdminProfile.objects.create(user=user)
                library = models.Library.objects.create(
                    name=form.cleaned_data["library_name"],
                    owner=user,
                )
                admin_profile.library = library
                admin_profile.save()
                LibraryMembership.objects.create(
                    library=library,
                    user=user,
                    role="owner",
                    added_by=user,
                    must_change_password=False,
                )
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


@login_required
def add_member(request):
    library_id = request.session.get("current_library_id") or request.session.get(
        "library_id"
    )
    library = get_object_or_404(models.Library, id=library_id)
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
        import re

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
            models.AdminProfile.objects.get_or_create(user=existing_user)
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

            models.AdminProfile.objects.get_or_create(user=new_user)
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
    library = get_object_or_404(models.Library, id=library_id)
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
    library = get_object_or_404(models.Library, id=library_id)
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
    library = get_user_library(request.user)

    if library:
        admin_profile, _ = models.AdminProfile.objects.get_or_create(user=request.user)
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


# -------------------- ADMIN VIEWS --------------------


@library_required
def addbook_view(request):
    """Add a new book to the current library."""
    library = request.library
    form = forms.BookForm()
    if request.method == "POST":
        form = forms.BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.library = library
            book.save()
            return render(request, "library/bookadded.html", {"library": library})
    return render(request, "library/addbook.html", {"form": form, "library": library})


@library_required
def viewbook_view(request):
    """View all books in the current library."""
    library = request.library
    # Get books from current library only, sorted by name A-Z
    books = Book.objects.filter(library=library).order_by("name")

    # Search query
    query = request.GET.get("q", "")
    if query:
        books = books.filter(Q(name__icontains=query) | Q(author__icontains=query))

    # Apply filters using BookFilter
    book_filter = BookFilter(request.GET, queryset=books)
    books = book_filter.qs

    # Pagination (10 per page)
    paginator = Paginator(books, 10)
    page = request.GET.get("page")

    try:
        books = paginator.page(page)
    except PageNotAnInteger:
        books = paginator.page(1)
    except EmptyPage:
        books = paginator.page(paginator.num_pages)

    # Prepare choices for template (using display labels from model choices)
    category_choices = Book.catchoice
    language_choices = Book.langchoice

    return render(
        request,
        "library/viewbook.html",
        {
            "books": books,
            "filter": book_filter,
            "query": query,
            "category_choices": category_choices,
            "language_choices": language_choices,
            "library": library,
        },
    )


@library_required
def delete_books_view(request):
    """Delete books from current library."""
    library = request.library
    if request.method == "POST":
        selected_books = request.POST.getlist("selected_books")
        if selected_books:
            # Only delete books from current library
            deleted_count, _ = models.Book.objects.filter(
                id__in=selected_books, library=library
            ).delete()
            messages.success(request, f"{deleted_count} book(s) deleted successfully!")
        else:
            messages.warning(request, "No books selected for deletion.")
        return redirect("viewbook")
    return redirect("viewbook")


@library_required
def update_books_view(request):
    """Update books in current library."""
    library = request.library
    if request.method == "POST":
        books_data = json.loads(request.POST.get("books_data", "[]"))

        for book_data in books_data:
            try:
                # Only update books from current library
                book = models.Book.objects.get(id=book_data["id"], library=library)
                book.name = book_data["name"]
                book.quantity = book_data["quantity"]
                book.author = book_data["author"]
                book.category = book_data["category"]
                book.language = book_data["language"]
                book.save()
            except models.Book.DoesNotExist:
                continue

        messages.success(request, "Books updated successfully!")
        return redirect("viewbook")
    return redirect("viewbook")


@library_required
def issuebook_view(request):
    """Issue a book to a student in the current library."""
    library = request.library
    form = forms.IssuedBookForm(library)
    if request.method == "POST":
        form = forms.IssuedBookForm(library, request.POST)
        if form.is_valid():
            student = form.cleaned_data["student"]
            book = form.cleaned_data["book"]
            return_date = form.cleaned_data["return_date"]

            # Verify both student and book belong to current library
            if student.library != library or book.library != library:
                messages.error(request, "Invalid student or book selection.")
                return render(
                    request,
                    "library/issuebook.html",
                    {"form": form, "library": library},
                )

            # Create IssuedBook object
            obj = models.IssuedBook()
            obj.student = student
            obj.book = book
            obj.enrollment = student.enrollment
            obj.book_name = book.name
            obj.issuedate = date.today()
            obj.return_date = return_date
            obj.expirydate = return_date

            # Reduce book quantity
            if book.quantity > 0:
                book.quantity -= 1
                book.save()

                obj.save()
                messages.success(
                    request, f"Book {book.name} issued successfully to {student.name}!"
                )
                return render(request, "library/bookissued.html", {"library": library})
            else:
                messages.error(request, "This book is out of stock!")

    return render(request, "library/issuebook.html", {"form": form, "library": library})


@library_required
def viewissuedbook_view(request):
    """View issued books in the current library."""
    library = request.library
    # Only show non-returned books from current library
    issuedbooks = (
        models.IssuedBook.objects.filter(returned=False, book__library=library)
        .select_related("student", "book")
        .order_by("book_name")
    )

    li = []
    today = date.today()

    # Check if we're filtering for overdue books
    show_overdue_only = request.GET.get("show_overdue") == "true"

    for ib in issuedbooks:
        try:
            # Get student name
            student_name = "N/A"
            if ib.student:
                student_name = ib.student.name
            elif ib.enrollment:
                try:
                    student = models.StudentExtra.objects.get(enrollment=ib.enrollment)
                    student_name = student.name
                except models.StudentExtra.DoesNotExist:
                    student_name = "Unknown Student"

            # Get book name - handle case where book might be deleted
            book_name = (
                ib.book_name
                if ib.book_name
                else (ib.book.name if ib.book else "Unknown Book")
            )

            # Calculate fine - PKR 500 if expired
            fine = 0
            is_expired = False
            if today > ib.return_date:
                fine = 500  # PKR 500 fine
                is_expired = True

            # Only include in list if not filtering or if book is overdue
            if not show_overdue_only or is_expired:
                # Build data tuple
                li.append(
                    (
                        student_name,
                        ib.enrollment,
                        book_name,
                        ib.issuedate.strftime("%Y-%m-%d"),
                        ib.return_date.strftime("%Y-%m-%d"),
                        fine,  # Fine amount
                        is_expired,  # Flag for expired status
                        ib.id,  # IssuedBook ID for return functionality
                    )
                )

        except Exception as e:
            print(f"Error processing issued book {ib.id}: {e}")
            continue

    # Pagination (10 per page)
    paginator = Paginator(li, 10)
    page = request.GET.get("page")

    try:
        li_page = paginator.page(page)
    except PageNotAnInteger:
        li_page = paginator.page(1)
    except EmptyPage:
        li_page = paginator.page(paginator.num_pages)

    return render(
        request,
        "library/viewissuedbook.html",
        {
            "li": li_page,
            "show_overdue_only": show_overdue_only,
            "total_count": len(li),
            "library": library,
        },
    )


@library_required
def update_issued_books_view(request):
    """Update issued books in the current library."""
    library = request.library
    if request.method == "POST":
        books_data = json.loads(request.POST.get("books_data", "[]"))

        for book_data in books_data:
            try:
                # Only update issued books from current library
                issued_book = models.IssuedBook.objects.get(
                    id=book_data["id"], book__library=library
                )
                issued_book.issue_date = book_data["issue_date"]
                issued_book.return_date = book_data["return_date"]
                issued_book.save()
            except models.IssuedBook.DoesNotExist:
                continue

        messages.success(request, "Issued books updated successfully!")
        return redirect("viewissuedbook")
    return redirect("viewissuedbook")


@library_required
def return_issued_book_view(request):
    """Return a book to the current library."""
    library = request.library
    if request.method == "POST":
        issuedbook_id = request.GET.get("issuedbook_id")
        try:
            # Get the issued book record - verify it belongs to current library
            issued_book = models.IssuedBook.objects.get(
                id=issuedbook_id, book__library=library
            )

            # Get the book to increase quantity
            if issued_book.book:
                book = issued_book.book
                book.quantity += 1
                book.save()

            # Mark as returned
            issued_book.returned = True
            issued_book.save()

            messages.success(request, "Book returned successfully!")

        except models.IssuedBook.DoesNotExist:
            messages.error(request, "Issued book record not found!")
        except Exception as e:
            messages.error(request, f"Error returning book: {str(e)}")

    return redirect("viewissuedbook")


# -------------------- STUDENT VIEWS --------------------


@library_required
def addstudent_view(request):
    """Add a new student to the current library."""
    library = request.library
    form = forms.StudentExtraForm(library)
    if request.method == "POST":
        form = forms.StudentExtraForm(library, request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.library = library
            student.save()
            return redirect("studentadded")
    return render(
        request, "student/addstudent.html", {"form": form, "library": library}
    )


def studentadded_view(request):
    return render(request, "student/studentadded.html")


@library_required
def viewstudent_view(request):
    """View all students in the current library."""
    library = request.library
    # Get students from current library only, sorted by name A-Z
    students = models.StudentExtra.objects.filter(library=library).order_by("name")

    # Search functionality
    query = request.GET.get("q", "").strip()
    if query and query != "None":  # Handle the "None" string case
        students = students.filter(
            Q(name__icontains=query) | Q(enrollment__icontains=query)
        )

    # Initialize filter - use StudentFilter directly
    student_filter = StudentFilter(request.GET, queryset=students)
    students = student_filter.qs

    # Pagination (10 per page)
    paginator = Paginator(students, 10)
    page = request.GET.get("page")

    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    return render(
        request,
        "student/viewstudent.html",
        {
            "students": students,
            "filter": student_filter,
            "query": query if query != "None" else "",
            "gender_choices": models.StudentExtra.genchoice,
            "library": library,
        },
    )


@library_required
def delete_students_view(request):
    """Delete students from current library."""
    library = request.library
    if request.method == "POST":
        selected_students = request.POST.getlist("selected_students")
        if selected_students:
            # Only delete students from current library
            deleted_count, _ = models.StudentExtra.objects.filter(
                id__in=selected_students, library=library
            ).delete()
            messages.success(
                request, f"{deleted_count} Student(s) deleted successfully!"
            )
        else:
            messages.warning(request, "No student selected for deletion.")
        return redirect("viewstudent")
    return redirect("viewstudent")


@library_required
def update_students_view(request):
    """Update students in current library."""
    library = request.library
    if request.method == "POST":
        students_data = json.loads(request.POST.get("students_data", "[]"))
        for student_data in students_data:
            try:
                # Only update students from current library
                student = models.StudentExtra.objects.get(
                    id=student_data["id"], library=library
                )
                student.name = student_data["name"]
                student.enrollment = student_data["enrollment"]
                student.address = student_data["address"]
                student.phone = student_data["phone"]
                student.gender = student_data["gender"]
                student.save()
            except models.StudentExtra.DoesNotExist:
                continue

        messages.success(request, "Student(s) updated successfully!")
        return redirect("viewstudent")
    return redirect("viewstudent")


# -------------------- USER PROFILE VIEWS --------------------


@library_required
def userprofile_view(request):
    """Show admin's profile and library information."""
    library = request.library
    user = request.user
    admin_profile, _ = models.AdminProfile.objects.get_or_create(user=user)

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
        return HttpResponse(
            json.dumps({"message": "Invalid request method."}),
            content_type="application/json",
            status=405,
        )

    user = request.user

    try:
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        if not first_name or not last_name:
            return HttpResponse(
                json.dumps({"message": "First name and last name are required."}),
                content_type="application/json",
                status=400,
            )

        if not email or "@" not in email:
            return HttpResponse(
                json.dumps({"message": "Invalid email address."}),
                content_type="application/json",
                status=400,
            )

        if User.objects.filter(email=email).exclude(id=user.id).exists():
            return HttpResponse(
                json.dumps({"message": "Email address is already in use."}),
                content_type="application/json",
                status=400,
            )

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        date_of_birth = request.POST.get("date_of_birth", "").strip()

        admin_profile, _ = models.AdminProfile.objects.get_or_create(user=user)

        if phone:
            admin_profile.phone = phone
        if address:
            admin_profile.address = address
        if date_of_birth:
            admin_profile.date_of_birth = datetime.strptime(
                date_of_birth, "%Y-%m-%d"
            ).date()

        admin_profile.save()

        return HttpResponse(
            json.dumps({"message": "Profile updated successfully."}),
            content_type="application/json",
            status=200,
        )

    except Exception as e:
        return HttpResponse(
            json.dumps({"message": f"An error occurred: {str(e)}"}),
            content_type="application/json",
            status=500,
        )


@library_required
def update_library_view(request):
    """Update library information (name, etc)."""
    if not request.session.get("is_library_owner", False):
        return HttpResponse(
            json.dumps(
                {"message": "Only the library owner can update library details."}
            ),
            content_type="application/json",
            status=403,
        )
    library = request.library
    if request.method != "POST":
        return HttpResponse(
            json.dumps({"message": "Invalid request method."}),
            content_type="application/json",
            status=405,
        )

    try:
        library_name = request.POST.get("library_name", "").strip()

        if not library_name:
            return HttpResponse(
                json.dumps({"message": "Library name is required."}),
                content_type="application/json",
                status=400,
            )

        library.name = library_name
        library.save()

        return HttpResponse(
            json.dumps(
                {
                    "message": "Library updated successfully.",
                    "library_name": library.name,
                }
            ),
            content_type="application/json",
            status=200,
        )

    except Exception as e:
        return HttpResponse(
            json.dumps({"message": f"An error occurred: {str(e)}"}),
            content_type="application/json",
            status=500,
        )


@library_required
def change_password_view(request):
    """
    Handle AJAX request to change user password.
    """
    library = request.library
    if request.method != "POST":
        return HttpResponse(
            json.dumps({"message": "Invalid request method."}),
            content_type="application/json",
            status=405,
        )

    user = request.user

    try:
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()

        # Validation
        if not current_password or not new_password:
            return HttpResponse(
                json.dumps({"message": "All password fields are required."}),
                content_type="application/json",
                status=400,
            )

        # Check current password
        if not user.check_password(current_password):
            return HttpResponse(
                json.dumps({"message": "Current password is incorrect."}),
                content_type="application/json",
                status=400,
            )

        # Validate new password
        if len(new_password) < 8:
            return HttpResponse(
                json.dumps({"message": "Password must be at least 8 characters long."}),
                content_type="application/json",
                status=400,
            )

        if current_password == new_password:
            return HttpResponse(
                json.dumps(
                    {"message": "New password must be different from current password."}
                ),
                content_type="application/json",
                status=400,
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Update session to prevent automatic logout
        from django.contrib.auth import update_session_auth_hash

        update_session_auth_hash(request, user)

        return HttpResponse(
            json.dumps({"message": "Password changed successfully."}),
            content_type="application/json",
            status=200,
        )

    except Exception as e:
        return HttpResponse(
            json.dumps({"message": f"An error occurred: {str(e)}"}),
            content_type="application/json",
            status=500,
        )


@library_required
def upload_profile_photo_view(request):
    """Upload admin's profile photo."""
    library = request.library
    if request.method != "POST":
        return HttpResponse(
            json.dumps({"message": "Invalid request method."}),
            content_type="application/json",
            status=405,
        )

    try:
        if "photo" not in request.FILES:
            return HttpResponse(
                json.dumps({"message": "No photo file provided."}),
                content_type="application/json",
                status=400,
            )

        photo = request.FILES["photo"]
        user = request.user

        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if photo.content_type not in allowed_types:
            return HttpResponse(
                json.dumps({"message": "Invalid file type. Please upload an image."}),
                content_type="application/json",
                status=400,
            )

        if photo.size > 5 * 1024 * 1024:
            return HttpResponse(
                json.dumps({"message": "File size must be less than 5MB."}),
                content_type="application/json",
                status=400,
            )

        admin_profile, _ = models.AdminProfile.objects.get_or_create(user=user)

        if admin_profile.photo:
            admin_profile.photo.delete()

        admin_profile.photo = photo
        admin_profile.save()

        return HttpResponse(
            json.dumps({"message": "Photo uploaded successfully."}),
            content_type="application/json",
            status=200,
        )

    except Exception as e:
        return HttpResponse(
            json.dumps({"message": f"An error occurred: {str(e)}"}),
            content_type="application/json",
            status=500,
        )


@library_required
def remove_profile_photo(request):
    """Remove admin's profile photo."""
    library = request.library
    if request.method != "POST":
        return HttpResponse(
            json.dumps({"message": "Invalid request method."}),
            content_type="application/json",
            status=405,
        )

    try:
        admin_profile, _ = models.AdminProfile.objects.get_or_create(user=request.user)

        if admin_profile.photo:
            admin_profile.photo.delete(save=True)

        return HttpResponse(
            json.dumps({"message": "Photo removed successfully."}),
            content_type="application/json",
            status=200,
        )

    except Exception as e:
        return HttpResponse(
            json.dumps({"message": f"An error occurred: {str(e)}"}),
            content_type="application/json",
            status=500,
        )
