from django.shortcuts import render, redirect
from datetime import date
from .models import Book, IssuedBook
from apps.students.models import StudentExtra
from .filters import BookFilter
from django.contrib import messages
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Case, When, Value, BooleanField
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


# -------------------- BOOK MANAGEMENT VIEWS --------------------


from apps.core.views import library_required


@library_required
def addbook_view(request):
    """Add a new book to the current library."""
    library = request.library
    from .forms import BookForm

    form = BookForm()
    if request.method == "POST":
        form = BookForm(request.POST)
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
    category_choices = Book.CATEGORY_CHOICES
    language_choices = Book.LANGUAGE_CHOICES

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
            deleted_count, _ = Book.objects.filter(
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

        with transaction.atomic():
            for book_data in books_data:
                try:
                    # Only update books from current library
                    book = Book.objects.get(id=book_data["id"], library=library)
                    book.name = book_data["name"]
                    book.quantity = book_data["quantity"]
                    book.author = book_data["author"]
                    book.category = book_data["category"]
                    book.language = book_data["language"]
                    book.save()
                except Book.DoesNotExist:
                    continue

        messages.success(request, "Books updated successfully!")
        return redirect("viewbook")
    return redirect("viewbook")


@library_required
def issuebook_view(request):
    """Issue a book to a student in the current library."""
    library = request.library
    from .forms import IssuedBookForm
    from .services import issue_book

    form = IssuedBookForm(library)
    if request.method == "POST":
        form = IssuedBookForm(library, request.POST)
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

            # Use service layer
            try:
                issue_book(student, book, return_date)
                messages.success(
                    request, f"Book {book.name} issued successfully to {student.name}!"
                )
                return render(request, "library/bookissued.html", {"library": library})
            except ValueError as e:
                messages.error(request, str(e))

    return render(request, "library/issuebook.html", {"form": form, "library": library})


@library_required
def viewissuedbook_view(request):
    """View issued books in the current library."""
    library = request.library
    today = date.today()
    
    # Check if we're filtering for overdue books
    show_overdue_only = request.GET.get("show_overdue") == "true"
    
    # Annotate queryset with is_expired flag directly in the database
    issuedbooks = (
        IssuedBook.objects.filter(returned=False, book__library=library)
        .select_related("student", "book")
        .annotate(
            is_expired=Case(
                When(return_date__lt=today, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .order_by("book_name")
    )
    
    # Filter for overdue books if requested
    if show_overdue_only:
        issuedbooks = issuedbooks.filter(is_expired=True)
    
    # Pagination (10 per page) - now on the queryset, not a list
    paginator = Paginator(issuedbooks, 10)
    page = request.GET.get("page")
    
    try:
        issued_books_page = paginator.page(page)
    except PageNotAnInteger:
        issued_books_page = paginator.page(1)
    except EmptyPage:
        issued_books_page = paginator.page(paginator.num_pages)
    
    # Build tuples only for the current page's records
    li = []
    for ib in issued_books_page:
        try:
            # Get student name
            student_name = "N/A"
            if ib.student:
                student_name = ib.student.name
            elif ib.enrollment:
                try:
                    student = StudentExtra.objects.get(enrollment=ib.enrollment)
                    student_name = student.name
                except StudentExtra.DoesNotExist:
                    student_name = "Unknown Student"
            
            # Get book name - handle case where book might be deleted
            book_name = (
                ib.book_name
                if ib.book_name
                else (ib.book.name if ib.book else "Unknown Book")
            )
            
            # Calculate fine - PKR 500 if expired
            fine = 500 if ib.is_expired else 0
            
            # Build data tuple
            li.append(
                (
                    student_name,
                    ib.enrollment,
                    book_name,
                    ib.issuedate.strftime("%Y-%m-%d"),
                    ib.return_date.strftime("%Y-%m-%d"),
                    fine,  # Fine amount
                    ib.is_expired,  # Flag for expired status
                    ib.id,  # IssuedBook ID for return functionality
                )
            )
        except Exception as e:
            logger.error(f"Error processing issued book {ib.id}: {e}")
            continue
    
    # Create a paginator object for template access to pagination info
    # by wrapping our tuple list in the page object
    from django.core.paginator import Page
    li_page = Page(li, issued_books_page.number, paginator)
    
    return render(
        request,
        "library/viewissuedbook.html",
        {
            "li": li_page,
            "show_overdue_only": show_overdue_only,
            "library": library,
        },
    )


@library_required
def update_issued_books_view(request):
    """Update issued books in the current library."""
    library = request.library
    if request.method == "POST":
        books_data = json.loads(request.POST.get("books_data", "[]"))

        with transaction.atomic():
            for book_data in books_data:
                try:
                    # Only update issued books from current library
                    issued_book = IssuedBook.objects.get(
                        id=book_data["id"], book__library=library
                    )
                    issued_book.issue_date = book_data["issue_date"]
                    issued_book.return_date = book_data["return_date"]
                    issued_book.save()
                except IssuedBook.DoesNotExist:
                    continue

        messages.success(request, "Issued books updated successfully!")
        return redirect("viewissuedbook")
    return redirect("viewissuedbook")


@library_required
def return_issued_book_view(request):
    """Return a book to the current library."""
    library = request.library
    from .services import return_book

    if request.method == "POST":
        issuedbook_id = request.POST.get("issuedbook_id")
        try:
            return_book(issuedbook_id, library)
            messages.success(request, "Book returned successfully!")
        except IssuedBook.DoesNotExist:
            messages.error(request, "Issued book record not found!")
        except Exception as e:
            messages.error(request, f"Error returning book: {str(e)}")

    return redirect("viewissuedbook")
