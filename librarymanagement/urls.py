from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse


def strix_verify(request):
    return HttpResponse(
        "strix-verify-57268871b985d3c921745e1204c70f53",
        content_type="text/plain",
    )


urlpatterns = [
    path(".well-known/strix-verify.txt", strix_verify),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("books/", include("apps.books.urls")),
    path("students/", include("apps.students.urls")),
    path("members/", include("apps.members.urls")),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)