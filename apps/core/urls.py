from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("adminclick/", views.adminclick_view, name="adminclick"),
    path("userprofile/", views.userprofile_view, name="userprofile"),
    path("update-profile/", views.update_profile_view, name="update_profile"),
    path("update-library/", views.update_library_view, name="update_library"),
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
