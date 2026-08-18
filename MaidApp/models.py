from django.db import models
from django.conf import settings


class MaidRegistration(models.Model):
    """An application submitted by a domestic professional."""

    ROLE_CHOICES = [
        ('maid', 'Maid / House Help'),
        ('cook', 'Cook / Chef'),
        ('nanny', 'Nanny / Babysitter'),
        ('caregiver', 'Caregiver'),
        ('driver', 'Driver'),
    ]
    WORK_TYPE_CHOICES = [
        ('live_in', 'Live-in'),
        ('live_out', 'Live-out'),
        ('both', 'Live-in or Live-out'),
    ]

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    state = models.CharField(max_length=80)
    city = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES)
    years_experience = models.PositiveSmallIntegerField()
    availability = models.CharField(max_length=100)
    expected_salary = models.CharField(max_length=100)
    languages = models.CharField(max_length=255)
    skills = models.TextField()
    bio = models.TextField()
    nin = models.CharField(max_length=11)
    reference_name = models.CharField(max_length=120)
    reference_phone = models.CharField(max_length=30)
    profile_photo = models.FileField(upload_to='maid_profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.get_role_display()}'


class SupportMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class BlogPost(models.Model):
    CATEGORY_CHOICES = [
        ('hiring',  'Hiring Tips'),
        ('safety',  'Safety'),
        ('career',  'Career Advice'),
        ('family',  'Family Life'),
        ('guides',  'How-To Guides'),
        ('general', 'General'),
    ]

    slug          = models.SlugField(max_length=160, unique=True)
    title         = models.CharField(max_length=200)
    excerpt       = models.TextField(help_text='Short summary shown on the listing page')
    category      = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    author_name   = models.CharField(max_length=120)
    author_avatar = models.URLField(blank=True, help_text='URL to author profile photo')
    author_bio    = models.TextField(blank=True)
    cover_image   = models.URLField(blank=True)
    content       = models.TextField(help_text='Full article HTML or plain text')
    tags          = models.CharField(max_length=300, blank=True, help_text='Comma-separated tags')
    read_time     = models.PositiveSmallIntegerField(default=5, help_text='Estimated read time in minutes')
    views         = models.PositiveIntegerField(default=0)
    is_featured   = models.BooleanField(default=False)
    is_published  = models.BooleanField(default=True)
    published_at  = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def tags_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def category_display(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)

    def __str__(self):
        return self.title


class Service(models.Model):
    ICON_CHOICES = [
        ('fa-broom',       'Broom (Maid)'),
        ('fa-utensils',    'Utensils (Cook)'),
        ('fa-baby',        'Baby (Nanny)'),
        ('fa-heart-pulse', 'Heart Pulse (Elderly Care)'),
        ('fa-car',         'Car (Driver)'),
        ('fa-star',        'Star (Generic)'),
    ]
    BADGE_CHOICES = [
        ('blue',   'Blue — Most Popular'),
        ('orange', 'Orange — In Demand'),
        ('green',  'Green — Highly Rated'),
        ('purple', 'Purple — Compassionate'),
        ('teal',   'Teal'),
    ]

    slug        = models.SlugField(max_length=60, unique=True, help_text='Used in URL tab ID, e.g. "maid"')
    title       = models.CharField(max_length=120)
    badge_label = models.CharField(max_length=60, blank=True)
    badge_color = models.CharField(max_length=20, choices=BADGE_CHOICES, default='blue')
    icon        = models.CharField(max_length=40, choices=ICON_CHOICES, default='fa-star')
    description = models.TextField()
    features    = models.TextField(help_text='One feature per line')
    image_url   = models.URLField(blank=True)
    available_count = models.CharField(max_length=20, default='0+')
    avg_rating      = models.CharField(max_length=10, default='4.9★')
    guarantee_days  = models.PositiveSmallIntegerField(default=30)
    order       = models.PositiveSmallIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def features_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveSmallIntegerField(default=0, help_text='Lower numbers appear first')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.question
