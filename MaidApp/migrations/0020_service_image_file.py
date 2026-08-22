from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MaidApp', '0019_blogsubscriber'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='image_file',
            field=models.ImageField(
                upload_to='services/',
                blank=True,
                null=True,
                help_text='Downloaded from image_url if provided',
            ),
        ),
    ]
