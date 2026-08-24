from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Authentication', '0002_pendingsignup'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingsignup',
            name='flw_charge_id',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
    ]
