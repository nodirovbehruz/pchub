"""Management command: open a test shift and backfill Computer.club FK.

Usage:
    python manage.py seed_open_shift
    python manage.py seed_open_shift --admin admin --cash 5000

This command:
1. Ensures all Computers have club FK set (backfill from group.club).
2. Opens an active shift for the first superuser / given username.
3. Prints a summary of the state.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Open a test shift + backfill Computer.club FK"

    def add_arguments(self, parser):
        parser.add_argument("--admin", default=None, help="Admin username (default: first superuser)")
        parser.add_argument("--cash", type=float, default=1000.0, help="Initial cash in register")
        parser.add_argument("--close-existing", action="store_true", help="Close any existing active shift first")

    def handle(self, *args, **options):
        from apps.accounts.models import CustomUser
        from apps.billing.models import Shift
        from apps.computers.models import Computer

        # ── 1. Backfill Computer.club from group.club ──────────────────────────
        self.stdout.write("Backfilling Computer.club FK…")
        updated = 0
        for pc in Computer.objects.select_related("group__club").filter(club__isnull=True):
            if pc.group and pc.group.club_id:
                pc.club_id = pc.group.club_id
                pc.save(update_fields=["club"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"  → Updated {updated} computers"))

        # ── 2. Find admin user ─────────────────────────────────────────────────
        username = options["admin"]
        if username:
            try:
                admin = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                raise CommandError(f"User '{username}' not found")
        else:
            admin = (
                CustomUser.objects.filter(is_superuser=True).first()
                or CustomUser.objects.filter(is_staff=True).first()
                or CustomUser.objects.first()
            )
        if not admin:
            raise CommandError("No users found in the database. Run migrations and create a superuser first.")
        self.stdout.write(f"Using admin: {admin.username}")

        # ── 3. Handle existing shift ───────────────────────────────────────────
        existing = Shift.get_active_shift()
        if existing:
            if options["close_existing"]:
                existing.is_active = False
                existing.end_time = timezone.now()
                existing.save(update_fields=["is_active", "end_time"])
                self.stdout.write(self.style.WARNING(f"  → Closed existing shift #{existing.id}"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"  → Shift already open (#{existing.id}, admin={existing.admin.username}). "
                    "Use --close-existing to close it first."
                ))
                self._print_summary()
                return

        # ── 4. Open new shift ──────────────────────────────────────────────────
        shift = Shift.objects.create(
            admin=admin,
            initial_cash=options["cash"],
            start_time=timezone.now(),
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f"  → Opened shift #{shift.id} for {admin.username} "
            f"with {options['cash']} сум initial cash"
        ))

        self._print_summary()

    def _print_summary(self):
        from apps.clubs.models import Club
        from apps.computers.models import Computer
        from apps.billing.models import Shift

        self.stdout.write("\n── Current state ──────────────────────")
        for club in Club.objects.all():
            pcs = Computer.objects.filter(club=club, is_active=True)
            self.stdout.write(
                f"  Club #{club.id}: {club.name} — {pcs.count()} computers"
                f" ({pcs.filter(status='ONLINE').count()} online)"
            )

        shift = Shift.get_active_shift()
        if shift:
            self.stdout.write(self.style.SUCCESS(
                f"  Active shift: #{shift.id} by {shift.admin.username} "
                f"since {shift.start_time:%H:%M}"
            ))
        else:
            self.stdout.write(self.style.WARNING("  No active shift"))
        self.stdout.write("────────────────────────────────────────\n")
        self.stdout.write(self.style.SUCCESS("Done! Now start the server and open the frontend."))
