from django.urls import path
from . import views

urlpatterns = [
    path("add-member/", views.add_member, name="add_member"),
    path("view-members/", views.view_members, name="view_members"),
    path("remove-member/", views.remove_member, name="remove_member"),
]
