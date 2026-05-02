from django.db import migrations


def seed_demo_head(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Head = apps.get_model("orgs", "Head")
    u = User.objects.filter(email__iexact="demo@company.com").first()
    if u and not Head.objects.filter(user=u).exists():
        Head.objects.create(
            user=u,
            subscription_type="demo",
            expiry_notification_sent=False,
        )


def noop_reverse(apps, schema_editor):
    Head = apps.get_model("orgs", "Head")
    User = apps.get_model("accounts", "User")
    u = User.objects.filter(email__iexact="demo@company.com").first()
    if u:
        Head.objects.filter(user=u).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_head, noop_reverse),
    ]
