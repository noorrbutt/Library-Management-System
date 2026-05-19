from django.urls import path
from . import views
from .views_csv import (
    import_books_view,
    export_books_csv_view,
    export_books_pdf_view,
    download_books_csv_sample_view,
)

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
    path("import/", import_books_view, name="import_books"),
    path("export/csv/", export_books_csv_view, name="export_books_csv"),
    path("export/pdf/", export_books_pdf_view, name="export_books_pdf"),
    path("import/sample/", download_books_csv_sample_view, name="books_csv_sample"),
]
