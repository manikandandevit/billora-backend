"""Reconcile subscription access per Head (demo/monthly/yearly). Run daily with cron."""

from django.core.management.base import BaseCommand

from orgs.models import Head
from orgs.subscription_access import apply_org_subscription_state


class Command(BaseCommand):
    help = (
        "Deactivate Client + Branch users whose Head has no subscription window left; "
        "reactivate when any client subscription_end covers today."
    )

    def handle(self, *args, **options):
        n = 0
        for h in Head.objects.all():
            apply_org_subscription_state(h.pk)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Reconciled subscription access for {n} head(s)."))
