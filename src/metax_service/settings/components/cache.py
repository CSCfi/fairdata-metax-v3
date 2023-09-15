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
            "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
            "LOCATION": "localhost:11211",
        }
    }
else:
    CACHALOT_ENABLED = False
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
