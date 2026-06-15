from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_remove_computer_balance"),
    ]

    operations = [
        migrations.CreateModel(
            name="TariffPlan",
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
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price in local currency",
                        max_digits=10,
                        verbose_name="Price",
                    ),
                ),
                (
                    "minutes",
                    models.PositiveIntegerField(
                        help_text="Play time granted in minutes", verbose_name="Minutes"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
            ],
            options={
                "verbose_name": "Tariff Plan",
                "verbose_name_plural": "Tariff Plans",
                "db_table": "billing_tariff_plans",
                "ordering": ["price"],
            },
        ),
    ]
