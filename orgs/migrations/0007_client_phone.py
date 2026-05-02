from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0006_subscription_demo_monthly_yearly"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
