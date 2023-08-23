from metax_service.settings.components.base import (
    ALLOWED_HOSTS,
    ENABLE_DEBUG_TOOLBAR,
    ENABLE_SILK_PROFILER,
    INSTALLED_APPS,
    MIDDLEWARE,
)

DEBUG = True

ALLOWED_HOSTS = ALLOWED_HOSTS + ["metax.localdomain", "127.0.0.1", "localhost", ".fd-dev.csc.fi"]

DEBUG_TOOLBAR_APPS = [
    "debug_toolbar",
]
DEBUG_TOOLBAR_MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.history.HistoryPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'cachalot.panels.CachalotPanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
]
SILK_MIDDLEWARE = ["silk.middleware.SilkyMiddleware"]
SILK_APP = ["silk"]

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS = INSTALLED_APPS + DEBUG_TOOLBAR_APPS
    MIDDLEWARE = MIDDLEWARE + DEBUG_TOOLBAR_MIDDLEWARE
if ENABLE_SILK_PROFILER:
    INSTALLED_APPS = INSTALLED_APPS + SILK_APP
    MIDDLEWARE = SILK_MIDDLEWARE + MIDDLEWARE
