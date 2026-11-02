import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "tracker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "tracker.context.account",
            ],
        },
    },
]

# All data lives in Firestore, so Django needs no SQL database.
DATABASES = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"  # "today" for roll call follows this; change if needed
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- accounts ----------------------------------------------------------------
# Users live in Firestore. The login session is a signed cookie, so no SQL
# database is needed.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # stay logged in for 7 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# Set SECURE_COOKIES=1 once the site is served over HTTPS.
SESSION_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "0") == "1"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

# Teachers must enter this code when they sign up, so students cannot make
# themselves teachers. In production, set TEACHER_SIGNUP_CODE to something private.
# If it is empty, teacher sign-up is switched off.
TEACHER_SIGNUP_CODE = os.environ.get(
    "TEACHER_SIGNUP_CODE", "rollcall-teacher" if DEBUG else ""
)
