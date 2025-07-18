"""
Configuration de production pour Theologix Backend
"""
from .settings import *
import os

# Production settings
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS settings plus restrictifs
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# Rate limiting plus strict
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '50/hour',  # Plus restrictif en production
}

# Logging en production
LOGGING['handlers']['file']['filename'] = '/var/log/theologix/theologix.log'
LOGGING['loggers']['api']['level'] = 'WARNING'  # Moins verbeux

# Cache (optionnel avec Redis)
if config('REDIS_URL', default=''):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

# Database en production (optionnel)
if config('DATABASE_URL', default=''):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(config('DATABASE_URL'))