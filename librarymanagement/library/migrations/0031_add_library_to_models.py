# Fixed migration: creates a default Library row before assigning FK to existing data

from django.db import migrations, models
import django.db.models.deletion


def create_default_library(apps, schema_editor):
    """
    Production had existing books/students but no Library row yet.
    We create a default superuser (if none exists) and a default Library,
    so the FK default=1 has something to point to.
    """
    User = apps.get_model("auth", "User")
    Library = apps.get_model("library", "Library")

    # Get or create a superuser to own the default library
    owner = User.objects.filter(is_superuser=True).first()
    if not owner:
        owner = User.objects.create_superuser(
            username="default_migration_admin",
            email="default-admin@example.com",
            password="changeme123",
        )

    # Create the default library with id=1 only if it doesn't exist
    if not Library.objects.filter(id=1).exists():
        lib = Library(
            id=1,
            name="Default Library",
            code="LIB-DEFAULT",
            owner=owner,
        )
        lib.save()


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0030_auto_20260417_2107"),
    ]

    operations = [
        # Step 1: create the default Library row so id=1 exists
        migrations.RunPython(create_default_library, migrations.RunPython.noop),
        # Step 2: now safely add the FK columns with default=1
        migrations.AddField(
            model_name="book",
            name="library",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="books",
                to="library.library",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="studentextra",
            name="library",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="students",
                to="library.library",
            ),
            preserve_default=False,
        ),
    ]
