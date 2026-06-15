import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create UserBalance table
        migrations.CreateModel(
            name="UserBalance",
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
                    "minutes_remaining",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Minutes Remaining"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=False, verbose_name="Is Active"),
                ),
                (
                    "last_updated",
                    models.DateTimeField(auto_now=True, verbose_name="Last Updated"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="balance",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Balance",
                "verbose_name_plural": "User Balances",
                "db_table": "billing_user_balance",
                "ordering": ["user__username"],
            },
        ),
        # Add user FK to Payment
        migrations.AddField(
            model_name="payment",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
        # Make Payment.computer nullable (historical data preserved)
        migrations.AlterField(
            model_name="payment",
            name="computer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="computer_payments",
                to="computers.computer",
                verbose_name="Computer",
                help_text="Legacy field — computer where session was played",
            ),
        ),
    ]
