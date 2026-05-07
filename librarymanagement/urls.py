from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from librarymanagement.library.views import AdminLoginView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),  # ← allauth handles all auth urls
    path("", include("librarymanagement.library.urls")),
    path("adminlogin/", AdminLoginView.as_view(), name="adminlogin"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
