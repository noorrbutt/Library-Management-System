from django.db import models
from django.contrib.auth.models import User
from apps.core.models import Library


class LibraryMembership(models.Model):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("member", "Member"),
    ]
    library = models.ForeignKey(
        Library, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_users",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    must_change_password = models.BooleanField(default=True)

    class Meta:
        app_label = "library"
        unique_together = ("library", "user")

    def __str__(self):
        return f"{self.user.email} - {self.library.name} ({self.role})"
