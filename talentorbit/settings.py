"""
Django settings for TalentOrbit project.
"""

import os
from pathlib import Path
import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Initialise environ — read .env from project root
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# No default — raises ImproperlyConfigured if SECRET_KEY is missing from .env
SECRET_KEY = env('SECRET_KEY')

DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage',
    'core',
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
    'core.middleware.RateLimitMiddleware',
    'core.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'talentorbit.urls'

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
                'core.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'talentorbit.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        conn_max_age=env.int('CONN_MAX_AGE', default=600),
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'core.User'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cloudinary Media Storage (Production & Dev)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

# If Cloudinary is configured, use it for media. Otherwise fallback to local.
if CLOUDINARY_STORAGE['CLOUD_NAME']:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Upload size limits — 52 MB max (allows video uploads up to 50 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800

# Email configuration
EMAIL_CONFIG = env.email_url('EMAIL_URL', default='consolemail://')
vars().update(EMAIL_CONFIG)
# django-environ puts TLS in OPTIONS dict instead of EMAIL_USE_TLS — fix it
if isinstance(EMAIL_CONFIG.get('OPTIONS'), dict):
    _opts = EMAIL_CONFIG['OPTIONS']
    if str(_opts.get('TLS', '')).lower() == 'true':
        EMAIL_USE_TLS = True
        EMAIL_USE_SSL = False
    elif str(_opts.get('SSL', '')).lower() == 'true':
        EMAIL_USE_SSL = True
        EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@talentorbit.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Authentication backends (support login with email or username)
AUTHENTICATION_BACKENDS = [
    'core.backends.EmailOrUsernameBackend',
]

# Login/Logout URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Token expiry for password reset and email verification (24 hours)
PASSWORD_RESET_TIMEOUT = 86400

# Logging
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'talentorbit.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'] if DEBUG else ['console', 'file'],
        'level': 'WARNING',
    },
}

# Security settings for production
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Razorpay payment gateway
RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET', default='')
