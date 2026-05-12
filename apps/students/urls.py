from django.urls import path
from . import views

urlpatterns = [
    path("addstudent/", views.addstudent_view, name="addstudent"),
    path("studentadded/", views.studentadded_view, name="studentadded"),
    path("viewstudent/", views.viewstudent_view, name="viewstudent"),
    path("deletestudents/", views.delete_students_view, name="deletestudents"),
    path("updatestudents/", views.update_students_view, name="updatestudents"),
]
