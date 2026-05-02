from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0004_remove_head_subscription_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="client",
            name="subscription_type",
            field=models.CharField(
                choices=[
                    ("free", "Free"),
                    ("basic", "Basic"),
                    ("standard", "Standard"),
                    ("pro", "Professional"),
                    ("enterprise", "Enterprise"),
                ],
                default="free",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="subscription_end",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="client",
            name="expiry_reminder_sent",
            field=models.BooleanField(
                default=False,
                help_text="Set when the 3-days-before email was sent for the current subscription_end.",
            ),
        ),
    ]
