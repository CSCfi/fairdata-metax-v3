import os

from metax_service.settings.components.base import DATABASES, LOGGING

LOGGING["handlers"]["file"] = {
    "level": "INFO",
    "class": "logging.FileHandler",
    "filename": os.environ.get("DJANGO_ERROR_LOG_FILENAME"),
    "formatter": "verbose",
}
LOGGING["root"]["handlers"] = ["console", "file"]

DATABASES["default"]["CONN_MAX_AGE"] = 30
DATABASES["default"]["ATOMIC_REQUESTS"] = True

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600  # one year 31536000
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
ENABLE_DEBUG_TOOLBAR = False
ENABLE_SILK_PROFILER = False

PID_MS_CLIENT_INSTANCE = "apps.core.services.pid_ms_client._PIDMSClient"
