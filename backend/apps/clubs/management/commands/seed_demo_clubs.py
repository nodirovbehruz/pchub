from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clubs.models import Club, ClubMembership
from apps.computers.models import ComputerGroup


class Command(BaseCommand):
    help = "Seed demo clubs and owner membership for the admin user."

    def handle(self, *args, **options):
        User = get_user_model()

        owner, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@pchub.local", "is_superuser": True, "is_staff": True},
        )
        owner.set_password("admin123")
        owner.is_superuser = True
        owner.is_staff = True
        if hasattr(owner, "user_type"):
            owner.user_type = "admin"
        owner.save()
        if created:
            self.stdout.write(self.style.SUCCESS("Created admin/admin123"))
        else:
            self.stdout.write("admin user already exists, password reset to admin123")

        clubs = [
            dict(
                name="Мой клуб",
                country="Россия",
                city="Санкт-Петербург",
                street="Дворцовая",
                house="6-8",
                timezone="Europe/Moscow",
                contact_name="Иван",
                is_trial=True,
                trial_until=timezone.now() + timedelta(days=30),
            ),
            dict(
                name="Gaming Space",
                country="Россия",
                city="City",
                street="Street",
                house="1",
                timezone="Europe/Moscow",
                is_trial=False,
            ),
        ]

        default_groups = [
            {"name": "Main Zone", "color": "#6366f1", "position": 0},
            {"name": "VIP Lounge", "color": "#a855f7", "position": 1},
        ]

        for data in clubs:
            club, created = Club.objects.get_or_create(
                name=data["name"], defaults={**data, "owner": owner}
            )
            status = "created" if created else "exists"
            self.stdout.write(f"  Club: {club.name} [{status}]")
            ClubMembership.objects.get_or_create(
                user=owner, club=club, defaults={"role": ClubMembership.Role.OWNER}
            )
            for g in default_groups:
                grp, g_created = ComputerGroup.objects.get_or_create(
                    club=club, name=g["name"],
                    defaults={"color": g["color"], "position": g["position"]},
                )
                self.stdout.write(
                    f"    Group: {grp.name} [{'created' if g_created else 'exists'}]"
                )

        self.stdout.write(self.style.SUCCESS(
            f"Done. Owner: {owner.username} | "
            f"Clubs: {Club.objects.count()} | "
            f"Memberships: {ClubMembership.objects.count()} | "
            f"Groups: {ComputerGroup.objects.count()}"
        ))
