# Caching

Metax V3 uses two separate caching mechanisms: django-cachalot, 
and a custom dataset cache implementation. Both support using the `memcached` data store.

## Cachalot

Cachalot is a library that caches Django ORM queries and automatically invalidates them.
Cachalot is enabled in Metax V3 by setting `ENABLE_MEMCACHED=true` in `.env` configuration.

If direct modifications are done to the database, it is a good idea to invalidate the
cache. This can be done by running the command `python manage.py invalidate_cachalot`.

See the official [cachalot docs](https://django-cachalot.readthedocs.io/) for further information.

## Dataset cache

When a dataset is serialized, a subset of dataset fields are cached in a data store.
When retrieving datasets, the serialized cached values are used for cached fields if available.
Only fields that don't have relations to other datasets or other dynamic information are cached.
As an exception, cached fields may contain reference data. It is recommended
to clear the cache if changes are made to reference data.

To enable the dataset cache, add `ENABLE_DATASET_CACHE=true` to `.env`. It is recommended
to also set `ENABLE_MEMCACHED=true` to enable `memcached` usage. Otherwise the cache uses 
a local per-process data store that is only useful for development.
When `DEBUG_DATASET_CACHE=true`, the server logs will include caching information when 
listing datasets.

To cache all uncached datasets, run `python manage.py cache_datasets`.
To clear the cache, run `python manage.py clear_dataset_cache`.


