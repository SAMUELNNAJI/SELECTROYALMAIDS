import re
import re
import re
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.files.storage import default_storage
from .image_utils import download_external_image


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
    nin = models.CharField(max_length=11, unique=True)
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
    # The employer whose support conversation this message belongs to.  Support
    # staff can reply to a particular employer without exposing it to others.
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_conversations',
        null=True,
        blank=True,
    )
    body = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
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
    author_avatar = models.URLField(max_length=500, blank=True, help_text='URL to author profile photo')
    author_bio    = models.TextField(blank=True)
    cover_image      = models.URLField(max_length=500, blank=True)
    cover_image_file = models.ImageField(upload_to='blog/covers/', blank=True, null=True,
                                         help_text='Upload a cover image (used instead of URL if provided)')
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

    @property
    def cover_url(self):
        """Returns the best available cover image URL — uploaded file takes priority over the URL field."""
        if self.cover_image_file:
            return self.cover_image_file.url
        return self.cover_image or ''

    def save(self, *args, **kwargs):
        if self.cover_image and not self.cover_image_file:
            downloaded = download_external_image(self.cover_image, 'blog/covers')
            if downloaded:
                self.cover_image_file = downloaded
        super().save(*args, **kwargs)

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
    image_url   = models.URLField(max_length=500, blank=True)
    image_file  = models.ImageField(upload_to='services/', blank=True, null=True,
                                    help_text='Downloaded from image_url if provided')
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

    def get_image_url(self):
        """
        Uploaded file takes priority over the remote URL. On this VPS the
        media disk is persistent, so uploads survive redeploys — unlike the
        old Render setup where hot-linking the CDN URL was the safer choice.
        """
        if self.image_file:
            return self.image_file.url
        return self.image_url or ''

    def __str__(self):
        return self.title


def _next_reg_number():
    """Return the next unique SRM-XXXXX reg number based on the highest existing number."""
    max_num = 0
    for rn in MaidProfile.objects.filter(reg_number__startswith='SRM-').values_list('reg_number', flat=True):
        try:
            num = int(rn.split('-', 1)[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    return f'SRM-{max_num + 1}'


def _next_legacy_id():
    """Return max(legacy_id) + 1 so the unique constraint is always satisfied."""
    from django.db.models import Max
    return (MaidProfile.objects.aggregate(m=Max('legacy_id'))['m'] or 0) + 1


def employer_plan(target, kind):
    """Return the subscription plan ('standard'/'premium') for an assignment target.

    `kind` is 'user' for site employers (AUTH_USER_MODEL) or 'legacy' for
    LegacyEmployer rows imported from request.sql.
    """
    if kind == 'user':
        try:
            return target.employer_profile.plan
        except Exception:
            return 'standard'
    return getattr(target, 'plan', 'standard')


def assigned_maid_count(target, kind, exclude_pk=None):
    """How many maids are currently assigned to this employer."""
    qs = MaidProfile.objects.all()
    qs = qs.filter(assigned_employer=target) if kind == 'user' else qs.filter(assigned_legacy_employer=target)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def placement_capacity_error(target, kind, exclude_pk=None):
    """Return an error message when assigning another maid would exceed the
    employer's plan capacity, or None when the assignment is allowed.
    Standard employers can hold only one maid; Premium employers unlimited."""
    if employer_plan(target, kind) == 'standard' and assigned_maid_count(target, kind, exclude_pk=exclude_pk) >= 1:
        name = str(target)
        return (f'{name} is on the Standard plan and already has a maid assigned. '
                'Standard employers can only be assigned one maid — upgrade them to Premium to assign more.')
    return None


class LegacyEmployer(models.Model):
    """An employer request imported from the legacy site's `request` table
    (selectro_new.request — see request.sql in the project root)."""

    PLAN_CHOICES = [
        ('standard', 'Standard'),
        ('premium',  'Premium'),
    ]

    legacy_id        = models.PositiveIntegerField(unique=True, help_text='Original `request.id` from the legacy database')
    first_name       = models.CharField(max_length=500, blank=True)
    last_name        = models.CharField(max_length=500, blank=True)
    phone            = models.CharField(max_length=500, blank=True)
    email            = models.CharField(max_length=500, blank=True)
    home_address     = models.CharField(max_length=500, blank=True)
    profession       = models.CharField(max_length=500, blank=True)
    company          = models.CharField(max_length=500, blank=True)
    company_address  = models.CharField(max_length=500, blank=True)
    family_members   = models.CharField(max_length=500, blank=True)
    apartment_type   = models.CharField(max_length=500, blank=True)
    marital_status   = models.CharField(max_length=500, blank=True)
    maid_gender      = models.CharField(max_length=500, blank=True)
    requested_service = models.TextField(blank=True)
    how_soon         = models.CharField(max_length=500, blank=True)
    plan             = models.CharField(max_length=20, choices=PLAN_CHOICES, default='premium')
    assigned         = models.CharField(max_length=500, blank=True, help_text="Raw legacy 'assigned' value ('unassigned' or a maid reg number)")
    is_spam          = models.BooleanField(default=False, db_index=True, help_text='Bot/spam submission detected during import')
    imported_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['legacy_id']
        verbose_name = 'Legacy employer (request.sql)'
        verbose_name_plural = 'Legacy employers (request.sql)'

    def __str__(self):
        return f'#{self.legacy_id} {self.full_name or "Unnamed"} — {self.get_plan_display()}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def assigned_reg_number(self):
        """The maid reg number recorded in the legacy dump, if any."""
        value = (self.assigned or '').strip()
        if not value or value.lower() == 'unassigned':
            return ''
        return value

    @property
    def legacy_assigned_maid(self):
        """MaidProfile referenced by the legacy 'assigned' reg number, if any."""
        reg = self.assigned_reg_number
        if not reg:
            return None
        return MaidProfile.objects.filter(reg_number__iexact=reg).first()


class MaidProfile(models.Model):
    """Imported maid profiles from the old selectroyalmaids.com.ng database."""

    ASSIGN_STATUS = [
        ('assigned',   'Assigned'),
        ('unassigned', 'Available'),
    ]

    # Original fields from old DB
    legacy_id      = models.IntegerField(unique=True, help_text='Original DB id')
    reg_number     = models.CharField(max_length=20, help_text='e.g. SRM-1658')
    slug           = models.SlugField(max_length=255, unique=True)
    full_name      = models.CharField(max_length=200)
    address        = models.TextField(blank=True)
    age            = models.CharField(max_length=10, blank=True)
    phone          = models.CharField(max_length=60, blank=True)
    email          = models.EmailField(blank=True)
    description    = models.TextField(blank=True)
    photo_filename = models.CharField(max_length=300, blank=True,
                                      help_text='Filename as stored on old server')
    image          = models.ImageField(upload_to='maid_profiles/', blank=True, null=True,
                                      help_text='Upload a profile photo')
    assign_status  = models.CharField(max_length=20, choices=ASSIGN_STATUS,
                                      default='unassigned')
    assigned_employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_maids',
        help_text='Site employer this maid is currently placed with.')
    assigned_legacy_employer = models.ForeignKey(
        'LegacyEmployer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_maids',
        help_text='Legacy employer (request.sql) this maid is currently placed with.')
    is_featured    = models.BooleanField(default=False)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']   # newest profiles first everywhere

    def save(self, *args, **kwargs):
        """Auto-generate reg_number/legacy_id, keep the placement status in
        sync with the assigned employer, and enforce the plan capacity rule
        (Standard employers may hold only ONE maid, Premium unlimited)."""
        if not self.pk:
            if not self.reg_number:
                self.reg_number = _next_reg_number()
            if not self.legacy_id:
                self.legacy_id = _next_legacy_id()

        if self.assign_status == 'unassigned':
            # An available maid cannot keep an employer attached.
            if self.assigned_employer_id or self.assigned_legacy_employer_id:
                self.assigned_employer = None
                self.assigned_legacy_employer = None
                update_fields = kwargs.get('update_fields')
                if update_fields:
                    kwargs['update_fields'] = tuple(set(update_fields) | {'assigned_employer', 'assigned_legacy_employer'})
        else:
            if self.assigned_employer_id:
                error = placement_capacity_error(self.assigned_employer, 'user', exclude_pk=self.pk)
                if error:
                    raise ValueError(error)
            if self.assigned_legacy_employer_id:
                error = placement_capacity_error(self.assigned_legacy_employer, 'legacy', exclude_pk=self.pk)
                if error:
                    raise ValueError(error)
            # Choosing an employer implies the maid is assigned.
            if self.assigned_employer_id or self.assigned_legacy_employer_id:
                self.assign_status = 'assigned'
        return super().save(*args, **kwargs)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @property
    def assigned_employer_label(self):
        """Human-readable label of the employer this maid is assigned to."""
        if self.assigned_employer_id:
            user = self.assigned_employer
            name = user.get_full_name() or user.username or user.email
            plan = 'standard'
            try:
                plan = user.employer_profile.plan
            except Exception:
                pass
            return f'{name} — {plan} plan'
        if self.assigned_legacy_employer_id:
            legacy = self.assigned_legacy_employer
            return f'{legacy.full_name} — {legacy.plan} plan (legacy)'
        return ''

    def photo_url(self):
        """
        Return the best URL for this maid's photo.
        Uploaded image takes priority over legacy filename.
        Legacy photos are hosted on the old site at:
          https://selectroyalmaids.com.ng/maids_photos/<filename>
        """
        if self.image:
            return self.image.url
        if not self.photo_filename:
            return ''
        name = self.photo_filename
        if name.startswith('maids/'):
            name = name[len('maids/'):]
        return f'https://selectroyalmaids.com.ng/maids_photos/{name}'

    @property
    def is_available(self):
        return self.assign_status == 'unassigned'

    @property
    def first_name(self):
        parts = self.full_name.strip().split()
        return parts[0] if parts else self.full_name

    def __str__(self):
        return f'{self.full_name} ({self.reg_number})'


class PlacementRequest(models.Model):
    """A single employer position, from request through completed placement."""
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('concluded', 'Placement concluded'),
        ('expired', 'Replacement window expired'),
    ]

    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='placement_requests')
    role = models.CharField(max_length=100)
    candidate = models.ForeignKey(MaidProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='placements')
    plan = models.CharField(max_length=20, choices=[('standard', 'Standard'), ('premium', 'Premium')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    requested_at = models.DateTimeField(auto_now_add=True)
    concluded_at = models.DateTimeField(null=True, blank=True)
    replacement_expires_at = models.DateTimeField(null=True, blank=True)
    requires_payment = models.BooleanField(default=False)
    replacement_for = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replacements')

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.employer} — {self.role} ({self.get_status_display()})'

    def conclude(self, candidate):
        """Lock the candidate and start the Premium one-year replacement period."""
        self.candidate = candidate
        self.status = 'concluded'
        self.concluded_at = timezone.now()
        self.replacement_expires_at = (
            self.concluded_at + timedelta(days=365) if self.plan == 'premium' else None
        )
        self.save(update_fields=['candidate', 'status', 'concluded_at', 'replacement_expires_at'])

    @property
    def has_free_replacement(self):
        return bool(
            self.plan == 'premium' and self.status == 'concluded' and
            self.replacement_expires_at and timezone.now() <= self.replacement_expires_at
        )

    def record_free_replacement(self, candidate):
        """Create a same-role Premium replacement without extending the guarantee."""
        if not self.has_free_replacement:
            raise ValueError('This placement is not eligible for a free replacement.')
        return PlacementRequest.objects.create(
            employer=self.employer,
            role=self.role,
            candidate=candidate,
            plan='premium',
            status='concluded',
            concluded_at=timezone.now(),
            replacement_expires_at=self.replacement_expires_at,
            replacement_for=self,
        )


class MaidRecommendation(models.Model):
    """A maid recommended to a specific employer."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='maid_recommendations'
    )
    maid = models.ForeignKey(MaidProfile, on_delete=models.CASCADE, related_name='recommendations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    recommended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recommendations_made'
    )
    recommended_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text='Optional notes from admin')

    class Meta:
        ordering = ['-recommended_at']
        unique_together = ['employer', 'maid']  # Prevent duplicate recommendations

    def __str__(self):
        return f'{self.maid} → {self.employer} ({self.status})'

    def accept(self):
        """Accept the recommendation."""
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save(update_fields=['status', 'responded_at'])

    def decline(self):
        """Decline the recommendation."""
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save(update_fields=['status', 'responded_at'])


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



def extract_policy_blocks(html):
    """Parse HTML and return a list of dicts {id, title, html} for every
    <div class="policy-block">...</div> section. Handles nested divs
    (e.g. .policy-notice) via balanced-div matching."""
    result = []
    content = html or ''
    pos = 0
    while True:
        start = content.find('<div class="policy-block"', pos)
        if start == -1:
            break
        i = start
        depth = 0
        end = -1
        while i < len(content):
            m = re.search(r'<div\b|</div\s*>', content[i:])
            if not m:
                break
            if m.group(0) == '<div':
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    end = i + m.end()
                    break
            i += m.end()
        if end == -1:
            end = len(content)
        block_html = content[start:end].strip()
        pos = end
        if not block_html:
            continue
        idm = re.search(r'\bid="([^"]+)"', block_html)
        bid = idm.group(1) if idm else ''
        h2m = re.search(r'<h2[^>]*>(.*?)</h2>', block_html, re.S)
        title = re.sub(r'<[^>]+>', ' ', h2m.group(1)).strip() if h2m else ''
        title = re.sub(r'\s+', ' ', title).strip()
        result.append({'id': bid, 'title': title, 'html': block_html})
    return result


class EditablePage(models.Model):
    """Admin-editable content for the public static pages
    (safety guidelines, terms, privacy, refund). When a row exists for a
    slug the public page renders this HTML instead of the hardcoded template."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text='HTML content rendered on the public page')
    hero_subtitle = models.TextField(default='', blank=True)
    hero_icon = models.CharField(max_length=100, default='fa-file-lines')
    hero_pill = models.CharField(max_length=100, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        return self.title

    def body_html(self):
        """Return just the .policy-block sections (extras stripped)."""
        return '\n'.join(b['html'] for b in extract_policy_blocks(self.content or ''))

    def toc_blocks(self):
        """Return a list of {'id', 'title'} for the 'On This Page' sidebar,
        auto-derived from the section headings. Sections without an id get one
        slugified from their title."""
        blocks = []
        for b in extract_policy_blocks(self.content or ''):
            bid = b['id']
            if not bid:
                base = re.sub(r'[^a-z0-9]+', '-', b['title'].lower()).strip('-')
                bid = base or 'section'
            blocks.append({'id': bid, 'title': b['title']})
        return blocks


class BlogSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email
