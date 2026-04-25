"""
Base settings shared by all environments.
Do not use this file directly — import from development or production.
"""

from pathlib import Path
import os

from ..logging_config import logging_config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECRET_KEY is intentionally left as None here.
# development.py provides a fallback; production.py validates it.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

# --- Application definition ------------------------------------------------- #

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "tailwind",
    "theme",
    "corsheaders",
    # Local
    "generator",
    "users",
]

TAILWIND_APP_NAME = "theme"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "portfolio_site_generator.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "theme" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portfolio_site_generator.wsgi.application"

# --- Database --------------------------------------------------------------- #
# Default to SQLite; override with DATABASE_URL in production.

import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# --- Static & media files --------------------------------------------------- #

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Auth ------------------------------------------------------------------- #

LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "generator:dashboard"
LOGOUT_REDIRECT_URL = "generator:landing"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalisation ---------------------------------------------------- #

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS ------------------------------------------------------------------- #

CORS_ALLOWED_ORIGINS = [
    "https://kit.fontawesome.com",
]

# --- API keys --------------------------------------------------------------- #

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- Logging ---------------------------------------------------------------- #

LOGGING = logging_config
