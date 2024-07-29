import abc
import logging
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.helpers import cachalot_toggle

_logger = logging.getLogger(__name__)


class ReferenceDataImporterInterface(Protocol, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def load(self):
        """Load the reference data from external source"""

    @property
    @abc.abstractmethod
    def data_type(self):
        """Return the data type of the reference data"""


class BaseDataImporter(ReferenceDataImporterInterface):
    def __init__(self, model, source, scheme=None):
        self.model = model
        self.source = source  # file path or URL
        self.scheme = scheme  # if scheme is not set, use scheme from data

    @property
    def data_type(self):
        return self.model.__name__

    def get_data(self):
        """Return a list of dicts containing the object fields.

        Expected fields
        - url           URL identifier of the concept
        - in_scheme     scheme of the concept
        - pref_label    dict of translations
        - broader       list of parent concept URLs, used to build relations between concepts
        - same_as       list of URLs of equivalent concepts
        - deprecated    set to datetime if deprecated
        - any additional fields from the model

        """
        raise NotImplementedError()

    def get_existing_objects_by_url(self):
        """Return dict of reference data objects by URL."""
        all_reference_objects = self.model.all_objects.all()
        return {object.url: object for object in all_reference_objects}

    def assign_fields(self, data_item, obj):
        """Assign fields to object from dict."""

        old_scheme = obj.in_scheme
        old_deprecated = obj.deprecated
        obj.in_scheme = self.scheme or data_item.get("in_scheme", "")
        if deprecated := data_item.get("deprecated"):
            # keep existing value if already deprecated
            obj.deprecated = obj.deprecated or deprecated
        else:
            obj.deprecated = None
        changed = obj.in_scheme != old_scheme or obj.deprecated != old_deprecated

        for field, value in data_item.items():
            if field in {"url", "in_scheme", "broader", "narrower", "deprecated"}:
                continue
            if field == "pref_label" and value and isinstance(value, dict):
                value = {
                    k: v for k, v in value.items() if k in settings.REFDATA_LANGUAGES
                } or dict([next(iter(value.items()))])

            if not hasattr(obj, field):
                raise ValueError(f"Invalid field '{field}' for {self.data_type}")
            if getattr(obj, field) != value:
                changed = True
                setattr(obj, field, value)

        return changed

    def get_bulk_update_fields(self):
        return {
            field.name
            for field in self.model._meta.fields
            if not field.is_relation and not field.primary_key
        }

    def create_or_update_objects(self, data, objects_by_url):
        """Update existing reference data objects or create new if needed."""
        new_object_count = 0
        updated_object_count = 0
        unchanged_object_count = 0
        deprecated_object_count = 0

        found_ids = []
        new_objects = []
        updated_objects = []
        for data_item in data:
            url = data_item["url"]
            obj = objects_by_url.get(url)
            is_new = not obj
            if is_new:
                obj = self.model(url=url)
                new_objects.append(obj)
                objects_by_url[url] = obj
                new_object_count += 1
            else:
                found_ids.append(obj.id)

            changed = self.assign_fields(data_item, obj)

            if not is_new:
                if changed:
                    updated_objects.append(obj)
                    updated_object_count += 1
                    if obj.deprecated:
                        deprecated_object_count += 1
                else:
                    unchanged_object_count += 1

        # Deprecate objects no longer in source data
        removed_reference_objects = self.model.all_objects.filter(deprecated__isnull=True).exclude(
            id__in=found_ids
        )
        missing_count = removed_reference_objects.update(deprecated=timezone.now())
        updated_object_count += missing_count
        deprecated_object_count += missing_count

        self.model.all_objects.bulk_create(new_objects, batch_size=1000)
        self.model.all_objects.bulk_update(
            updated_objects, fields=self.get_bulk_update_fields(), batch_size=1000
        )

        return {
            "new": new_object_count,
            "updated": updated_object_count,
            "unchanged": unchanged_object_count,
            "deprecated": deprecated_object_count,
        }

    def create_relationships(self, data, objects_by_url):
        """Create hierarchical relationships between objects."""
        # Clear any previously existing parent and child relations for data.
        # Use auto-created through model to change relations directly in bulk.
        objs = [objects_by_url.get(data_item["url"]) for data_item in data]
        through_model = self.model.broader.through
        from_field = self.model.broader.field.m2m_field_name()
        to_field = self.model.broader.field.m2m_reverse_field_name()
        through_model.objects.filter(**{f"{to_field}__in": objs}).delete()
        through_model.objects.filter(**{f"{from_field}__in": objs}).delete()

        # Set parent relations, which will also assign parents' children
        relations = []  # Collect and update m2m relations in bulk
        for data_item in data:
            obj = objects_by_url.get(data_item["url"])
            broader = [
                objects_by_url[parent_url]
                for parent_url in data_item.get("broader", [])
                if parent_url in objects_by_url
            ]
            if len(broader) > 0:
                relations.extend(
                    (through_model(**{from_field: obj, to_field: parent}) for parent in broader)
                )
        through_model.objects.bulk_create(relations, batch_size=1000)

    @transaction.atomic
    def save(self, data):
        objects_by_url = self.get_existing_objects_by_url()
        counts = self.create_or_update_objects(data, objects_by_url)
        self.create_relationships(data, objects_by_url)
        _logger.info(f"Created {counts['new']} new objects")
        _logger.info(f"Updated {counts['updated']} existing objects")
        _logger.info(f"Left {counts['unchanged']} existing objects unchanged")
        _logger.info(f"Deprecated {counts['deprecated']} objects")

    def load(self):
        _logger.info("Extracting relevant data from the parsed data")
        data = self.get_data()

        _logger.info(f"Saving {self.model.__name__} objects")
        if data:
            with cachalot_toggle(enabled=False):
                self.save(data)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.source}>"
