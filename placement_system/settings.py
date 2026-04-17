"""
Django settings for placement_system project.
"""

import os
from pathlib import Path
from decouple import config

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-dev-key-here-change-this')
DEBUG = config('DEBUG', default='True', cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',

    # Your apps
    'apps.dashboard',
    'apps.data_uploads',
    'apps.ml_engine',
    'apps.reports',
    'apps.authentication',
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

ROOT_URLCONF = 'placement_system.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'placement_system.wsgi.application'

# Database Configuration

def get_database_config():
    postgres_db = config('POSTGRES_DB', default=None)
    if postgres_db:
        postgres_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': postgres_db,
            'USER': config('POSTGRES_USER', default='postgres'),
            'PASSWORD': config('POSTGRES_PASSWORD', default=''),
            'HOST': config('POSTGRES_HOST', default='127.0.0.1'),
            'PORT': config('POSTGRES_PORT', default='5432'),
        }
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=postgres_config['NAME'],
                user=postgres_config['USER'],
                password=postgres_config['PASSWORD'],
                host=postgres_config['HOST'],
                port=postgres_config['PORT'],
                connect_timeout=5,
            )
            conn.close()
            return postgres_config
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}")
            print("Attempting MongoDB or SQLite fallback...")

    try:
        from pymongo import MongoClient
        # Test MongoDB connection
        client = MongoClient(
            config('MONGODB_URI', default='mongodb://localhost:27017/placement_system'),
            username=config('MONGODB_USERNAME', default=''),
            password=config('MONGODB_PASSWORD', default=''),
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        # Try to get server info to test connection
        client.admin.command('ping')
        client.close()

        # If successful, return MongoDB config
        return {
            'ENGINE': 'djongo',
            'NAME': config('MONGODB_DATABASE', default='placement_system'),
            'CLIENT': {
                'host': config('MONGODB_URI', default='mongodb://localhost:27017/placement_system'),
                'username': config('MONGODB_USERNAME', default=''),
                'password': config('MONGODB_PASSWORD', default=''),
                'authSource': 'admin',
                'authMechanism': 'SCRAM-SHA-1'
            }
        }
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print("Falling back to SQLite database...")
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }

DATABASES = {
    'default': get_database_config()
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'

if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / 'static']
else:
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'