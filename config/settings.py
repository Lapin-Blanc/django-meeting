"""
Django settings for django-meeting project.

Mode développement : fonctionne sans aucune variable d'environnement.
Mode production (Docker) : surcharger via variables d'environnement DJANGO_*.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name, default='False'):
    return os.environ.get(name, default).lower() in ('true', '1', 'yes')


# ============================================================
# Security
# ============================================================

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    os.environ.get('SECRET_KEY', 'dev-insecure-key-change-in-production-django-meeting-2024')
)

DEBUG = _bool('DJANGO_DEBUG', 'True')

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    _allowed = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost')
    ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()]

_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

# Proxy (cloudflared, nginx, etc.)
USE_X_FORWARDED_HOST = _bool('DJANGO_USE_X_FORWARDED_HOST')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if USE_X_FORWARDED_HOST else None

# HTTPS / cookies
SECURE_SSL_REDIRECT = _bool('DJANGO_SECURE_SSL_REDIRECT')
SESSION_COOKIE_SECURE = _bool('DJANGO_SESSION_COOKIE_SECURE')
CSRF_COOKIE_SECURE = _bool('DJANGO_CSRF_COOKIE_SECURE')

# HSTS
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = _bool('DJANGO_SECURE_HSTS_PRELOAD')

# ============================================================
# Application definition
# ============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    # Third-party
    'solo',
    'django_apscheduler',
    # Local apps
    'apps.site_config',
    'apps.accounts',
    'apps.polls',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.site_config.context_processors.site_configuration',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ============================================================
# Database
# ============================================================

_db_path = os.environ.get('DJANGO_DB_PATH', os.environ.get('DATABASE_PATH', str(BASE_DIR / 'db.sqlite3')))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _db_path,
    }
}

# ============================================================
# Password validation
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# Internationalization
# ============================================================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Brussels'
USE_I18N = True
USE_TZ = True

# ============================================================
# Static files (CSS, JavaScript, Images)
# ============================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================
# Media files (uploads)
# ============================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media'))
SERVE_MEDIA = _bool('DJANGO_SERVE_MEDIA', 'True')

# ============================================================
# Authentication
# ============================================================

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ============================================================
# Default primary key field type
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# Email (géré dynamiquement via SiteConfiguration)
# Fallback console en développement si SMTP non configuré
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================================
# APScheduler
# ============================================================

APSCHEDULER_DATETIME_FORMAT = 'N j, Y, f:s a'
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # seconds
