"""
Book management service layer.
Handles core business logic for issuing and returning books.
"""

from datetime import datetime
from django.db import transaction
from apps.books.models import IssuedBook

__all__ = ["issue_book", "return_book"]


def issue_book(student, book, return_date):
    """
    Issue a book to a student.

    Args:
        student: StudentExtra instance
        book: Book instance
        return_date: datetime.date for return date

    Returns:
        IssuedBook instance

    Raises:
        ValueError: If book is out of stock
    """
    if book.quantity <= 0:
        raise ValueError(f"Book '{book.name}' is out of stock")

    # Perform quantity decrement and issued record creation atomically
    with transaction.atomic():
        book.quantity -= 1
        book.save()

        issued_book = IssuedBook.objects.create(
            student=student,
            book=book,
            enrollment=student.enrollment,
            book_name=book.name,
            issuedate=datetime.today().date(),
            return_date=return_date,
            returned=False,
        )

    return issued_book


def return_book(issued_book_id, library):
    """
    Mark a book as returned.

    Args:
        issued_book_id: ID of IssuedBook record
        library: Library instance (for authorization)

    Returns:
        IssuedBook instance

    Raises:
        IssuedBook.DoesNotExist: If issued book not found in library
    """
    issued_book = IssuedBook.objects.get(
        id=issued_book_id,
        book__library=library,
    )

    # Perform quantity increment and mark-as-returned atomically
    with transaction.atomic():
        if issued_book.book:
            book = issued_book.book
            book.quantity += 1
            book.save()

        issued_book.returned = True
        issued_book.save()

    return issued_book
