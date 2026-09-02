from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class PendingSignup(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    password = models.CharField(max_length=128)
    phone = models.CharField(max_length=30, blank=True)
    city = models.CharField(max_length=100, blank=True)
    plan = models.CharField(max_length=20, default='standard')
    service = models.CharField(max_length=100, blank=True)
    how_heard = models.CharField(max_length=100, blank=True)
    request_details = models.TextField(blank=True, help_text="Employer's specific requirements and requests")
    house_address = models.CharField(max_length=300, blank=True)
    marital_status = models.CharField(max_length=60, blank=True)
    profession = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    apartment_type = models.CharField(max_length=200, blank=True)
    rooms = models.CharField(max_length=100, blank=True)
    maid_gender = models.CharField(max_length=50, blank=True)
    expected_resume_date = models.DateField(blank=True, null=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    # Flutterwave v4 charge id (chg_xxx) once a card charge has been initiated.
    flw_charge_id = models.CharField(max_length=40, blank=True, default='')

    class Meta:
        verbose_name = 'Pending Signup'
        verbose_name_plural = 'Pending Signups'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} — {self.plan}'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class EmployerProfile(models.Model):
    PLAN_CHOICES = [
        ('standard', 'Standard'),
        ('premium',  'Premium'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
    ]

    PLAN_AMOUNTS = {
        'standard': 10000,
        'premium':  20000,
    }

    user           = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employer_profile',
    )
    phone          = models.CharField(max_length=30, blank=True)
    city           = models.CharField(max_length=100, blank=True)
    service_needed = models.CharField(max_length=100, blank=True)
    how_heard      = models.CharField(max_length=100, blank=True)
    request_details = models.TextField(blank=True, help_text='Employer\'s specific requirements and requests')
    house_address  = models.CharField(max_length=300, blank=True)
    marital_status = models.CharField(max_length=60, blank=True)
    profession     = models.CharField(max_length=200, blank=True)
    company        = models.CharField(max_length=200, blank=True)
    apartment_type = models.CharField(max_length=200, blank=True)
    rooms          = models.CharField(max_length=100, blank=True)
    maid_gender    = models.CharField(max_length=50, blank=True)
    expected_resume_date = models.DateField(blank=True, null=True)
    plan           = models.CharField(max_length=20, choices=PLAN_CHOICES, default='standard')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_ref    = models.CharField(max_length=200, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Employer Profile'
        verbose_name_plural = 'Employer Profiles'

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.get_plan_display()} ({self.payment_status})'

    @property
    def amount(self):
        return self.PLAN_AMOUNTS.get(self.plan, 10000)

    @property
    def is_paid(self):
        return self.payment_status == 'paid'
