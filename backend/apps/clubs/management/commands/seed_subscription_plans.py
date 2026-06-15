from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.clubs.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Seed 3 platform subscription plans: Free / Starter / Business."

    def handle(self, *args, **options):
        plans = [
            ("free", "Free", Decimal("0"), 5, {
                "online_booking": False, "club_accounts": False, "telegram": False,
            }),
            ("starter", "Starter", Decimal("2990"), 20, {
                "online_booking": True, "club_accounts": True, "telegram": True,
                "cloud_payments": False,
            }),
            ("business", "Business", Decimal("5990"), 0, {
                "online_booking": True, "club_accounts": True, "telegram": True,
                "cloud_payments": True, "kkm_integration": True, "custom_roles": True,
                "smart_gamer": True, "promised_payment": True, "deposit_transfer": True,
            }),
        ]
        for tier, name, price, max_pcs, features in plans:
            obj, created = SubscriptionPlan.objects.update_or_create(
                tier=tier,
                defaults={
                    "name": name, "monthly_price": price,
                    "max_pcs": max_pcs, "features": features,
                },
            )
            self.stdout.write(f"  {name}: {'created' if created else 'updated'}")
        self.stdout.write(self.style.SUCCESS("Done."))
