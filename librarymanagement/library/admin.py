"""
Admin registrations moved to app-specific admin.py files:
- apps/core/admin.py: Library, AdminProfile
- apps/members/admin.py: LibraryMembership
- apps/books/admin.py: Book, IssuedBook
- apps/students/admin.py: StudentExtra
"""

from django.contrib import admin

# This file is kept for backward compatibility but all models are now
# registered in their respective app admin.py files
