# Generated manually for the private employer support conversation.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('MaidApp', '0013_maidprofile_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportmessage',
            name='employer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='support_conversations', to=settings.AUTH_USER_MODEL),
        ),
    ]
