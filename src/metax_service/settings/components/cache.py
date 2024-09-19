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
            "OPTIONS": {"MAX_ENTRIES": 10000},
        }
    }
    CACHALOT_ENABLED = False

ENABLE_DATASET_CACHE = env.bool("ENABLE_DATASET_CACHE", False)
DEBUG_DATASET_CACHE = env.bool("DEBUG_DATASET_CACHE", False)  # Log cache info

if ENABLE_DATASET_CACHE:
    if ENABLE_MEMCACHED:
        CACHES["serialized_datasets"] = {
            "BACKEND": "apps.cache.caches.IgnoreTooLargePyMemcacheCache",
            "LOCATION": "localhost:11211",
            "KEY_PREFIX": "dataset",
            "TIMEOUT": None,
        }
    else:
        CACHES["serialized_datasets"] = {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "serialized-datasets",
            "OPTIONS": {"MAX_ENTRIES": 50000},
        }
else:
    CACHES["serialized_datasets"] = {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
