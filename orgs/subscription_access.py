"""Gates dashboard client + outlet branch logins by subscription calendar (demo / monthly / yearly)."""

from django.utils import timezone

from .models import Branch, Client


def _today():
    return timezone.localdate()


def sync_and_refresh_end(client: Client):
    client.sync_subscription_end()
    client.refresh_from_db(fields=("subscription_end",))
    return client.subscription_end


def organization_subscription_calendar_open(head_id: int, today=None) -> bool:
    """
    True if at least one Client under this Head has subscription_end covering `today`.
    Dates come from subscription_period_start (or signup) + plan length after sync_subscription_end().
    """
    today = today or _today()
    qs = Client.objects.filter(head_id=head_id)
    if not qs.exists():
        return False
    for c in qs.iterator(chunk_size=100):
        end = sync_and_refresh_end(c)
        if end is not None and today <= end:
            return True
    return False


def client_subscription_expired(client: Client, today=None) -> bool:
    today = today or _today()
    end = sync_and_refresh_end(client)
    return end is not None and today > end


def deactivate_all_branch_users(head_id: int) -> None:
    for br in Branch.objects.filter(head_id=head_id).select_related("user"):
        u = br.user
        if u.is_active:
            u.is_active = False
            u.save(update_fields=["is_active"])


def deactivate_all_client_users(head_id: int) -> None:
    for c in Client.objects.filter(head_id=head_id).select_related("user"):
        u = c.user
        if u.is_active:
            u.is_active = False
            u.save(update_fields=["is_active"])


def freeze_organization_if_calendar_closed(head_id: int, today=None) -> None:
    """If no Client still inside subscription window for this Head, lock all Client + Branch accounts."""
    today = today or _today()
    if organization_subscription_calendar_open(head_id, today):
        return
    deactivate_all_branch_users(head_id)
    deactivate_all_client_users(head_id)


def reopen_branches_under_head(head_id: int) -> None:
    """Re-open branches only outlets the Head did not explicitly pause."""
    qs = Branch.objects.filter(head_id=head_id, paused_by_head=False).select_related("user")
    for br in qs:
        u = br.user
        if not u.is_active:
            u.is_active = True
            u.save(update_fields=["is_active"])


def reconcile_client_activation_for_calendar(client: Client, today=None) -> None:
    """Set this Client user's is_active according to subscription window (used when org opens)."""
    today = today or _today()
    end = sync_and_refresh_end(client)
    u = client.user
    if end is not None and today <= end:
        if not u.is_active:
            u.is_active = True
            u.save(update_fields=["is_active"])
    elif u.is_active:
        u.is_active = False
        u.save(update_fields=["is_active"])


def subscription_denial_reason_for_user(user, today=None) -> str | None:
    """
    Non-empty → session must stop (JWT access, JWT refresh): subscription / deactivated / unlinked.
    Side effects match LoginView where applicable (freeze org, deactivate expired client users).
    """
    if user.is_staff or user.is_superuser:
        return None
    head = getattr(user, "head_profile", None)
    if head is not None:
        return None
    if not user.is_active:
        return (
            "This account has been deactivated. "
            "Contact your company Head if you need access again."
        )

    today = today or _today()
    branch = getattr(user, "branch_profile", None)
    client = getattr(user, "client_profile", None)

    if branch:
        if not organization_subscription_calendar_open(branch.head_id, today):
            freeze_organization_if_calendar_closed(branch.head_id, today)
            return (
                "Subscription ended for this company. "
                "Branch logins stay off until your Head renews the client subscription."
            )
        return None

    if client:
        if client_subscription_expired(client, today):
            user.is_active = False
            user.save(update_fields=["is_active"])
            freeze_organization_if_calendar_closed(client.head_id, today)
            return (
                "Your subscription has ended (demo / monthly / yearly window). "
                "Ask your company Head to renew the plan — client and outlet logins reopen when "
                "the subscription is valid again."
            )
        return None

    return (
        "This account is not linked to a Billora Head, Branch, or Client. "
        "Ask your administrator to provision access."
    )


def apply_org_subscription_state(head_id: int) -> None:
    """
    Align branch + client activations with calendar (called after subscription changes via API or cron).
    """
    today = _today()
    if organization_subscription_calendar_open(head_id, today):
        reopen_branches_under_head(head_id)
        for c in Client.objects.filter(head_id=head_id):
            reconcile_client_activation_for_calendar(c, today)
    else:
        deactivate_all_branch_users(head_id)
        deactivate_all_client_users(head_id)
