import secrets
import string

from django.db import migrations, models


def _make_token():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def populate_tokens(apps, schema_editor):
    Club = apps.get_model("clubs", "Club")
    used = set()
    for club in Club.objects.all():
        token = _make_token()
        while token in used:
            token = _make_token()
        used.add(token)
        club.club_token = token
        club.save(update_fields=["club_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0004_clubsettings"),
    ]

    operations = [
        # Step 1: add nullable column
        migrations.AddField(
            model_name="club",
            name="club_token",
            field=models.CharField(
                blank=True, default="", max_length=8, verbose_name="Club token",
            ),
        ),
        # Step 2: fill existing rows
        migrations.RunPython(populate_tokens, migrations.RunPython.noop),
        # Step 3: add unique constraint
        migrations.AlterField(
            model_name="club",
            name="club_token",
            field=models.CharField(
                blank=True,
                help_text="8-char code for shell setup — auto-links PC to this club",
                max_length=8,
                unique=True,
                verbose_name="Club token",
            ),
        ),
    ]
