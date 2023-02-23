import abc
import logging
from typing import Protocol

from django.db import transaction
from django.db.models import prefetch_related_objects

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
        - is_removed    set True if deprecated
        - any additional fields from the model

        """
        raise NotImplementedError()

    def get_existing_objects_by_url(self):
        """Return dict of reference data objects by URL."""
        all_reference_objects = self.model.all_objects.filter(is_reference_data=True)
        return {object.url: object for object in all_reference_objects}

    def assign_fields(self, data_item, obj):
        """Assign fields to object from dict."""

        obj.in_scheme = self.scheme or data_item.get("in_scheme", "")
        obj.is_removed = data_item.get("is_removed", False)  # 'unremove' changed objects

        for field, value in data_item.items():
            if field in {"url", "in_scheme", "broader", "narrower"}:
                continue
            if not hasattr(obj, field):
                raise ValueError(f"Invalid field '{field}' for {self.data_type}")
            setattr(obj, field, value)

    def create_or_update_objects(self, data, objects_by_url):
        """Update existing reference data objects or create new if needed."""
        new_object_count = 0
        existing_object_count = 0
        deprecated_object_count = 0

        for data_item in data:
            url = data_item["url"]
            obj = objects_by_url.get(url)
            is_new = not obj
            if is_new:
                obj = self.model(url=url, is_reference_data=True)
                objects_by_url[url] = obj

            self.assign_fields(data_item, obj)
            obj.save()

            if is_new:
                new_object_count += 1
            else:
                existing_object_count += 1
            if obj.is_removed:
                deprecated_object_count += 1

        return {
            "new": new_object_count,
            "existing": existing_object_count,
            "deprecated": deprecated_object_count,
        }

    def create_relationships(self, data, objects_by_url):
        """Create hierarchical relationships between objects."""
        prefetch_related_objects(list(objects_by_url.values()), "broader", "narrower")

        # clear any previously existing children
        for data_item in data:
            obj = objects_by_url.get(data_item["url"])
            if obj.narrower.count() > 0:
                obj.narrower.clear()

        # set parent relations, which will also assign parents' children
        for data_item in data:
            obj = objects_by_url.get(data_item["url"])
            broader = [
                objects_by_url[parent_url]
                for parent_url in data_item.get("broader", [])
                if parent_url in objects_by_url
            ]
            if len(broader) > 0 or obj.broader.count() > 0:
                obj.broader.set(broader)

    @transaction.atomic
    def save(self, data):
        objects_by_url = self.get_existing_objects_by_url()

        counts = self.create_or_update_objects(data, objects_by_url)
        self.create_relationships(data, objects_by_url)
        _logger.info(
            f"Created {counts['new']} new objects, "
            f"updated {counts['existing']} existing objects "
            f"({counts['deprecated']} deprecated objects)"
        )

    def load(self):
        _logger.info("Extracting relevant data from the parsed data")
        data = self.get_data()

        _logger.info("Saving objects")
        if data:
            self.save(data)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.source}>"
