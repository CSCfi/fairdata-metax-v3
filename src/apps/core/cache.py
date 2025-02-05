from django.db.models.base import Model as Model

from apps.cache.serializer_cache import SerializerCacheBase


class DatasetSerializerCache(SerializerCacheBase):
    cache_name = "serialized_datasets"
    modified_attr = "record_modified"
    cached_fields = {
        "id",
        "access_rights",
        "actors",
        "bibliographic_citation",
        "description",
        "field_of_science",
        "fileset",
        "infrastructure",
        "keyword",
        "language",
        "metadata_owner",
        "persistent_identifier",
        "projects",
        "provenance",
        "remote_resources",
        "spatial",
        "temporal",
        "theme",
        "title",
    }
