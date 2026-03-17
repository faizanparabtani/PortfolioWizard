"""
Development settings.

Loads .env automatically, uses SQLite, enables hot-reload, and relaxes
security constraints so you can iterate quickly without needing HTTPS or
a PostgreSQL instance.
"""
import os

from dotenv import load_dotenv

# Load .env BEFORE base.py reads os.environ so all variables are present.
load_dotenv()

from .base import *  # noqa: E402, F401, F403

DEBUG = True

# Fall back to a local-only insecure key so you never need to set
# DJANGO_SECRET_KEY in .env during development.
if not SECRET_KEY:
    SECRET_KEY = 'dev-only-insecure-key-do-not-use-in-production'  # noqa: S105

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]']

# --- Dev-only apps & middleware --------------------------------------------- #

INSTALLED_APPS = INSTALLED_APPS + ['django_browser_reload']

MIDDLEWARE = MIDDLEWARE + ['django_browser_reload.middleware.BrowserReloadMiddleware']

# --- Database --------------------------------------------------------------- #
# Always use SQLite locally — no DATABASE_URL needed.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Static files ----------------------------------------------------------- #
# Skip the manifest step so collectstatic isn't required during development.

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# --- Email ------------------------------------------------------------------ #
# Print emails to the console instead of sending them.

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
