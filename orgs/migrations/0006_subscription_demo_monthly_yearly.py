from datetime import timedelta

from django.db import migrations, models


def forwards(apps, schema_editor):
    Client = apps.get_model("orgs", "Client")
    map_old = {
        "free": "monthly",
        "basic": "monthly",
        "standard": "monthly",
        "pro": "monthly",
        "enterprise": "yearly",
        "demo": "demo",
        "monthly": "monthly",
        "yearly": "yearly",
    }
    days_for = {"demo": 7, "monthly": 30, "yearly": 365}
    for c in Client.objects.all().iterator():
        nt = map_old.get(c.subscription_type, "monthly")
        d = days_for.get(nt, 30)
        end = c.created_at.date() + timedelta(days=d)
        Client.objects.filter(pk=c.pk).update(subscription_type=nt, subscription_end=end)


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0005_client_subscription_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="client",
            name="subscription_type",
            field=models.CharField(
                choices=[
                    ("demo", "Demo"),
                    ("monthly", "Monthly"),
                    ("yearly", "Yearly"),
                ],
                default="monthly",
                max_length=32,
            ),
        ),
    ]
