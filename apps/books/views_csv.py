"""
CSV Import/Export + PDF Export views for Books.
Add these to apps/books/views.py (or keep as a separate file and import).
"""

import csv
import io
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction, IntegrityError
from .models import Book
from apps.core.views import library_required

# ── BOOK CSV EXPORT ────────────────────────────────────────────────────────────


@library_required
def export_books_csv_view(request):
    """Download all books as a CSV file."""
    library = request.library
    books = Book.objects.filter(library=library).order_by("name")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="books.csv"'

    writer = csv.writer(response)
    writer.writerow(["name", "quantity", "author", "category", "language"])  # header
    for book in books:
        writer.writerow(
            [book.name, book.quantity, book.author, book.category, book.language]
        )

    return response


# ── BOOK PDF EXPORT ────────────────────────────────────────────────────────────


@library_required
def export_books_pdf_view(request):
    """Download all books as a PDF table using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        messages.error(
            request, "PDF export requires reportlab. Run: pip install reportlab"
        )
        return redirect("viewbook")

    library = request.library
    books = Book.objects.filter(library=library).order_by("name")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor("#1e3a5f"),
    )

    elements = [
        Paragraph(f"Books — {library.name}", title_style),
        Spacer(1, 0.3 * cm),
    ]

    # Table data
    data = [["#", "Book Name", "Author", "Quantity", "Category", "Language"]]
    for i, book in enumerate(books, 1):
        data.append(
            [
                str(i),
                book.name,
                book.author,
                str(book.quantity),
                book.category,
                book.language,
            ]
        )

    col_widths = [1 * cm, 8 * cm, 6 * cm, 2.5 * cm, 4.5 * cm, 3.5 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f0f4f8")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="books.pdf"'
    return response


# ── BOOK CSV SAMPLE DOWNLOAD ───────────────────────────────────────────────────


@library_required
def download_books_csv_sample_view(request):
    """Download a sample CSV so users know the expected format."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="books_sample.csv"'
    writer = csv.writer(response)
    writer.writerow(["name", "quantity", "author", "category", "language"])
    writer.writerow(["The Alchemist", "5", "Paulo Coelho", "Novel", "English"])
    writer.writerow(["Sapiens", "3", "Yuval Noah Harari", "History", "English"])
    return response


# ── BOOK CSV IMPORT ────────────────────────────────────────────────────────────

BOOK_MODEL_FIELDS = [
    ("name", "Book Name", True),  # (field_name, label, required)
    ("author", "Author", True),
    ("quantity", "Quantity", True),
    ("category", "Category", False),
    ("language", "Language", False),
]


@library_required
def import_books_view(request):
    """
    Step 1 (GET)        : Show upload form.
    Step 2 (POST upload): Parse CSV, show column-mapping UI.
    Step 3 (POST confirm): Validate mapped rows and bulk-create books.
    """
    library = request.library

    # ── STEP 3: Confirm & save ─────────────────────────────────────────────────
    if request.method == "POST" and request.POST.get("action") == "confirm_import":
        mapping = {}  # model_field → csv_column_index (int)
        csv_data = request.POST.get("csv_data", "")
        headers_raw = request.POST.get("csv_headers", "")
        headers = headers_raw.split("||") if headers_raw else []

        for field, label, required in BOOK_MODEL_FIELDS:
            col_idx = request.POST.get(f"map_{field}", "")
            if col_idx != "":
                mapping[field] = int(col_idx)

        reader = csv.reader(io.StringIO(csv_data))
        rows = list(reader)

        books_to_create = []
        errors = []

        for row_num, row in enumerate(rows, start=2):
            if not any(cell.strip() for cell in row):
                continue

            book_kwargs = {"library": library}
            row_error = False

            for field, label, required in BOOK_MODEL_FIELDS:
                if field not in mapping:
                    if required:
                        errors.append(
                            f"Row {row_num}: required field '{label}' not mapped."
                        )
                        row_error = True
                    continue

                idx = mapping[field]
                value = row[idx].strip() if idx < len(row) else ""

                if required and not value:
                    errors.append(f"Row {row_num}: '{label}' is empty.")
                    row_error = True
                    continue

                if field == "quantity":
                    try:
                        value = int(value)
                        if value < 0:
                            raise ValueError
                    except ValueError:
                        errors.append(
                            f"Row {row_num}: 'Quantity' must be a positive number (got '{value}')."
                        )
                        row_error = True
                        continue

                if not required and value == "":
                    continue

                book_kwargs[field] = value

            if not row_error:
                book_kwargs.setdefault("category", "Education")
                book_kwargs.setdefault("language", "English")
                books_to_create.append(Book(**book_kwargs))
            if not row_error:

                book_kwargs.setdefault("category", "Education")
                book_kwargs.setdefault("language", "English")
                books_to_create.append(Book(**book_kwargs))

        if errors:
            pass

        imported_count = 0
        if books_to_create:
            try:
                with transaction.atomic():
                    Book.objects.bulk_create(books_to_create)
                    imported_count = len(books_to_create)
            except Exception as e:
                messages.error(request, f"Import failed: {str(e)}")
                return redirect("import_books")

        if imported_count:
            messages.success(
                request, f"✓ {imported_count} book(s) imported successfully!"
            )
        if errors:
            for err in errors[:10]:  # cap at 10 shown
                messages.warning(request, err)
        if not books_to_create and not errors:
            messages.warning(request, "No valid rows found in the CSV.")

        return redirect("viewbook")

    # ── STEP 2: Upload & show mapping UI ──────────────────────────────────────
    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            messages.error(request, "Please upload a .csv file.")
            return redirect("import_books")

        try:
            decoded = csv_file.read().decode("utf-8-sig")  # utf-8-sig handles BOM
        except UnicodeDecodeError:
            messages.error(
                request, "Could not read file. Make sure it's UTF-8 encoded."
            )
            return redirect("import_books")

        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)

        if len(rows) < 2:
            messages.error(
                request, "CSV must have at least a header row and one data row."
            )
            return redirect("import_books")

        csv_headers = rows[0]
        preview_rows = rows[1:6]  # show first 5 data rows as preview
        # Store data rows (excluding header) for later confirmation
        data_rows_io = io.StringIO()
        writer = csv.writer(data_rows_io)
        for row in rows[1:]:
            writer.writerow(row)
        csv_data_str = data_rows_io.getvalue()

        return render(
            request,
            "library/import_books.html",
            {
                "library": library,
                "step": "mapping",
                "csv_headers": csv_headers,
                "preview_rows": preview_rows,
                "model_fields": BOOK_MODEL_FIELDS,
                "csv_data": csv_data_str,
                "headers_joined": "||".join(csv_headers),
                "total_rows": len(rows) - 1,
            },
        )

    # ── STEP 1: Show upload form ───────────────────────────────────────────────
    return render(
        request,
        "library/import_books.html",
        {
            "library": library,
            "step": "upload",
            "model_fields": BOOK_MODEL_FIELDS,
        },
    )
