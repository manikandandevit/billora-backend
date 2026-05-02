"""Subscription length from a calendar start date (signup or Head renewal) + plan days."""

from datetime import date, datetime, timedelta

from django.utils import timezone as django_tz

# demo: 7 days from created, then account is deactivated (see login + management command).
SUBSCRIPTION_DAYS = {
    "demo": 7,
    "monthly": 30,
    "yearly": 365,
}


def subscription_end_for(created_at: datetime | date, subscription_type: str) -> date:
    # datetime is a subclass of date — check datetime first.
    if isinstance(created_at, datetime):
        # Use calendar date in Django's TIME_ZONE so "today" matches the business region.
        base = (
            django_tz.localtime(created_at).date()
            if django_tz.is_aware(created_at)
            else created_at.date()
        )
    else:
        base = created_at
    days = SUBSCRIPTION_DAYS.get(subscription_type, 30)
    return base + timedelta(days=days)
