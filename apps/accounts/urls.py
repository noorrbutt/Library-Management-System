from django.urls import path
from . import views

urlpatterns = [
    path("adminlogin/", views.AdminLoginView.as_view(), name="adminlogin"),
    path("adminsignup/", views.adminsignup_view, name="adminsignup"),
    path("afterlogin/", views.afterlogin_view, name="afterlogin"),
    path(
        "force-password-change/",
        views.force_password_change,
        name="force_password_change",
    ),
]
