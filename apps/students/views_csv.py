"""
CSV Import/Export and PDF Export views for Students.
"""

import csv
import io
import base64
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import StudentExtra
from apps.core.views import library_required

# ── STUDENT CSV EXPORT


@library_required
def export_students_csv_view(request):
    """Download all students as a CSV file."""
    library = request.library
    students = StudentExtra.objects.filter(library=library).order_by("name")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="students.csv"'

    writer = csv.writer(response)
    writer.writerow(["name", "enrollment", "address", "phone", "gender"])
    for s in students:
        writer.writerow(
            [s.name, s.enrollment, s.address or "", s.phone or "", s.gender]
        )

    return response


# ── STUDENT PDF EXPORT


@library_required
def export_students_pdf_view(request):
    """Download all students as a PDF table."""
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
        return redirect("viewstudent")

    library = request.library
    students = StudentExtra.objects.filter(library=library).order_by("name")

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
        Paragraph(f"Students — {library.name}", title_style),
        Spacer(1, 0.3 * cm),
    ]

    data = [["#", "Name", "Enrollment", "Gender", "Phone", "Address"]]
    for i, s in enumerate(students, 1):
        data.append(
            [
                str(i),
                s.name or "",
                s.enrollment,
                s.gender or "",
                s.phone or "",
                s.address or "",
            ]
        )

    col_widths = [1 * cm, 6 * cm, 5 * cm, 3 * cm, 4 * cm, 7.5 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
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
    response["Content-Disposition"] = 'attachment; filename="students.pdf"'
    return response


# ── STUDENT CSV SAMPLE DOWNLOAD


@library_required
def download_students_csv_sample_view(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="students_sample.csv"'
    writer = csv.writer(response)
    writer.writerow(["name", "enrollment", "address", "phone", "gender"])
    writer.writerow(
        ["Ali Hassan", "2024-CS-001", "Karachi, Pakistan", "03001234567", "Male"]
    )
    writer.writerow(
        ["Sara Ahmed", "2024-CS-002", "Lahore, Pakistan", "03009876543", "Female"]
    )
    return response


# ── STUDENT CSV IMPORT

STUDENT_MODEL_FIELDS = [
    ("name", "Full Name", True),
    ("enrollment", "Enrollment Number", True),
    ("phone", "Phone", False),
    ("address", "Address", False),
    ("gender", "Gender", False),
]

VALID_GENDERS = ["Male", "Female"]


@library_required
def import_students_view(request):
    """
    Step 1 (GET)         : Show upload form.
    Step 2 (POST upload) : Parse CSV, show column-mapping UI.
    Step 3 (POST confirm): Validate mapped rows and bulk-create students.
    """
    library = request.library

    # ── STEP 3: Confirm & save
    if request.method == "POST" and request.POST.get("action") == "confirm_import":
        mapping = {}
        csv_b64 = request.POST.get("csv_b64", "")
        if not csv_b64:
            messages.error(request, "CSV data missing. Please upload the file again.")
            return redirect("import_students")
        try:
            csv_bytes = base64.b64decode(csv_b64.encode('ascii'))
            csv_text = csv_bytes.decode('utf-8')
        except Exception:
            messages.error(request, "Could not read CSV data. Please upload the file again.")
            return redirect("import_students")
        headers_raw = request.POST.get("csv_headers", "")
        headers = headers_raw.split('||') if headers_raw else []

        for field, label, required in STUDENT_MODEL_FIELDS:
            col_idx = request.POST.get(f"map_{field}", "")
            if col_idx != "":
                mapping[field] = int(col_idx)

        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        students_to_create = []
        errors = []
        skipped_duplicates = 0

        # Get existing enrollments to detect duplicates fast
        existing_enrollments = set(
            StudentExtra.objects.filter(library=library).values_list(
                "enrollment", flat=True
            )
        )

        for row_num, row in enumerate(rows, start=2):
            if not any(cell.strip() for cell in row):
                continue

            student_kwargs = {"library": library}
            row_error = False

            for field, label, required in STUDENT_MODEL_FIELDS:
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

                if field == "gender" and value and value not in VALID_GENDERS:
                    value = "Female"  # fallback default

                student_kwargs[field] = value if value else None

            if row_error:
                continue

            enrollment = student_kwargs.get("enrollment", "")
            if enrollment in existing_enrollments:
                skipped_duplicates += 1
                continue
            existing_enrollments.add(enrollment)

            student_kwargs.setdefault("gender", "Female")
            students_to_create.append(StudentExtra(**student_kwargs))

        imported_count = 0
        if students_to_create:
            try:
                with transaction.atomic():
                    StudentExtra.objects.bulk_create(students_to_create)
                    imported_count = len(students_to_create)
            except Exception as e:
                messages.error(request, f"Import failed: {str(e)}")
                return redirect("import_students")

        if imported_count:
            messages.success(
                request, f"✓ {imported_count} student(s) imported successfully!"
            )
        if skipped_duplicates:
            messages.warning(
                request,
                f"{skipped_duplicates} row(s) skipped — enrollment number already exists.",
            )
        if errors:
            for err in errors[:10]:
                messages.warning(request, err)
        if not students_to_create and not errors and not skipped_duplicates:
            messages.warning(request, "No valid rows found in the CSV.")

        return redirect("viewstudent")

    # ── STEP 2: Upload & show mapping UI
    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]

        if not csv_file.name.endswith(".csv"):
            messages.error(request, "Please upload a .csv file.")
            return redirect("import_students")

        try:
            decoded = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            messages.error(
                request, "Could not read file. Make sure it's UTF-8 encoded."
            )
            return redirect("import_students")

        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)

        if len(rows) < 2:
            messages.error(
                request, "CSV must have at least a header row and one data row."
            )
            return redirect("import_students")

        csv_headers = rows[0]
        preview_rows = rows[1:6]

        data_rows_io = io.StringIO()
        writer = csv.writer(data_rows_io)
        for row in rows[1:]:
            writer.writerow(row)
        csv_b64 = base64.b64encode(data_rows_io.getvalue().encode('utf-8')).decode('ascii')

        return render(
            request,
            "student/import_students.html",
            {
                "library": library,
                "step": "mapping",
                "csv_headers": csv_headers,
                "preview_rows": preview_rows,
                "model_fields": STUDENT_MODEL_FIELDS,
                "csv_b64": csv_b64,
                "headers_joined": "||".join(csv_headers),
                "total_rows": len(rows) - 1,
            },
        )

    return render(
        request,
        "student/import_students.html",
        {
            "library": library,
            "step": "upload",
            "model_fields": STUDENT_MODEL_FIELDS,
        },
    )
