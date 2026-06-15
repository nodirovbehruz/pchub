from django.db import migrations


def backfill_club_from_group(apps, schema_editor):
    Computer = apps.get_model("computers", "Computer")
    for pc in Computer.objects.filter(club__isnull=True, group__isnull=False).select_related("group"):
        pc.club_id = pc.group.club_id
        pc.save(update_fields=["club"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("computers", "0014_backfill_computer_club"),
    ]

    operations = [
        migrations.RunPython(backfill_club_from_group, reverse_noop),
    ]
