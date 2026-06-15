from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0011_add_club_to_shift_and_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="userbalance",
            name="session_mode",
            field=models.CharField(
                choices=[("prepaid", "Предоплата"), ("postpaid", "Постоплата")],
                default="prepaid",
                max_length=10,
                verbose_name="Session mode",
            ),
        ),
        migrations.AddField(
            model_name="userbalance",
            name="postpaid_minutes",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Postpaid minutes (debt)",
                help_text="Minutes played on credit in the current postpaid session.",
            ),
        ),
        migrations.AddField(
            model_name="userbalance",
            name="postpaid_started_at",
            field=models.DateTimeField(
                null=True, blank=True,
                verbose_name="Postpaid session started at",
            ),
        ),
        migrations.AddField(
            model_name="userbalance",
            name="postpaid_rate",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, null=True, blank=True,
                verbose_name="Postpaid rate (₽/hour)",
                help_text="Hourly rate used when closing the postpaid session.",
            ),
        ),
    ]
