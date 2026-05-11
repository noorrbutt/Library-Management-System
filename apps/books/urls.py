from django.urls import path
from . import views

urlpatterns = [
    path("addbook/", views.addbook_view, name="addbook"),
    path("viewbook/", views.viewbook_view, name="viewbook"),
    path("issuebook/", views.issuebook_view, name="issuebook"),
    path("viewissuedbook/", views.viewissuedbook_view, name="viewissuedbook"),
    path("deletebooks/", views.delete_books_view, name="deletebooks"),
    path("updatebooks/", views.update_books_view, name="updatebooks"),
    path(
        "return-issued-book/", views.return_issued_book_view, name="return_issued_book"
    ),
    path(
        "update-issued-books/",
        views.update_issued_books_view,
        name="update_issued_books",
    ),
]
