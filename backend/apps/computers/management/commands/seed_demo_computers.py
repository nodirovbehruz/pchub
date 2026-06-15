from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.clubs.models import Club
from apps.computers.models import Computer, ComputerGroup
from apps.computers.models.enums import ComputerStatus


SPEC_PRESETS = [
    {"cpu": "Intel Core i5-12400F", "ram": 16, "gpu": "RTX 3060 12GB"},
    {"cpu": "Intel Core i7-13700K", "ram": 32, "gpu": "RTX 4070 12GB"},
    {"cpu": "AMD Ryzen 5 7600X", "ram": 16, "gpu": "RTX 3070 8GB"},
    {"cpu": "AMD Ryzen 7 7800X3D", "ram": 32, "gpu": "RTX 4080 16GB"},
]


class Command(BaseCommand):
    help = "Seed demo computers distributed across club groups."

    def add_arguments(self, parser):
        parser.add_argument("--club", type=str, default="Мой клуб",
                            help="Club name to seed PCs into")

    def handle(self, *args, **options):
        club_name = options["club"]
        try:
            club = Club.objects.get(name=club_name)
        except Club.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Club '{club_name}' not found. Run seed_demo_clubs first."))
            return

        main_zone = ComputerGroup.objects.filter(club=club, name="Main Zone").first()
        vip_lounge = ComputerGroup.objects.filter(club=club, name="VIP Lounge").first()
        if not main_zone or not vip_lounge:
            self.stdout.write(self.style.ERROR("Expected groups Main Zone / VIP Lounge — run seed_demo_clubs first."))
            return

        # 10 PCs: 6 in Main Zone, 4 in VIP Lounge
        layout = [
            # (number, group, status)
            (1, main_zone,   ComputerStatus.ONLINE),
            (2, main_zone,   ComputerStatus.OFFLINE),
            (3, main_zone,   ComputerStatus.OFFLINE),
            (4, main_zone,   ComputerStatus.OFFLINE),
            (5, main_zone,   ComputerStatus.MAINTENANCE),
            (6, main_zone,   ComputerStatus.OFFLINE),
            (7, vip_lounge,  ComputerStatus.ONLINE),
            (8, vip_lounge,  ComputerStatus.OFFLINE),
            (9, vip_lounge,  ComputerStatus.OFFLINE),
            (10, vip_lounge, ComputerStatus.OFFLINE),
        ]

        created = 0
        updated = 0
        for idx, (number, group, status) in enumerate(layout):
            spec = SPEC_PRESETS[idx % len(SPEC_PRESETS)]
            name = f"PC-{number:02d}"
            defaults = {
                "slug": slugify(name),
                "pc_number": number,
                "group": group,
                "status": status,
                "is_active": True,
                "cpu_model": spec["cpu"],
                "ram_total_gb": spec["ram"],
                "gpu_model": spec["gpu"],
                "storage_total_gb": 1000,
                "os_name": "Windows 11 Pro",
                "ip_address": f"192.168.1.{100 + number}",
                "position_x": (idx % 6) * 100,
                "position_y": (idx // 6) * 100,
            }
            pc, was_created = Computer.objects.get_or_create(
                name=name, defaults=defaults,
            )
            if not was_created:
                pc.group = group
                pc.status = status
                pc.cpu_model = spec["cpu"]
                pc.ram_total_gb = spec["ram"]
                pc.gpu_model = spec["gpu"]
                pc.save(update_fields=["group", "status", "cpu_model", "ram_total_gb", "gpu_model"])
                updated += 1
            else:
                created += 1
            self.stdout.write(f"  {name} | {group.name} | {status}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created} | Updated: {updated} | Total: {Computer.objects.count()}"
        ))
