"""One-shot seed for full demo: clients, products, services, combos, games,
news, tasks, bookings, reviews. Use to populate UI for demo purposes."""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import Booking
from apps.clubs.models import Club, ClientGroup, ClubMembership, UserClubProfile
from apps.computers.models import Computer
from apps.content.models import News, Task
from apps.games.models import Game
from apps.sessions_.models import Review
from apps.shops.models import (
    Category, Combo, ComboProductItem, Product, ProductGroup, Service, Stock,
)


CLIENT_DATA = [
    ('Алексей', 'Иванов', '+79991110001', 1500, 50, 0),
    ('Мария', 'Петрова', '+79991110002', 3200, 100, 5),
    ('Дмитрий', 'Кузнецов', '+79991110003', 250, 0, 0),
    ('Анна', 'Смирнова', '+79991110004', 5800, 200, 10),
    ('Сергей', 'Попов', '+79991110005', 800, 30, 0),
    ('Елена', 'Соколова', '+79991110006', 4500, 150, 15),
    ('Иван', 'Новиков', '+79991110007', 1200, 80, 0),
    ('Ольга', 'Морозова', '+79991110008', 6700, 350, 20),
]

PRODUCT_DATA = [
    # (name, purchase_price, sale_price, category, stock)
    ('Coca-Cola 0.5', 45, 80, 'drinks', 50),
    ('Pepsi 0.5', 45, 80, 'drinks', 30),
    ('Энергетик Red Bull', 95, 180, 'drinks', 25),
    ('Чипсы Lays', 70, 130, 'snacks', 40),
    ('Сэндвич клубный', 80, 150, 'food', 15),
    ('Хот-дог', 90, 170, 'food', 20),
    ('Шоколад Snickers', 50, 90, 'snacks', 60),
    ('Сок J7 Апельсин', 60, 110, 'drinks', 18),
    ('Вода Aqua Minerale', 25, 50, 'drinks', 80),
    ('Пицца ломтик', 110, 200, 'food', 12),
]

SERVICE_DATA = [
    ('Печать A4 (ч/б)', 5),
    ('Печать A4 (цветная)', 15),
    ('Скан документа', 10),
    ('Запись на USB', 20),
]

GAME_DATA = [
    ('Counter-Strike 2', 'steam', 'steam://rungameid/730'),
    ('Dota 2', 'steam', 'steam://rungameid/570'),
    ('Valorant', 'riot', 'C:\\Riot\\RiotClientServices.exe'),
    ('League of Legends', 'riot', 'C:\\Riot\\RiotClientServices.exe'),
    ('Fortnite', 'epic', 'com.epicgames.launcher://apps/fortnite'),
    ('GTA V', 'steam', 'steam://rungameid/271590'),
    ('Apex Legends', 'ea', 'C:\\EA\\Apex.exe'),
    ('PUBG Battlegrounds', 'steam', 'steam://rungameid/578080'),
]

NEWS_DATA = [
    ('Открытие нового зала!',
     'У нас появилась новая VIP-зона с топовым железом — i9 13900K и RTX 4090. Заходи попробовать!'),
    ('Турнир по Counter-Strike 2',
     'В эту субботу проводим турнир 5×5 с призовым фондом 50 000 сум. Регистрация на стойке.'),
    ('Скидка 30% на ночные часы',
     'С понедельника по четверг с 22:00 до 08:00 действует скидка 30% на все тарифы.'),
]

TASK_DATA = [
    ('Заказать колу и снеки', 'Заканчиваются Pepsi и Snickers — позвонить поставщику'),
    ('Проверить ПК-15', 'Клиент жалуется на странные звуки — посмотреть кулер'),
    ('Обновить Valorant', 'На всех ПК VIP-зала'),
    ('Подсчитать наличку', 'Перед закрытием смены'),
]

REVIEW_DATA = [
    (5, 'Отличный клуб, всё работает идеально. Спасибо!'),
    (4, 'Хорошо, но иногда лагает мышь на ПК-7'),
    (5, 'Лучший клуб в городе! Куча игр, быстрые ПК'),
    (3, 'Скучаю по своему любимому ПК — занят постоянно :('),
    (5, 'Удобно платить через Kaspi QR'),
]


class Command(BaseCommand):
    help = "Seed full demo dataset for a club: clients, products, services, games, news, tasks, etc."

    def add_arguments(self, parser):
        parser.add_argument('--club', type=str, default='Мой клуб',
                            help='Club name to seed into')
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing demo data first')

    def handle(self, *args, **options):
        User = get_user_model()
        club_name = options['club']
        try:
            club = Club.objects.get(name=club_name)
        except Club.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Club '{club_name}' not found. Run seed_demo_clubs first."))
            return

        # -- Clients (UserClubProfile)
        clients = []
        for fn, ln, phone, dep, bonus, disc in CLIENT_DATA:
            user, created = User.objects.get_or_create(
                username=phone,
                defaults={'first_name': fn, 'last_name': ln, 'phone': phone},
            )
            if created:
                user.set_password('client123')
                user.save()
            profile, _ = UserClubProfile.objects.get_or_create(user=user, club=club)
            profile.deposit_money = Decimal(str(dep))
            profile.bonus_balance = Decimal(str(bonus))
            profile.personal_discount = disc
            profile.last_visit_at = timezone.now() - timedelta(days=random.randint(0, 14))
            profile.save()
            clients.append(user)
        self.stdout.write(f"  Clients: {len(clients)}")

        # -- Client groups
        cg_regulars, _ = ClientGroup.objects.get_or_create(
            club=club, name='Постоянные', defaults={'percent_discount': 5},
        )
        cg_vip, _ = ClientGroup.objects.get_or_create(
            club=club, name='VIP', defaults={'percent_discount': 15},
        )
        # Assign some to VIP/regulars
        if len(clients) >= 4:
            UserClubProfile.objects.filter(user=clients[3], club=club).update(group=cg_vip)
            UserClubProfile.objects.filter(user=clients[7] if len(clients) > 7 else clients[3], club=club).update(group=cg_vip)
            UserClubProfile.objects.filter(user=clients[0], club=club).update(group=cg_regulars)
            UserClubProfile.objects.filter(user=clients[5], club=club).update(group=cg_regulars)
        self.stdout.write("  ClientGroups: Постоянные, VIP")

        # -- Product groups & categories
        cat_drinks, _ = Category.objects.get_or_create(slug='drinks', defaults={'name': 'Напитки'})
        cat_snacks, _ = Category.objects.get_or_create(slug='snacks', defaults={'name': 'Снеки'})
        cat_food, _ = Category.objects.get_or_create(slug='food', defaults={'name': 'Еда'})
        cat_map = {'drinks': cat_drinks, 'snacks': cat_snacks, 'food': cat_food}

        pg_drinks, _ = ProductGroup.objects.get_or_create(club=club, name='Напитки')
        pg_food, _ = ProductGroup.objects.get_or_create(club=club, name='Еда и снеки')
        pg_map = {'drinks': pg_drinks, 'snacks': pg_food, 'food': pg_food}

        # -- Products
        products = []
        for name, pp, sp, cat, stock in PRODUCT_DATA:
            from django.utils.text import slugify
            p, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'slug': slugify(name + '-' + str(random.randint(100, 999))),
                    'category': cat_map[cat],
                    'club': club,
                    'product_group': pg_map[cat],
                    'price': Decimal(str(sp)),
                    'purchase_price': Decimal(str(pp)),
                    'is_active': True,
                    'shell_display': True,
                },
            )
            Stock.objects.update_or_create(product=p, defaults={'quantity': stock})
            products.append(p)
        self.stdout.write(f"  Products: {len(products)}")

        # -- Services
        services = []
        for name, price in SERVICE_DATA:
            s, _ = Service.objects.get_or_create(
                club=club, name=name, defaults={'price': Decimal(str(price))},
            )
            services.append(s)
        self.stdout.write(f"  Services: {len(services)}")

        # -- Combos
        if len(products) >= 2:
            combo, created = Combo.objects.get_or_create(
                club=club, name='Игровой набор',
                defaults={'sale_price': Decimal('250'), 'base_price': Decimal('290'), 'is_active': True},
            )
            if created:
                ComboProductItem.objects.create(combo=combo, product=products[0], qty=1)
                ComboProductItem.objects.create(combo=combo, product=products[3], qty=1)
            self.stdout.write("  Combos: 1 (Игровой набор)")

        # -- Games
        for name, platform, path in GAME_DATA:
            from django.utils.text import slugify
            Game.objects.get_or_create(
                name=name,
                defaults={
                    'slug': slugify(name),
                    'executable_path': path,
                    'is_active': True,
                },
            )
        self.stdout.write(f"  Games: {len(GAME_DATA)}")

        # -- News
        for title, body in NEWS_DATA:
            News.objects.get_or_create(
                club=club, title=title,
                defaults={'body': body, 'is_published': True},
            )
        self.stdout.write(f"  News: {len(NEWS_DATA)}")

        # -- Tasks
        for title, body in TASK_DATA:
            Task.objects.get_or_create(
                club=club, title=title,
                defaults={'body': body, 'is_finished': False},
            )
        self.stdout.write(f"  Tasks: {len(TASK_DATA)}")

        # -- Bookings (1-2 active for upcoming hours)
        pcs = list(Computer.objects.filter(club=club)[:4])
        if pcs:
            now = timezone.now()
            b1, created = Booking.objects.get_or_create(
                club=club, guest_name='Иван (друг)',
                defaults={
                    'guest_phone': '+79991234567',
                    'from_at': now + timedelta(hours=2),
                    'to_at': now + timedelta(hours=5),
                    'comment': 'День рождения',
                    'status': 'active',
                },
            )
            if created:
                b1.hosts.set(pcs[:2])
            if len(clients) > 0:
                b2, c2 = Booking.objects.get_or_create(
                    club=club, client=clients[0],
                    defaults={
                        'from_at': now + timedelta(hours=8),
                        'to_at': now + timedelta(hours=12),
                        'status': 'active',
                    },
                )
                if c2:
                    b2.hosts.set(pcs[2:4] if len(pcs) >= 4 else pcs[2:])
            self.stdout.write("  Bookings: up to 2")

        # -- Reviews (random ratings & comments)
        for i, (rating, comment) in enumerate(REVIEW_DATA):
            if i >= len(clients) or not pcs:
                break
            Review.objects.get_or_create(
                club=club, client=clients[i], computer=pcs[i % len(pcs)],
                defaults={
                    'rating': rating, 'comment': comment,
                    'tip_amount': Decimal('50') if rating == 5 and i % 2 == 0 else Decimal('0'),
                },
            )
        self.stdout.write(f"  Reviews: {Review.objects.filter(club=club).count()}")

        # -- Employees: ensure admin user is a member with owner role
        ClubMembership.objects.get_or_create(
            user__username='admin', club=club,
            defaults={'user': User.objects.get(username='admin'), 'role': 'owner'},
        )

        # -- Sample staff
        staff_data = [
            ('+79993330001', 'Анна', 'Менеджерова', 'manager'),
            ('+79993330002', 'Виктор', 'Операторов', 'operator'),
        ]
        for phone, fn, ln, role in staff_data:
            u, _ = User.objects.get_or_create(
                username=phone,
                defaults={'first_name': fn, 'last_name': ln, 'phone': phone, 'is_staff': True},
            )
            ClubMembership.objects.get_or_create(
                user=u, club=club, defaults={'role': role},
            )
        self.stdout.write(f"  Employees: +{len(staff_data)} staff")

        self.stdout.write(self.style.SUCCESS(f"\nDemo seed for «{club.name}» completed."))
