"""
Library management service layer.
Handles core business logic for creating libraries with admin setup.
"""

from django.contrib.auth.models import Group
from apps.core.models import Library, AdminProfile
from apps.members.models import LibraryMembership

__all__ = ["create_library_with_owner"]


def create_library_with_owner(user, library_name):
    """
    Create a new library with owner setup, admin profile, membership, and group.

    Args:
        user: User instance (library owner)
        library_name: String name for the library

    Returns:
        dict with keys: 'library', 'admin_profile', 'membership'

    Creates:
        - Library instance
        - AdminProfile for the owner
        - LibraryMembership with 'owner' role
        - Adds user to ADMIN group
        - Sets session keys in caller's request.session
    """
    # Create the library
    library = Library.objects.create(
        name=library_name,
        owner=user,
    )

    # Ensure ADMIN group exists and add user
    admin_group, _ = Group.objects.get_or_create(name="ADMIN")
    admin_group.user_set.add(user)

    # Create or update AdminProfile atomically and refresh user relation
    admin_profile, _ = AdminProfile.objects.update_or_create(
        user=user, defaults={"library": library}
    )
    # Ensure caller's user instance reflects updated related objects
    try:
        user.refresh_from_db()
    except Exception:
        pass

    # Create LibraryMembership with owner role
    membership, _ = LibraryMembership.objects.get_or_create(
        library=library,
        user=user,
        defaults={
            "role": "owner",
            "added_by": user,
            "must_change_password": False,
        },
    )

    return {
        "library": library,
        "admin_profile": admin_profile,
        "membership": membership,
    }
