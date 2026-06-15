from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.clubs.models import Club
from apps.loyalty.models import (
    Achievement,
    AchievementTrigger,
    CashbackRule,
    Discount,
    Promocode,
    PromocodeRewardType,
    RewardType,
)


class Command(BaseCommand):
    help = "Seed demo loyalty data (discounts, promocodes, cashback, achievements)."

    def add_arguments(self, parser):
        parser.add_argument("--club", type=str, default="Мой клуб")

    def handle(self, *args, **options):
        try:
            club = Club.objects.get(name=options["club"])
        except Club.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Club '{options['club']}' not found"))
            return

        Discount.objects.update_or_create(
            club=club, name="Открытие клуба",
            defaults={"percent": 50, "schedule_days": "1234567"},
        )
        Discount.objects.update_or_create(
            club=club, name="Пятница",
            defaults={"percent": 10, "schedule_days": "5"},
        )
        self.stdout.write("  Discounts: 2")

        Promocode.objects.update_or_create(
            code="WELCOME2026", defaults={
                "club": club, "name": "Приветственный",
                "reward_type": PromocodeRewardType.DEPOSIT_TOPUP,
                "value": Decimal("100"),
                "usage_limit": 100,
                "channels": ["admin", "mobile", "shell"],
            },
        )
        Promocode.objects.update_or_create(
            code="NIGHT20", defaults={
                "club": club, "name": "Ночная скидка 20%",
                "reward_type": PromocodeRewardType.DISCOUNT,
                "value": Decimal("20"),
                "applies_to_tariffs": True, "applies_to_products": False,
                "applies_to_services": False, "applies_to_combos": False,
                "channels": ["admin"],
            },
        )
        self.stdout.write("  Promocodes: 2")

        CashbackRule.objects.update_or_create(
            club=club, deposit_threshold=Decimal("500"),
            defaults={"name": "5% от 500сум", "value": Decimal("5")},
        )
        CashbackRule.objects.update_or_create(
            club=club, deposit_threshold=Decimal("2000"),
            defaults={"name": "10% от 2000сум", "value": Decimal("10")},
        )
        self.stdout.write("  Cashback rules: 2")

        Achievement.objects.update_or_create(
            club=club, name="Новичок",
            defaults={
                "trigger_type": AchievementTrigger.REGISTRATION,
                "threshold": Decimal("0"),
                "reward_type": RewardType.BONUS,
                "reward_value": Decimal("50"),
                "description": "За регистрацию в клубе",
            },
        )
        Achievement.objects.update_or_create(
            club=club, name="VIP",
            defaults={
                "trigger_type": AchievementTrigger.SPEND_TOTAL,
                "threshold": Decimal("10000"),
                "reward_type": RewardType.DISCOUNT,
                "reward_value": Decimal("10"),
                "description": "Постоянный клиент — потратил >10 000сум",
            },
        )
        self.stdout.write("  Achievements: 2")

        self.stdout.write(self.style.SUCCESS("Done."))
