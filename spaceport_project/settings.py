"""Local challenge configuration; deploy with a private secret and DEBUG disabled."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'spaceport-local-development-only')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
INSTALLED_APPS = ['django.contrib.contenttypes', 'rest_framework', 'charter_app']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.middleware.common.CommonMiddleware']
ROOT_URLCONF = 'spaceport_project.urls'
WSGI_APPLICATION = 'spaceport_project.wsgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.environ.get('SPACEPORT_DB', BASE_DIR / 'db.sqlite3'),
    # Obtain the writer reservation before reading conflicts inside atomic().
    'OPTIONS': {'transaction_mode': 'IMMEDIATE', 'timeout': 20},
    'TEST': {'NAME': BASE_DIR / 'test.sqlite3'},
}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TIME_ZONE = 'America/Chicago'
USE_TZ = True
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}
