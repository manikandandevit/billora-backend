"""Email each Head when a client subscription ends in exactly 3 days. Run daily via cron / scheduler."""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from orgs.models import Client


class Command(BaseCommand):
    help = "Notify Heads by email when a client subscription ends in 3 days (one email per client per end date)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        target_end = today + timedelta(days=3)
        qs = Client.objects.filter(
            subscription_end=target_end,
            expiry_reminder_sent=False,
        ).select_related("head__user", "user")

        sent = 0
        for c in qs:
            head_user = c.head.user
            label = c.name.strip() if c.name else c.user.email
            body = (
                f"Billora subscription reminder\n\n"
                f"Client: {label}\n"
                f"Sign-in email: {c.user.email}\n"
                f"Plan: {c.get_subscription_type_display()}\n"
                f"Subscription ends on: {c.subscription_end.isoformat()}\n\n"
                f"This is an automated message from Billora."
            )
            try:
                send_mail(
                    subject="Billora: client subscription ending in 3 days",
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[head_user.email],
                    fail_silently=False,
                )
                c.expiry_reminder_sent = True
                c.save(update_fields=["expiry_reminder_sent"])
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"Reminder sent for client id={c.pk} ({c.user.email})"))
            except Exception as exc:  # noqa: BLE001 — log and continue other clients
                self.stderr.write(f"Failed client id={c.pk}: {exc}")

        if sent == 0:
            self.stdout.write("No reminders due today.")
