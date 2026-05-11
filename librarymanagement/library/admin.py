from django.contrib import admin
from apps.books.models import Book, IssuedBook
from apps.students.models import StudentExtra


# Register your models here.
class BookAdmin(admin.ModelAdmin):
    pass


admin.site.register(Book, BookAdmin)


class StudentExtraAdmin(admin.ModelAdmin):
    pass


admin.site.register(StudentExtra, StudentExtraAdmin)


class IssuedBookAdmin(admin.ModelAdmin):
    pass


admin.site.register(IssuedBook, IssuedBookAdmin)
