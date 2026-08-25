import os
import traceback
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'selectroyal.settings')
django.setup()

from django.conf import settings
# ── PRODUCTION CONDITIONS ──
settings.DEBUG = False
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

print('DEBUG =', settings.DEBUG)
print('STATICFILES_STORAGE =', getattr(settings, 'STATICFILES_STORAGE', '<default>'))
print('WHITENOISE_USE_FINDERS =', getattr(settings, 'WHITENOISE_USE_FINDERS', '<unset>'))

from django.test import Client
from django.contrib.auth.models import User
from Authentication.models import EmployerProfile

admin = User.objects.filter(is_superuser=True).first()
c = Client()

def probe(label, url):
    try:
        # production conditions: do NOT raise — capture like the server does,
        # but re-render exception info ourselves from the response? The test
        # client with default raise_request_exception=True will raise; catch it.
        r = c.get(url, raise_request_exception=True)
        print(f'{label} {url} -> {r.status_code}')
    except Exception:
        print(f'{label} {url} -> EXCEPTION:')
        tb = traceback.format_exc()
        print(tb[-3500:])

print('\n===== ADMIN DASHBOARD =====')
if admin:
    c.force_login(admin)
    probe('ADMIN', '/admin/dashboard/')
    probe('ADMIN', '/admin/dashboard/?tab=employers')
    probe('ADMIN', '/admin/dashboard/?tab=maids')
    probe('ADMIN', '/admin/dashboard/?tab=placements')
else:
    print('no superuser found')

print('\n===== EMPLOYER DASHBOARD =====')
paid = EmployerProfile.objects.filter(payment_status='paid').select_related('user').first()
if paid:
    c.force_login(paid.user)
    r = None
    try:
        r = c.get('/employer/dashboard/', raise_request_exception=False)
        print('EMPLOYER /employer/dashboard/ ->', r.status_code)
        if r.status_code >= 400:
            print(r.content.decode(errors='replace')[:2500])
    except Exception:
        print('EMPLOYER /employer/dashboard/ -> EXCEPTION:')
        print(traceback.format_exc()[-3500:])
else:
    print('no paid employer found')

print('\nDONE')