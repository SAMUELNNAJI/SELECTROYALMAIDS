from django.db import migrations, models


HERO_DATA = {
    'safety-guidelines': {
        'hero_subtitle': 'Your safety and peace of mind are our top priority. Please read these guidelines carefully before using our platform.',
        'hero_icon': 'fa-shield-halved',
        'hero_pill': 'TRUSTED & VERIFIED',
    },
    'terms-of-service': {
        'hero_subtitle': 'Please read these terms carefully. By using SelectRoyal Maids, you agree to be bound by these terms of service.',
        'hero_icon': 'fa-file-contract',
        'hero_pill': 'LEGAL AGREEMENT',
    },
    'privacy-policy': {
        'hero_subtitle': 'We take your privacy seriously. This policy explains how we collect, use, and protect your personal information.',
        'hero_icon': 'fa-lock',
        'hero_pill': 'YOUR PRIVACY',
    },
    'refund-policy': {
        'hero_subtitle': 'We want you to be completely satisfied with our service. Here is our policy regarding refunds and cancellations.',
        'hero_icon': 'fa-right-left',
        'hero_pill': 'HASSLE-FREE',
    },
}


def backfill_hero(apps, schema_editor):
    EditablePage = apps.get_model('MaidApp', 'EditablePage')
    for slug, data in HERO_DATA.items():
        EditablePage.objects.filter(slug=slug).update(**data)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('MaidApp', '0025_editablepage'),
    ]

    operations = [
        migrations.AddField(
            model_name='editablepage',
            name='hero_subtitle',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='editablepage',
            name='hero_icon',
            field=models.CharField(default='fa-file-lines', max_length=100),
        ),
        migrations.AddField(
            model_name='editablepage',
            name='hero_pill',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.RunPython(backfill_hero, noop),
    ]