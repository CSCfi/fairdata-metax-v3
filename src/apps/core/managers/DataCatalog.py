from collections import OrderedDict
from django.db import models

from apps.core.models import DataCatalog


class DataCatalogFilter:

    def __init__(self, title=None, id=None, dataset_versioning_enabled=None, harvested=None,
                 research_dataset_schema=None, access_rights_id=None, access_rights_description=None,
                 access_type_id=None, access_type_title=None, publisher_id=None, publisher_name=None,
                 publisher_homepage_id=None, publisher_homepage_title=None, language_id=None, language_title=None):
        self.title = title
        self.id = id
        self.dataset_versioning_enabled = dataset_versioning_enabled
        self.harvested = harvested
        self.research_dataset_schema = research_dataset_schema
        self.access_rights_id = access_rights_id
        self.access_rights_description = access_rights_description
        self.access_type_id = access_type_id
        self.access_type_title = access_type_title
        self.publisher_id = publisher_id
        self.publisher_name = publisher_name
        self.publisher_homepage_id = publisher_homepage_id
        self.publisher_homepage_title = publisher_homepage_title
        self.language_id = language_id
        self.language_title = language_title

    def read_filters(self, data):
        pass


class DataCatalogManager(models.Manager):

    def filter_catalogs(self, filter_data=None, order_data=None):
        filters = OrderedDict()

        if 'title' in filter_data:
            filters['{0}__{1}'.format('title', 'icontains')] = filter_data.get('title')

        if 'id' in filter_data:
            filters['{0}__{1}'.format('id', 'icontains')] = filter_data.get('id')

        if 'dataset_versioning_enabled' in filter_data:
            filters['dataset_versioning_enabled'] = filter_data.get('dataset_versioning_enabled')

        if 'harvested' in filter_data:
            filters['harvested'] = filter_data.get('harvested')

        if 'research_dataset_schema' in filter_data:
            filters['research_dataset_schema'] = filter_data.get('research_dataset_schema')

        if 'access_rights_id' in filter_data:
            filters['{0}__{1}'.format('access_rights__id', 'icontains')] = filter_data.get('access_rights_id')

        if 'access_rights_description' in filter_data:
            filters['{0}__{1}'.format('access_rights__description', 'icontains')] = filter_data.get('access_rights_description')

        if 'access_type_id' in filter_data:
            filters['{0}__{1}'.format('access_rights__access_type__id', 'icontains')] = filter_data.get('access_type_id')

        if 'access_type_id' in filter_data:
            filters['{0}__{1}'.format('access_rights__access_type__title', 'icontains')] = filter_data.get('access_type_title')

        if 'publisher_id' in filter_data:
            filters['{0}__{1}'.format('publisher__id', 'icontains')] = filter_data.get('publisher_id')

        if 'publisher_name' in filter_data:
            filters['{0}__{1}'.format('publisher__name', 'icontains')] = filter_data.get('publisher_name')

        if 'publisher_homepage_id' in filter_data:
            filters['{0}__{1}'.format('publisher__homepage__id', 'icontains')] = filter_data.get('publisher_homepage_id')

        if 'publisher_homepage_title' in filter_data:
            filters['{0}__{1}'.format('publisher__homepage__title', 'icontains')] = filter_data.get('publisher_homepage_title')

        if 'language_id' in filter_data:
            filters['{0}__{1}'.format('language__id', 'icontains')] = filter_data.get('language_id')

        if 'language_title' in filter_data:
            filters['{0}__{1}'.format('language__title', 'icontains')] = filter_data.get('language_title')

        if filters:
            return DataCatalog.objects.filter(**filters)
        else:
            return DataCatalog.objects.all()

