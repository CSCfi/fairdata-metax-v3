from rest_framework import serializers

from metax_service.settings.components.base import (
    ALLOWED_HOSTS,
    DATABASES,
    ENABLE_DEBUG_TOOLBAR,
    ENABLE_SILK_PROFILER,
    INSTALLED_APPS,
    MIDDLEWARE,
)

DEBUG = True

ALLOWED_HOSTS = ALLOWED_HOSTS + [
    "metax.localdomain",
    "127.0.0.1",
    "localhost",
    ".fd-dev.csc.fi",
]

SHELL_PLUS_SUBCLASSES_IMPORT = [serializers.Serializer]

CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "https://localhost",
    "https://etsin.fd-dev.csc.fi",
    "https://qvain.fd-dev.csc.fi",
]
CORS_ORIGIN_ALLOW_ALL = True

DEBUG_TOOLBAR_APPS = [
    "debug_toolbar",
]
DEBUG_TOOLBAR_MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.history.HistoryPanel",
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "cachalot.panels.CachalotPanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",
]
SILK_MIDDLEWARE = ["silk.middleware.SilkyMiddleware"]
SILK_APP = ["silk"]

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS = INSTALLED_APPS + DEBUG_TOOLBAR_APPS
    MIDDLEWARE = MIDDLEWARE + DEBUG_TOOLBAR_MIDDLEWARE
if ENABLE_SILK_PROFILER:
    INSTALLED_APPS = INSTALLED_APPS + SILK_APP
    MIDDLEWARE = SILK_MIDDLEWARE + MIDDLEWARE

SILKY_DYNAMIC_PROFILING = [
    {"module": "apps.core.views.dataset_view", "function": "DatasetViewSet.list"}
]

DATABASES["default"]["ATOMIC_REQUESTS"] = True

PID_MS_CLIENT_INSTANCE = "apps.core.services.pid_ms_client._DummyPIDMSClient"

# Print emails in console instead of sending
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
