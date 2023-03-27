from metax_service.settings.components.base import (
    ALLOWED_HOSTS,
    INSTALLED_APPS,
    MIDDLEWARE,
    ENABLE_DEBUG_TOOLBAR,
    ENABLE_SILK_PROFILER,
)


DEBUG = True

ALLOWED_HOSTS = ALLOWED_HOSTS + ["metax.localdomain", "127.0.0.1", "localhost"]

DEBUG_TOOLBAR_APPS = [
    "debug_toolbar",
]
DEBUG_TOOLBAR_MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
SILK_MIDDLEWARE = ["silk.middleware.SilkyMiddleware"]
SILK_APP = ["silk"]

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS = INSTALLED_APPS + DEBUG_TOOLBAR_APPS
    MIDDLEWARE = MIDDLEWARE + DEBUG_TOOLBAR_MIDDLEWARE

if ENABLE_SILK_PROFILER:
    INSTALLED_APPS = INSTALLED_APPS + SILK_APP
    MIDDLEWARE = SILK_MIDDLEWARE + MIDDLEWARE
