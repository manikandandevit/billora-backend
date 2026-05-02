"""
Django settings for Billora API.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")

DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")

# Set USE_TLS=1 in production (behind HTTPS). Do not infer from DEBUG alone — some stacks use HTTP internally.
USE_TLS = _env_bool("USE_TLS", "false")

if (not DEBUG or USE_TLS) and (
    len(SECRET_KEY) < 48
    or "change-me" in SECRET_KEY.lower()
    or SECRET_KEY.startswith("django-insecure")
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a long random string (48+ chars), not the dev default, "
        "when DEBUG=False or USE_TLS=1."
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "accounts",
    "orgs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_db_password = os.environ.get("DB_PASSWORD")
if _db_password:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "postgres"),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": _db_password,
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "OPTIONS": {"sslmode": os.environ.get("DB_SSLMODE", "require")},
            "DISABLE_SERVER_SIDE_CURSORS": True,
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
# Subscription end calculation uses calendar day in this zone (ISO name, e.g. Asia/Kolkata).
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC").strip() or "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Production: serve admin/app static from STATIC_ROOT (after collectstatic). Dev uses app static finders.
if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

_email_host = os.environ.get("EMAIL_HOST", "").strip()
if _email_host:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = _email_host
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    _tls = os.environ.get("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
    EMAIL_USE_TLS = _tls
    EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() in ("1", "true", "yes")
    if not EMAIL_USE_TLS and not EMAIL_USE_SSL and EMAIL_PORT == 465:
        EMAIL_USE_SSL = True
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@billora.local")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_HOST = "localhost"
    EMAIL_PORT = 25
    EMAIL_USE_TLS = False
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Billora <noreply@billora.local>")

# Optional: primary inbox for product notifications (BCC / internal routing in your mail flows)
BILLORA_RECEIVER_EMAIL = os.environ.get("BILLORA_RECEIVER_EMAIL", "").strip()

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.SubscriptionEnforcingJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_RATES": {
        "login": os.environ.get("JWT_LOGIN_THROTTLE", "20/minute"),
        "refresh": os.environ.get("JWT_REFRESH_THROTTLE", "60/minute"),
        "anon": os.environ.get("DRF_ANON_THROTTLE", "120/minute"),
    },
}

_access_minutes = int(os.environ.get("JWT_ACCESS_MINUTES", "15"))
_refresh_days = int(os.environ.get("JWT_REFRESH_DAYS", "14"))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=_access_minutes),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=_refresh_days),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "LEEWAY": int(os.environ.get("JWT_LEEWAY_SECONDS", "5")),
}

_jwt_issuer = os.environ.get("JWT_ISSUER", "").strip()
if _jwt_issuer:
    SIMPLE_JWT["ISSUER"] = _jwt_issuer

_jwt_audience = os.environ.get("JWT_AUDIENCE", "").strip()
if _jwt_audience:
    SIMPLE_JWT["AUDIENCE"] = _jwt_audience

_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "https://billora-frontend.vercel.app,"
    "https://billora-frontend-git-main-manikandans-projects-5f6ac6b9.vercel.app,"
    "https://billora-frontend-k5ykr8l4x-manikandans-projects-5f6ac6b9.vercel.app"
)
_cors = os.environ.get("CORS_ALLOWED_ORIGINS", _default_origins)

def _normalize_cors_origin(o: str) -> str:
    return o.strip().rstrip("/")

CORS_ALLOWED_ORIGINS = [_normalize_cors_origin(o) for o in _cors.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# Covers production + future Vercel preview URLs under billora-frontend*.vercel.app
_cors_regex_raw = os.environ.get("CORS_ALLOWED_ORIGIN_REGEXES", "").strip()
if _cors_regex_raw and _cors_regex_raw.lower() in ("none", "false", "0", "off"):
    CORS_ALLOWED_ORIGIN_REGEXES: list[str] = []
else:
    CORS_ALLOWED_ORIGIN_REGEXES = (
        [p.strip() for p in _cors_regex_raw.split("|") if p.strip()]
        if _cors_regex_raw
        else [r"^https://billora-frontend(?:-[\w.-]+)?\.vercel\.app$"]
    )

_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS = (
    [o.strip() for o in _csrf_origins.split(",") if o.strip()]
    if _csrf_origins
    else list(CORS_ALLOWED_ORIGINS)
)

if USE_TLS:
    if _env_bool("TRUST_PROXY_SSL", "false"):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", "true")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", str(60 * 60 * 24 * 365)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true")
    SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", "false")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = os.environ.get("SECURE_REFERRER_POLICY", "same-origin")
    SECURE_CROSS_ORIGIN_OPENER_POLICY = os.environ.get("SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin")
    X_FRAME_OPTIONS = "DENY"
