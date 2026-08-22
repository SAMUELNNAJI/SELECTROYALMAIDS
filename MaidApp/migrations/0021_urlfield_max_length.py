from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MaidApp', '0020_service_image_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogpost',
            name='author_avatar',
            field=models.URLField(blank=True, help_text='URL to author profile photo', max_length=500),
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='cover_image',
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='service',
            name='image_url',
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
