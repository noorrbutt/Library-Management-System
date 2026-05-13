"""
Library membership management service layer.
Handles core business logic for adding members to libraries.
"""

import re
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from apps.members.models import LibraryMembership
from apps.core.models import AdminProfile

__all__ = ["add_member_to_library"]


def add_member_to_library(owner, library, email, username):
    """
    Add a member to a library. Handles both new and existing users.

    Args:
        owner: User instance (library owner)
        library: Library instance
        email: String email address (lowercase)
        username: String username

    Returns:
        dict with keys: 'user', 'membership', 'is_new', 'temp_password'
        - is_new: True if user was created, False if existing
        - temp_password: Temporary password (None if existing user)

    Raises:
        ValueError: If email/username invalid or username already taken
        Exception: If user already member of this library
    """
    email = email.strip().lower()
    username = username.strip()

    # Validate email
    if not email or "@" not in email:
        raise ValueError("Please enter a valid email address.")

    # Validate username
    if not username:
        raise ValueError("Please enter a username for the new member.")

    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise ValueError("Username may only contain letters, numbers and underscores.")

    # Check if username already taken
    if User.objects.filter(username=username).exclude(id=owner.id).exists():
        raise ValueError(
            f"The username '{username}' is already taken. "
            "Please choose a different one."
        )

    # Try to find existing user by email
    existing_user = User.objects.filter(email=email).first()

    if existing_user:
        # User exists — check if already member
        if LibraryMembership.objects.filter(
            library=library, user=existing_user
        ).exists():
            raise Exception(
                f"'{existing_user.username}' ({email}) is already a member "
                "of this library."
            )

        # Add as member (they keep existing credentials)
        AdminProfile.objects.get_or_create(user=existing_user)

        membership = LibraryMembership.objects.create(
            library=library,
            user=existing_user,
            added_by=owner,
            role="member",
            must_change_password=False,
        )

        return {
            "user": existing_user,
            "membership": membership,
            "is_new": False,
            "temp_password": None,
        }

    # Create brand-new user
    temp_password = User.objects.make_random_password(length=10)

    new_user = User.objects.create(
        email=email,
        username=username,
        password=make_password(temp_password),
    )

    AdminProfile.objects.get_or_create(user=new_user)

    membership = LibraryMembership.objects.create(
        library=library,
        user=new_user,
        added_by=owner,
        role="member",
        must_change_password=True,
    )

    return {
        "user": new_user,
        "membership": membership,
        "is_new": True,
        "temp_password": temp_password,
    }
