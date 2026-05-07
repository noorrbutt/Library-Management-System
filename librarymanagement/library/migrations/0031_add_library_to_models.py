# Generated manually for adding library FK to Book and StudentExtra

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0030_auto_20260417_2107"),
    ]

    operations = [
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
