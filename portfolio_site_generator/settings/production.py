"""
Production settings.

Reads all configuration from environment variables — no .env file is loaded
here. Set variables through your hosting platform (Railway, Render, etc.).
"""
import os

from .base import *  # noqa: F401, F403

DEBUG = False

# --- Required env vars ------------------------------------------------------ #

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable is required in production")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required in production")

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# --- Security headers ------------------------------------------------------- #

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Trust the X-Forwarded-Proto header set by Railway/Render's reverse proxy.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- Static files ----------------------------------------------------------- #
# CompressedManifestStaticFilesStorage is already set in base.py.
# Run `python manage.py collectstatic` during build.
