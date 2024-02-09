from cachalot.settings import SUPPORTED_CACHE_BACKENDS

from metax_service.settings.components.base import env

ENABLE_MEMCACHED = env.bool("ENABLE_MEMCACHED", False)
CACHALOT_DATABASES = ["default"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
if ENABLE_MEMCACHED:
    CACHES = {
        "default": {
            "BACKEND": "apps.cache.caches.IgnoreTooLargePyMemcacheCache",
            "LOCATION": "localhost:11211",
        }
    }
    # Patch list of supported cache backends to suppress warning
    SUPPORTED_CACHE_BACKENDS.add("apps.cache.caches.IgnoreTooLargePyMemcacheCache")
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
    CACHALOT_ENABLED = False
