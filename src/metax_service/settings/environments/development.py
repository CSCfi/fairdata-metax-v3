from metax_service.settings.components.base import INSTALLED_APPS, MIDDLEWARE, ALLOWED_HOSTS

DEBUG = True

ALLOWED_HOSTS = ALLOWED_HOSTS + ["metax.localdomain"]

DEV_ONLY_APPS = [
    "debug_toolbar",
]
DEV_ONLY_MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    # "silk.middleware.SilkyMiddleware",
]
INSTALLED_APPS = INSTALLED_APPS + DEV_ONLY_APPS
MIDDLEWARE = MIDDLEWARE + DEV_ONLY_MIDDLEWARE
