from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone as django_timezone
from django.utils.text import slugify

from .subscription_utils import subscription_end_for


class Head(models.Model):
    """Single Billora company owner: login + logo. Full access (no subscription window)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="head_profile",
    )
    company_logo = models.ImageField(
        upload_to="company_logos/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["png", "jpg", "jpeg", "webp"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        if self.user_id:
            return f"Head({self.user.email})"
        return "Head (unsaved)"


class SubscriptionType(models.TextChoices):
    DEMO = "demo", "Demo"
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class Client(models.Model):
    """End-user under a Head; authenticates with own email/password."""

    head = models.ForeignKey(Head, on_delete=models.CASCADE, related_name="clients")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_profile",
    )
    name = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    subscription_type = models.CharField(
        max_length=32,
        choices=SubscriptionType.choices,
        default=SubscriptionType.MONTHLY,
    )
    subscription_end = models.DateField(null=True, blank=True)
    subscription_period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start of current billed window; set when Head changes plan so end = this + plan days. If null, signup date (created_at) is used.",
    )
    expiry_reminder_sent = models.BooleanField(
        default=False,
        help_text="Set when the 3-days-before email was sent for the current subscription_end.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Client({self.user.email} @ {self.head})"

    def sync_subscription_end(self) -> None:
        """End date = period start date + plan length (7 / 30 / 365)."""
        if self.subscription_period_start is not None:
            base = self.subscription_period_start
        else:
            if not self.created_at:
                return
            created = self.created_at
            if django_timezone.is_aware(created):
                base = django_timezone.localtime(created).date()
            else:
                base = created.date()
        end = subscription_end_for(base, self.subscription_type)
        if self.subscription_end != end:
            Client.objects.filter(pk=self.pk).update(subscription_end=end)
            self.subscription_end = end

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_subscription_end()


class Branch(models.Model):
    """Outlet / hotel login: separate credentials from Head; opens SalesPoints dashboard by slug URL."""

    head = models.ForeignKey(Head, on_delete=models.CASCADE, related_name="branches")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="branch_profile",
    )
    hotel_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    address = models.TextField(blank=True, default="")
    salespoints_slug = models.SlugField(
        max_length=96,
        unique=True,
        help_text='URL path fragment, typically "{hotel}-salespoints".',
    )
    paused_by_head = models.BooleanField(
        default=False,
        help_text="When True, do not auto-activate outlet login after subscription renews.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Branch({self.hotel_name} @ {self.head})"

    @classmethod
    def allocate_salespoints_slug(cls, hotel_name: str, exclude_pk: int | None = None) -> str:
        base = (slugify(hotel_name)[:48] or "").strip() or "outlet"
        candidate = f"{base}-salespoints"
        qs = cls.objects.all()
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.filter(salespoints_slug=candidate).exists():
            return candidate
        n = 2
        while qs.filter(salespoints_slug=f"{candidate}-{n}").exists():
            n += 1
        return f"{candidate}-{n}"
