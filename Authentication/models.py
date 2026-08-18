from django.db import models
from django.conf import settings


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
