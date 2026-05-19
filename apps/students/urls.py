from django.urls import path
from . import views
from .views_csv import (
    import_students_view,
    export_students_csv_view,
    export_students_pdf_view,
    download_students_csv_sample_view,
)

urlpatterns = [
    path("addstudent/", views.addstudent_view, name="addstudent"),
    path("studentadded/", views.studentadded_view, name="studentadded"),
    path("viewstudent/", views.viewstudent_view, name="viewstudent"),
    path("deletestudents/", views.delete_students_view, name="deletestudents"),
    path("updatestudents/", views.update_students_view, name="updatestudents"),
    path("import/", import_students_view, name="import_students"),
    path("export/csv/", export_students_csv_view, name="export_students_csv"),
    path("export/pdf/", export_students_pdf_view, name="export_students_pdf"),
    path(
        "import/sample/", download_students_csv_sample_view, name="students_csv_sample"
    ),
]
