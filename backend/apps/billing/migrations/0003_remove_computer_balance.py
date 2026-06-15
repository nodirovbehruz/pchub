from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_user_balance"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ComputerBalance",
        ),
    ]
