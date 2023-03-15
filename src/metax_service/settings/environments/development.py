from metax_service.settings.components.base import ALLOWED_HOSTS, INSTALLED_APPS, MIDDLEWARE

DEBUG = True

ALLOWED_HOSTS = ALLOWED_HOSTS + ["metax.localdomain", "127.0.0.1", "localhost"]

DEV_ONLY_APPS = [
    "debug_toolbar",
]
DEV_ONLY_MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    # "silk.middleware.SilkyMiddleware",
]
INSTALLED_APPS = INSTALLED_APPS + DEV_ONLY_APPS
MIDDLEWARE = MIDDLEWARE + DEV_ONLY_MIDDLEWARE
