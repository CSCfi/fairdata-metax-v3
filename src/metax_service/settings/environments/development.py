from metax_service.settings.components.base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "0.0.0.0",  # noqa: S104
    "127.0.0.1",
    "[::1]",
    "metax.localdomain",
]
INTERNAL_IPS = [
    "127.0.0.1",
]
DEV_ONLY_APPS = [
    "debug_toolbar",
]
DEV_ONLY_MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    # "silk.middleware.SilkyMiddleware",
]
INSTALLED_APPS = INSTALLED_APPS + DEV_ONLY_APPS
MIDDLEWARE = MIDDLEWARE + DEV_ONLY_MIDDLEWARE
