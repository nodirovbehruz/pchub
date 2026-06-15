from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0003_tag_game_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="game_type",
            field=models.CharField(
                choices=[("steam", "Steam"), ("local", "Local")],
                default="steam",
                help_text="Game type: steam or local",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="executable_path",
            field=models.CharField(
                blank=True,
                help_text="Full path to game executable (local games only, e.g. C:\\Games\\game.exe)",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="game",
            name="steam_app_id",
            field=models.BigIntegerField(
                blank=True,
                help_text="Steam App ID (Steam games only)",
                null=True,
                unique=True,
            ),
        ),
    ]
