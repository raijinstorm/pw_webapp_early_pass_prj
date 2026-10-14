"""Load fictional demo data.

Users are created here (passwords need Django's hasher); everything else comes from sql/demo_data.sql.
Runs only when the database has no users yet, so it is safe to call on every container start.
The demo users' password comes from the DEMO_PASSWORD environment variable.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from app.models import User

USERS = [
    # username, first name, last name, is_admin
    ("admin", "Alex", "Admin", True),
    ("anna", "Anna", "Kowalska", False),
    ("tomasz", "Tomasz", "Nowak", False),
    ("piotr", "Piotr", "Wiśniewski", False),
    ("ewa", "Ewa", "Zielińska", False),
    ("jan", "Jan", "Lewandowski", False),
]


class Command(BaseCommand):
    help = "Load fictional demo data (only if the database has no users yet)."

    def handle(self, *args, **options):
        if User.objects.exists():
            self.stdout.write("Users already exist – skipping demo data.")
            return
        password = os.environ.get("DEMO_PASSWORD")
        if not password:
            raise CommandError("Set DEMO_PASSWORD to create the demo users.")
        with transaction.atomic():
            for username, first, last, is_admin in USERS:
                User.objects.create_user(
                    username, f"{username}@confighub.example.com", password,
                    first_name=first, last_name=last, is_superuser=is_admin, is_staff=is_admin,
                )
            with connection.cursor() as cursor:
                cursor.execute((settings.BASE_DIR / "sql" / "demo_data.sql").read_text())
        self.stdout.write(self.style.SUCCESS("Demo data created."))
