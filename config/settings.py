"""Zoo Planeta company website — Django + Wagtail."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.getenv("SECRET_KEY", "")
DEBUG = env_bool("DEBUG")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("SECRET_KEY is required when DEBUG is off")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "core",
    "pages",
    "stores",
    "leads",
    "catalog",

    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.simple_translation",
    "wagtail.locales",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "core.context_processors.site",
            ],
        },
    },
]

# SQLite: one file, enough for an info site (few editors, a few dozen form posts a day).
# In Docker the file lives in /app/data, mounted from the host — rebuilding the image keeps it.
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", BASE_DIR / "db.sqlite3"))
SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SQLITE_PATH,
        "OPTIONS": {
            # WAL: readers never block the writer; IMMEDIATE + timeout: no "database is locked"
            # when several gunicorn workers write at once
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;",
        },
    }
}
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", SQLITE_PATH.parent / "backups"))
BACKUP_KEEP = int(os.getenv("BACKUP_KEEP", "14"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# ── languages ────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский"), ("uz", "Oʻzbekcha"), ("en", "English")]
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES
USE_I18N = True
TIME_ZONE = "Asia/Tashkent"
USE_TZ = True

# ── static / media ───────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = Path(os.getenv("STATIC_ROOT", BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))
# CVs and other personal files: not served by the web server, only through the CMS
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", BASE_DIR / "private"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ── wagtail ──────────────────────────────────────────────────────────────────
WAGTAIL_SITE_NAME = "Zoo Planeta"
# public address of the site: canonical URLs, sitemap, Open Graph (python manage.py sync_site applies it to Wagtail)
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
WAGTAILADMIN_BASE_URL = SITE_URL
WAGTAIL_ENABLE_UPDATE_CHECK = False
WAGTAIL_ENABLE_WHATS_NEW_BANNER = False
WAGTAIL_GRAVATAR_PROVIDER_URL = None  # no requests to gravatar.com from the CMS
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 15 * 1024 * 1024
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILADMIN_PERMITTED_LANGUAGES = [("ru", "Русский"), ("en", "English")]
ADMIN_URL = os.getenv("ADMIN_URL", "cms/").strip("/") + "/"

# map tiles (OpenStreetMap by default; change if the traffic grows)
MAP_TILE_URL = os.getenv("MAP_TILE_URL", "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
MAP_TILE_ATTRIBUTION = os.getenv("MAP_TILE_ATTRIBUTION", "&copy; OpenStreetMap")

# e-mail notifications about new applications (optional)
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "site@zooplaneta.uz")
LEADS_NOTIFY_EMAILS = [e.strip() for e in os.getenv("LEADS_NOTIFY_EMAILS", "").split(",") if e.strip()]
# Telegram notifications about new applications (optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── security ─────────────────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^health/$"]  # local checks over plain http
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "SAMEORIGIN"  # Wagtail preview uses an iframe

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "WARNING")},
}
