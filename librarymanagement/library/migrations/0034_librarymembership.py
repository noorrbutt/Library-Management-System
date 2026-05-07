# Generated manually for LibraryMembership model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0033_auto_20260425_1652"),
    ]

    operations = [
        migrations.CreateModel(
            name="LibraryMembership",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("member", "Member")],
                        default="member",
                        max_length=10,
                    ),
                ),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("must_change_password", models.BooleanField(default=True)),
                (
                    "added_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invited_users",
                        to="auth.user",
                    ),
                ),
                (
                    "library",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="library.library",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="auth.user",
                    ),
                ),
            ],
            options={
                "unique_together": {("library", "user")},
            },
        ),
    ]
