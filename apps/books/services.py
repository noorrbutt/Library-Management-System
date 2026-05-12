"""
Book management service layer.
Handles core business logic for issuing and returning books.
"""

from datetime import datetime, timedelta
from apps.books.models import Book, IssuedBook

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

    # Reduce book quantity
    book.quantity -= 1
    book.save()

    # Create issued book record
    issued_book = IssuedBook.objects.create(
        student=student,
        book=book,
        enrollment=student.enrollment,
        book_name=book.name,
        issuedate=datetime.today().date(),
        return_date=return_date,
        expirydate=return_date,
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

    # Increase book quantity
    if issued_book.book:
        book = issued_book.book
        book.quantity += 1
        book.save()

    # Mark as returned
    issued_book.returned = True
    issued_book.save()

    return issued_book
