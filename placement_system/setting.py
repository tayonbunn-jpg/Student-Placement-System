# placement_system/settings.py
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings - use environment variables
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-dev-key-here')

# DEBUG should be False in production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Allow Render domain and localhost
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# Add Render's URL pattern
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Database configuration - use PostgreSQL on Render
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files configuration with WhiteNoise
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if DEBUG else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Add WhiteNoise to serve static files
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WhiteNoise storage for compressed static files
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (for user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'