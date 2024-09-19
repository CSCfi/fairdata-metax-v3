from typing import List, Optional

from django.core.cache import BaseCache, caches
from django.db import models
from rest_framework import serializers

from apps.common.helpers import pickle_deepcopy


class SerializerCacheBase:
    """Helper base class for using a cache backend during serialization.

    Provides a dict-based short term cache that fetches its data from a
    Django cache backend and supports committing changes back.

    For usage example, see SerializerCacheSerializer.
    """

    # Attributes required to be set by subclasses
    cache_name: str  # Name of Django cache to use
    cached_fields: set  # Which fields are cached
    modified_attr: str  # Model attribute of latest modification timestamp

    # Internal fields
    changed: set  # Changed values not yet in source_cache

    def __init__(self, initial_instances: List[models.Model] = [], autocommit=True):
        self.get_source_cache()
        if not self.cached_fields:
            raise ValueError("Missing cached_fields")
        if not self.modified_attr:
            raise ValueError("Missing modified_attr")

        # When autocommit is enabled (default), changes are committed to source_cache immediately
        self.autocommit = autocommit
        self.changed = set()
        self.values = {}
        self.fetch_from_source(initial_instances)

    @classmethod
    def get_source_cache(cls) -> BaseCache:
        """Source cache is determined dynamically so it can be changed in tests."""
        return caches[cls.cache_name]

    def fetch_from_source(self, instances: List[models.Model], include_newer=False):
        """Fetch cached data from source cache.

        Fetch cached values that match modification timestamp of corresponding instance.
        """
        cached_values = self.get_source_cache().get_many([instance.id for instance in instances])
        for instance in instances:
            if cached := cached_values.get(instance.id):
                modified = getattr(instance, self.modified_attr)
                if cached["_modified"] == modified:
                    self.values[instance.id] = cached
                if include_newer and cached["_modified"] > modified:
                    # Include cache entries that are newer than instance
                    self.values[instance.id] = cached

    def commit_changed_to_source(self):
        changed = {key: self.values[key] for key in self.changed}
        self.get_source_cache().set_many(changed)
        self.clear_changed()

    def clear(self):
        self.values.clear()
        self.clear_changed()

    def clear_changed(self):
        self.changed.clear()

    def get_changed(self):
        return {k: v for k, v in self.values.items() if k in self.changed}

    def get_value(self, instance: models.Model) -> Optional[dict]:
        value = self.values.get(instance.id)
        if value is None:
            return None
        return {k: v for k, v in value.items() if k in self.cached_fields}

    def get_value_context(self, instance: models.Model):
        value = self.values.get(instance.id)
        if value is None:
            return None
        return value.get("_context")

    def set_value(
        self,
        instance: models.Model,
        value: dict,
        value_context: Optional[dict] = None,
        only_if_modified=False,
    ):
        """Set per-instance value to cache.

        The in-memory value is not copied so care needs to be taken
        to avoid modifying it after using set_value.
        """
        modified = getattr(instance, self.modified_attr)

        if only_if_modified:
            entry = self.values.get(instance.id) or {}
            if entry_modified := entry.get("_modified"):
                if modified <= entry_modified:
                    return  # Instance is same or older than existing cached entry

        self.changed.add(instance.id)
        self.values[instance.id] = {k: v for k, v in value.items() if k in self.cached_fields}
        self.values[instance.id]["_modified"] = modified
        if value_context:
            self.values[instance.id]["_context"] = value_context
        self.values[instance.id] = pickle_deepcopy(self.values[instance.id])
        if self.autocommit:
            self.commit_changed_to_source()


class SerializerCacheSerializer(serializers.Serializer):
    """Serializer with support for partially cached field values.

    Only fields in cached_fields are cached, so cache invalidation
    is needed only when a value in cached_fields changes.

    Usage example:
    ```
    class SerializerCache:
        cache_name = "default" # Use default Django cache
        cached_fields = {"field1", "field2"}  # Which fields are cached
        modified_attr = "modified" # Model field containing timestamp of latest modification

    class SomeSerializer(ModelSerializer, SerializerCacheSerializer):
        ...

        def to_representation(self, instance):
            ret = super().to_representation(instance)
            if cache := get_serializer_cache():
                # Save serialized value to serializer cache
                cache.set_value(instance, ret, only_if_modified=True)
            return ret

    # Serialize instances using cached values
    instances = SomeModel.objects.filter(...)
    cache = SerializerCache(instances)
    serializer = SomeSerializer(instances, cache=cache, many=True)
    serialized_values = serializer.data
    ```
    """

    def __init__(self, *args, cache: Optional[SerializerCacheBase] = None, **kwargs):
        self.cache = cache
        super().__init__(*args, **kwargs)

    def get_cached_field_sources(self) -> list:
        """List sources of cached fields."""
        if not self.cache:
            return []

        field_names = self.cache.cached_fields
        model_fields = [
            self.fields[name].source or name for name in field_names if name in self.fields
        ]
        return model_fields

    def to_representation(self, instance) -> dict:
        """Serialization modified to support cached values."""
        ret = {}
        fields = self._readable_fields

        cached_values = None
        cached_fields = None
        if cache := self.cache:
            cached_values = cache.get_value(instance)
            cached_fields = cache.cached_fields

        for field in fields:
            # Use cached value for field if available
            field_name = field.field_name
            if cached_values is not None and field_name in cached_fields:
                if field_name in cached_values:
                    ret[field_name] = cached_values[field_name]
                continue

            # Rest of the method works like normal Serializer.to_representation
            try:
                attribute = field.get_attribute(instance)
            except serializers.SkipField:
                continue

            check_for_none = (
                attribute.pk if isinstance(attribute, serializers.PKOnlyObject) else attribute
            )
            if check_for_none is None:
                ret[field_name] = None
            else:
                ret[field_name] = field.to_representation(attribute)

        return ret
