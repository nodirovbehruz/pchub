"""
python manage.py seed_rich_data --club 4

Fills Gaming Space (or any club) with rich realistic demo data:
 - 12 computers in 3 zones
 - 10 clients with deposits & balances
 - 4 tariff plans
 - 20 payments (mix of cash/card)
 - open shift with revenue
 - bookings, reviews, sessions
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
import random, datetime

User = get_user_model()


class Command(BaseCommand):
    help = "Seed rich demo data for a specific club"

    def add_arguments(self, parser):
        parser.add_argument("--club", type=int, default=4, help="Club ID (default 4 = Gaming Space)")

    def handle(self, *args, **options):
        club_id = options["club"]

        from apps.clubs.models import Club, ClubMembership, UserClubProfile, ClientGroup
        from apps.computers.models import Computer, ComputerGroup
        from apps.billing.models import TariffPlan, TariffPrice, Payment, PaymentMethod, Shift, UserBalance
        from apps.sessions_.models import ClientSession, Review
        from apps.bookings.models import Booking

        try:
            club = Club.objects.get(pk=club_id)
        except Club.DoesNotExist:
            self.stderr.write(f"Club {club_id} not found!")
            return

        self.stdout.write(f"Seeding rich data for: {club.name} (id={club.id})")

        # ── 1. Computer groups ──────────────────────────────────────────────
        zone_defs = [
            ("VIP-зона", "#7c3aed"),
            ("Стандарт", "#2563eb"),
            ("Киберспорт", "#dc2626"),
        ]
        zones = []
        for zname, zcolor in zone_defs:
            zone, _ = ComputerGroup.objects.get_or_create(
                club=club, name=zname,
                defaults={"color": zcolor, "position": len(zones)},
            )
            zones.append(zone)
        self.stdout.write(f"  Zones: {[z.name for z in zones]}")

        # ── 2. Computers ──────────────────────────────────────────────────
        pc_configs = [
            # (alias, zone_idx, pos_x, pos_y, cpu, ram, gpu)
            ("VIP-1", 0, 50,  50,  "Intel i9-13900K", 64, "RTX 4090"),
            ("VIP-2", 0, 160, 50,  "Intel i9-13900K", 64, "RTX 4090"),
            ("VIP-3", 0, 270, 50,  "Intel i9-13900K", 32, "RTX 4080"),
            ("PC-01", 1, 50,  50,  "Intel i5-12400F", 16, "RTX 3060"),
            ("PC-02", 1, 160, 50,  "Intel i5-12400F", 16, "RTX 3060"),
            ("PC-03", 1, 270, 50,  "Intel i5-12400F", 16, "RTX 3060"),
            ("PC-04", 1, 380, 50,  "AMD Ryzen 5 5600", 16, "RTX 3060 Ti"),
            ("PC-05", 1, 50,  160, "AMD Ryzen 5 5600", 16, "RTX 3060 Ti"),
            ("PC-06", 1, 160, 160, "Intel i5-12400F", 32, "RTX 3070"),
            ("CS-01", 2, 50,  50,  "Intel i7-13700K", 32, "RTX 3080"),
            ("CS-02", 2, 160, 50,  "Intel i7-13700K", 32, "RTX 3080"),
            ("CS-03", 2, 270, 50,  "Intel i7-13700K", 32, "RTX 4070"),
        ]
        computers = []
        statuses = ["ONLINE", "ONLINE", "ONLINE", "OFFLINE", "OFFLINE", "ONLINE", "ONLINE", "ONLINE", "OFFLINE", "ONLINE", "ONLINE", "OFFLINE"]
        for i, (pc_name, zone_idx, px, py, cpu, ram, gpu) in enumerate(pc_configs):
            unique_name = f"c{club_id}-{pc_name}"
            unique_slug = f"club{club_id}-{pc_name.lower().replace(' ', '-')}"
            unique_hwid = f"HW-{club_id}-{i+1:03d}"
            pc, created = Computer.objects.get_or_create(
                name=unique_name,
                defaults={
                    "slug": unique_slug,
                    "club": club,
                    "group": zones[zone_idx],
                    "position_x": px,
                    "position_y": py,
                    "cpu_model": cpu,
                    "ram_total_gb": ram,
                    "gpu_model": gpu,
                    "pc_number": i + 1,
                    "status": statuses[i],
                    "is_active": True,
                    "ip_address": f"192.168.1.{10 + i}",
                    "hardware_id": unique_hwid,
                },
            )
            if not created:
                Computer.objects.filter(pk=pc.pk).update(
                    group=zones[zone_idx], position_x=px, position_y=py, status=statuses[i]
                )
            computers.append(pc)
        self.stdout.write(f"  Computers: {len(computers)}")

        # ── 3. Clients with profiles ─────────────────────────────────────
        client_data = [
            ("artem_k",    "Артём",    "Козлов",    "+79001112233", 2500, 150),
            ("maria_s",    "Мария",    "Смирнова",  "+79002223344", 5000, 300),
            ("dima_v",     "Дмитрий",  "Волков",    "+79003334455", 1200, 50),
            ("olga_p",     "Ольга",    "Петрова",   "+79004445566", 8000, 500),
            ("ivan_m",     "Иван",     "Морозов",   "+79005556677", 300,  0),
            ("sasha_t",    "Александр","Тихонов",   "+79006667788", 4500, 200),
            ("nastya_b",   "Анастасия","Белова",    "+79007778899", 1800, 80),
            ("vlad_n",     "Владислав","Никитин",   "+79008889900", 6200, 420),
            ("kate_z",     "Екатерина","Захарова",  "+79009990011", 900,  0),
            ("maks_g",     "Максим",   "Григорьев", "+79001230123", 3300, 110),
        ]
        clients = []
        for uname, first, last, phone, deposit, bonus in client_data:
            u, _ = User.objects.get_or_create(
                username=uname,
                defaults={
                    "first_name": first, "last_name": last,
                    "phone": phone,
                    "password": "demo_password",
                },
            )
            if _:
                u.set_password("demo123")
                u.save()
            # Club membership
            ClubMembership.objects.get_or_create(user=u, club=club)
            # Club profile with deposit
            prof, created = UserClubProfile.objects.get_or_create(
                user=u, club=club,
                defaults={"deposit_money": Decimal(deposit), "bonus_balance": Decimal(bonus)},
            )
            if not created:
                prof.deposit_money = Decimal(deposit)
                prof.bonus_balance = Decimal(bonus)
                prof.save()
            clients.append(u)
        self.stdout.write(f"  Clients: {len(clients)}")

        # ── 4. Tariff plans ──────────────────────────────────────────────
        tariff_defs = [
            ("Стандарт 1 руб/мин",  "per_minute",  60),
            ("VIP 1.5 руб/мин",     "per_minute",  90),
            ("Ночной 0.7 руб/мин",  "per_minute",  40),
            ("Пакет 3 часа",         "fixed",       290),
            ("Пакет Ночь",           "package",     190),
            ("Абонемент месяц",      "subscription", 2990),
        ]
        for tname, ttype, price in tariff_defs:
            TariffPlan.objects.get_or_create(
                club=club, name=tname,
                defaults={
                    "tariff_type": ttype,
                    "price": Decimal(price),
                    "is_active": True,
                },
            )
        self.stdout.write(f"  Tariffs: {TariffPlan.objects.filter(club=club).count()}")

        # ── 5. Open shift (if none active) ───────────────────────────────
        admin_user = User.objects.filter(is_staff=True).first()
        shift = Shift.objects.filter(is_active=True).first()
        if not shift:
            shift = Shift.objects.create(
                admin=admin_user,
                initial_cash=Decimal("500"),
                is_active=True,
            )
        self.stdout.write(f"  Shift: #{shift.id} (active={shift.is_active})")

        # ── 6. Payments ───────────────────────────────────────────────────
        methods = [PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.CASH]
        amounts = [290, 180, 90, 540, 270, 90, 180, 360, 120, 290, 450, 60, 90, 180, 270, 360, 90, 180, 540, 90]
        now = timezone.now()
        pay_count = 0
        for i, (amount, client) in enumerate(zip(amounts, clients * 3)):
            delta = datetime.timedelta(hours=i * 0.4)
            Payment.objects.get_or_create(
                user=client,
                admin=admin_user,
                amount_paid=Decimal(amount),
                defaults={
                    "minutes_added": amount // 2,
                    "payment_method": methods[i % len(methods)],
                    "note": f"Автоматический платёж #{i+1}",
                },
            )
            pay_count += 1
        self.stdout.write(f"  Payments added: {pay_count}")

        # ── 7. Bookings ───────────────────────────────────────────────────
        booking_data = [
            (clients[0], computers[0], 1, 3),
            (clients[1], computers[1], 2, 4),
            (clients[3], computers[9], 0, 2),
            (clients[5], computers[3], 3, 5),
        ]
        for client, pc, h_from, h_to in booking_data:
            from_dt = now + datetime.timedelta(hours=h_from)
            to_dt = now + datetime.timedelta(hours=h_to)
            Booking.objects.get_or_create(
                club=club, client=client,
                from_at=from_dt.replace(second=0, microsecond=0),
                defaults={
                    "to_at": to_dt.replace(second=0, microsecond=0),
                    "status": "confirmed",
                    "created_by": admin_user,
                },
            )
        self.stdout.write(f"  Bookings: {Booking.objects.filter(club=club).count()}")

        # ── 8. Reviews ────────────────────────────────────────────────────
        review_texts = [
            "Отличный клуб! Быстрые ПК, приятная атмосфера. Буду приходить чаще.",
            "VIP-зона топ, мониторы 240Гц — кайф. Персонал вежливый.",
            "Хорошее место, но бывает шумновато. В целом доволен.",
            "Регулярно хожу сюда на ночные смены. Цены адекватные.",
            "Очень понравилось! Быстрый интернет, чистые рабочие места.",
        ]
        for i, (client, text) in enumerate(zip(clients[:5], review_texts)):
            Review.objects.get_or_create(
                club=club, client=client,
                defaults={
                    "rating": random.choice([4, 5, 5, 5]),
                    "comment": text,
                },
            )
        self.stdout.write(f"  Reviews: {Review.objects.filter(club=club).count()}")

        self.stdout.write(self.style.SUCCESS(f"\n✅  Rich data seeded for «{club.name}»!"))
        self.stdout.write("   Refresh http://localhost:5173 — all pages should show live data.")
