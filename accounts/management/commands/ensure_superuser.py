"""
Create Django admin superuser once from env (Render / CI), idempotent across redeploys.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_EMAIL/PASSWORD if none exist."

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.NOTICE("Superuser already exists; skipping."))
            return

        email = (os.environ.get("DJANGO_SUPERUSER_EMAIL") or "").strip().lower()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or ""
        password = password.strip() if isinstance(password, str) else ""

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set; skipping."
                )
            )
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser {email}"))
        self.stdout.flush()
