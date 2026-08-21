"""
Django settings for selectroyal project.
Production-ready: reads secrets from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Always read this project's environment file when developing locally.  The
# override makes a corrected value in .env take precedence over an old value
# inherited by the VS Code/PowerShell process.  Render has no project .env, so
# its configured service environment variables continue to be used there.
load_dotenv(BASE_DIR / '.env', override=True)

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-#ft)d8hphvo=s84d#$zm%dq3mq$)h-sy4fj$*&g!p)b3xytq(a',
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1 selectroyalmaids.onrender.com').split()

# ── Applications ──────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_summernote',
    'MaidApp',
    'Authentication',
    'Dashboard',
]

# ── Middleware (WhiteNoise inserted after SecurityMiddleware) ──────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # serves static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'selectroyal.middleware.NoCacheMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'selectroyal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'Templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'selectroyal.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# Uses Neon PostgreSQL by default. Override with DATABASE_URL env var if needed.
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_Y6Dvjkcfi1Tt@ep-late-sky-b1le0p0y-pooler.c-5.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=DATABASE_URL.startswith(('postgres://', 'postgresql://')),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Lagos'
USE_I18N      = True
USE_TZ        = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'          # where collectstatic writes to
STATICFILES_DIRS = [BASE_DIR / 'static']        # source static folder

# WhiteNoise compression + caching for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media files ───────────────────────────────────────────────────────────────
# NOTE: Render's disk is ephemeral. For persistent uploads use an S3-compatible
# service (e.g. Cloudinary or AWS S3) and swap these settings accordingly.
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Security headers (enforced in production) ─────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT          = True
    SESSION_COOKIE_SECURE        = True
    CSRF_COOKIE_SECURE           = True
    SECURE_HSTS_SECONDS          = 31536000   # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD          = True
    SECURE_BROWSER_XSS_FILTER   = True
    SECURE_CONTENT_TYPE_NOSNIFF  = True

# ── Summernote ────────────────────────────────────────────────────────────────
SUMMERNOTE_CONFIG = {
    'summernote': {
        'width': '100%',
        'height': '480',
        'toolbar': [
            ['style',  ['style']],
            ['font',   ['bold', 'italic', 'underline', 'strikethrough', 'clear']],
            ['fontsize', ['fontsize']],
            ['color',  ['color']],
            ['para',   ['ul', 'ol', 'paragraph']],
            ['height', ['height']],
            ['table',  ['table']],
            ['insert', ['link', 'picture', 'hr']],
            ['view',   ['fullscreen', 'codeview']],
            ['help',   ['help']],
        ],
    },
    'disable_attachment': False,
}

# Summernote needs iframe rendering
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)

if EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
    EMAIL_HOST      = os.environ.get('EMAIL_HOST', 'smtp.zeptomail.com')
    EMAIL_PORT      = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS   = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_USE_SSL   = os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true'
    if EMAIL_USE_TLS and EMAIL_USE_SSL:
        raise ValueError('Set only one of EMAIL_USE_TLS or EMAIL_USE_SSL.')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'emailapikey')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    # Never allow an unavailable SMTP server to hold a web request indefinitely.
    EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'info@selectroyalmaids.com.ng')
    SERVER_EMAIL = DEFAULT_FROM_EMAIL
else:
    EMAIL_HOST_USER = ''
    EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))
    EMAIL_HOST_PASSWORD = ''
    DEFAULT_FROM_EMAIL = 'info@selectroyalmaids.com.ng'
    SERVER_EMAIL = DEFAULT_FROM_EMAIL

SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

# Flutterwave must return the customer to the public HTTPS address of this
# application.  Set this explicitly in production when the service sits behind
# a proxy or has more than one hostname.  Leaving it blank keeps local
# development convenient by deriving the address from the incoming request.
PAYMENT_CALLBACK_URL = os.environ.get('PAYMENT_CALLBACK_URL', '').rstrip('/')



# WhatsApp Business Cloud API. Set these in the deployment environment to have
# maid applications delivered to WhatsApp as PDF documents.
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_APPLICATION_RECIPIENT = os.environ.get('WHATSAPP_APPLICATION_RECIPIENT', '2349137894958')

# ── Logging (suppress noisy HTTPS-on-HTTP 400s in dev) ───────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'suppress_https_warnings': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: 'You\'re accessing the development server over HTTPS' not in record.getMessage()
                                       and 'Bad request' not in record.getMessage(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['suppress_https_warnings'],
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ── Misc ──────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Flutterwave ───────────────────────────────────────────────────────────────
FLUTTERWAVE_PUBLIC_KEY  = os.environ.get('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_SECRET_KEY  = os.environ.get('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_ENCRYPT_KEY = os.environ.get('FLUTTERWAVE_ENCRYPT_KEY', '')
FLUTTERWAVE_VERIFY_URL  = 'https://api.flutterwave.com/v3/transactions/{id}/verify'
