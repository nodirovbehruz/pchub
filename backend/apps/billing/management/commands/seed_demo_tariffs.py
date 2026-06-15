from datetime import time

from django.core.management.base import BaseCommand

from apps.billing.models import PricePeriod, TariffPlan, TariffPrice, TariffType
from apps.clubs.models import Club
from apps.computers.models import ComputerGroup


class Command(BaseCommand):
    help = "Seed 4 demo tariffs for 'Мой клуб' matching SmartShell reference screen."

    def add_arguments(self, parser):
        parser.add_argument("--club", type=str, default="Мой клуб")

    def handle(self, *args, **options):
        club_name = options["club"]
        try:
            club = Club.objects.get(name=club_name)
        except Club.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Club '{club_name}' not found"))
            return

        main = ComputerGroup.objects.filter(club=club, name="Main Zone").first()
        vip = ComputerGroup.objects.filter(club=club, name="VIP Lounge").first()
        if not main or not vip:
            self.stdout.write(self.style.ERROR("Groups Main Zone / VIP Lounge missing"))
            return

        # 1. Абонемент "5 часов абонемент" — 5h, life 30 days
        #    Main: day 1000 / night 900   VIP: day 1200 / night 1000
        self._upsert(
            club, "5 часов абонемент", TariffType.SUBSCRIPTION,
            minutes=300, life_days=30,
            schedule_days="1234567",
            schedule_start=time(0, 0), schedule_end=time(0, 0),
            is_night=True, apply_discount=True, has_schedule=True,
            prices=[
                (main, PricePeriod.DAY, 1000), (main, PricePeriod.NIGHT, 900),
                (vip, PricePeriod.DAY, 1200), (vip, PricePeriod.NIGHT, 1000),
            ],
        )

        # 2. Пакетный "Ночной пакет" — действует 22:00–08:00, до 08:00
        #    Main: 300 (day=night)   VIP: 500 (day=night)
        self._upsert(
            club, "Ночной пакет", TariffType.PACKAGE,
            valid_until_time=time(8, 0),
            schedule_days="1234567",
            schedule_start=time(22, 0), schedule_end=time(8, 0),
            is_night=True, apply_discount=True, has_schedule=True,
            prices=[
                (main, PricePeriod.DAY, 300), (main, PricePeriod.NIGHT, 300),
                (vip, PricePeriod.DAY, 500), (vip, PricePeriod.NIGHT, 500),
            ],
        )

        # 3. Поминутный "Поминутный" — 1 минута
        #    Main: 2   VIP: 2
        self._upsert(
            club, "Поминутный", TariffType.PER_MINUTE,
            minutes=1,
            schedule_days="3457126",
            schedule_start=time(0, 0), schedule_end=time(20, 38),
            apply_discount=True, has_schedule=False,
            prices=[
                (main, PricePeriod.DAY, 2), (main, PricePeriod.NIGHT, 2),
                (vip, PricePeriod.DAY, 2), (vip, PricePeriod.NIGHT, 2),
            ],
        )

        # 4. Фиксированный "1 час"
        #    Main: day 100 / night 100   VIP: day 200 / night 200
        self._upsert(
            club, "1 час", TariffType.FIXED,
            minutes=60,
            schedule_days="1234567",
            schedule_start=time(0, 0), schedule_end=time(0, 0),
            is_night=True, apply_discount=True, has_schedule=True,
            prices=[
                (main, PricePeriod.DAY, 100), (main, PricePeriod.NIGHT, 100),
                (vip, PricePeriod.DAY, 200), (vip, PricePeriod.NIGHT, 200),
            ],
        )

        self.stdout.write(self.style.SUCCESS(
            f"Done. Tariffs: {TariffPlan.objects.filter(club=club).count()} | "
            f"Prices: {TariffPrice.objects.filter(tariff__club=club).count()}"
        ))

    def _upsert(self, club, name, tariff_type, *, prices, **fields):
        defaults = {
            "tariff_type": tariff_type,
            "minutes": fields.get("minutes", 60),
            "valid_until_time": fields.get("valid_until_time"),
            "life_days": fields.get("life_days", 0),
            "schedule_days": fields.get("schedule_days", "1234567"),
            "schedule_start": fields.get("schedule_start"),
            "schedule_end": fields.get("schedule_end"),
            "is_night": fields.get("is_night", False),
            "apply_discount": fields.get("apply_discount", True),
            "has_schedule": fields.get("has_schedule", False),
            "price": prices[0][2] if prices else 0,
            "is_active": True,
        }
        tariff, created = TariffPlan.objects.update_or_create(
            club=club, name=name, defaults=defaults,
        )
        tariff.prices.all().delete()
        for group, period, price in prices:
            TariffPrice.objects.create(tariff=tariff, group=group, period=period, price=price)
        self.stdout.write(f"  {name} [{tariff_type}] {'created' if created else 'updated'}, "
                          f"{len(prices)} prices")
