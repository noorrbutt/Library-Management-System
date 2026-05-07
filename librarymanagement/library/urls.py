from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("adminclick/", views.adminclick_view, name="adminclick"),
    path("adminsignup/", views.adminsignup_view, name="adminsignup"),
    path("afterlogin/", views.afterlogin_view, name="afterlogin"),
    # Admin: Book management
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
    # Admin: Student management
    path("addstudent/", views.addstudent_view, name="addstudent"),
    path("studentadded/", views.studentadded_view, name="studentadded"),
    path("viewstudent/", views.viewstudent_view, name="viewstudent"),
    path("deletestudents/", views.delete_students_view, name="deletestudents"),
    path("updatestudents/", views.update_students_view, name="updatestudents"),
    # User Profile Management
    path("userprofile/", views.userprofile_view, name="userprofile"),
    path("update-profile/", views.update_profile_view, name="update_profile"),
    path("update-library/", views.update_library_view, name="update_library"),
    path("add-member/", views.add_member, name="add_member"),
    path("view-members/", views.view_members, name="view_members"),
    path(
        "force-password-change/",
        views.force_password_change,
        name="force_password_change",
    ),
    path("remove-member/", views.remove_member, name="remove_member"),
    path("change-password/", views.change_password_view, name="change_password"),
    path(
        "upload-profile-photo/",
        views.upload_profile_photo_view,
        name="upload_profile_photo",
    ),
    path(
        "remove-profile-photo/", views.remove_profile_photo, name="remove_profile_photo"
    ),
]
