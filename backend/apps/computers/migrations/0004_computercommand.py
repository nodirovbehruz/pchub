import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("computers", "0003_alter_computer_hardware_id"),
        ("games", "0005_game_text_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ComputerCommand",
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
                    "command_type",
                    models.CharField(
                        choices=[
                            ("install", "Install"),
                            ("reinstall", "Reinstall"),
                            ("uninstall", "Uninstall"),
                            ("update", "Update"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "computer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="commands",
                        to="computers.computer",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_commands",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="commands",
                        to="games.game",
                    ),
                ),
            ],
            options={
                "verbose_name": "Computer Command",
                "verbose_name_plural": "Computer Commands",
                "db_table": "computer_commands",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="computercommand",
            index=models.Index(
                fields=["computer", "status"],
                name="computer_commands_computer_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="computercommand",
            index=models.Index(
                fields=["-created_at"],
                name="computer_commands_created_at_idx",
            ),
        ),
    ]
