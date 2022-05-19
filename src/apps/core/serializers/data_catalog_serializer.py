# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging
from rest_framework.serializers import ModelSerializer

from apps.core.models import DataCatalog, DatasetLicense, AccessType, DatasetPublisher, AccessRight, CatalogHomePage, \
    DatasetLanguage
from apps.core.serializers.common_serializers import AccessRightsModelSerializer, DatasetPublisherModelSerializer, \
    DatasetLanguageModelSerializer, AbstractDatasetPropertyModelSerializer

logger = logging.getLogger(__name__)
# class DataCatalogSerializer(ModelSerializer):
#     access_rights = AccessRightsModelSerializer(read_only=True)
#     publisher = DatasetPublisherModelSerializer(read_only=True)
#     language = DatasetLanguageModelSerializer(read_only=True, many=True)
#
#     class Meta:
#         model = DataCatalog
#         fields = ('id', 'access_rights', 'publisher', 'language', 'title', 'dataset_versioning_enabled', 'harvested', 'research_dataset_schema')

class DataCatalogModelSerializer(AbstractDatasetPropertyModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    publisher = DatasetPublisherModelSerializer(required=False)
    language = DatasetLanguageModelSerializer(required=False, many=True)

    class Meta(AbstractDatasetPropertyModelSerializer.Meta):
        model = DataCatalog
        fields = ('id', 'access_rights', 'publisher', 'language', 'title', 'dataset_versioning_enabled', 'harvested',
                  'research_dataset_schema')

    def create(self, validated_data):
        access_type = None
        publisher = None
        access_rights = None
        datacatalog_license = None
        homepages_data = []
        license_data = None
        access_type_data = None
        logger.info(f"{validated_data=}")
        language_data = validated_data.pop("language", [])
        publisher_data = validated_data.pop("publisher", None)
        access_rights_data = validated_data.pop("access_rights", None)
        if publisher_data:
            homepages_data = publisher_data.pop("homepage", [])
        if access_rights_data:
            license_data = access_rights_data.pop("license", None)
            access_type_data = access_rights_data.pop("access_type", None)

        if license_data:
            datacatalog_license, license_created = DatasetLicense.objects.get_or_create(url=license_data.get("url"), defaults=license_data)
        if access_type_data:
            access_type, access_type_created = AccessType.objects.get_or_create(url=access_type_data.get("url"), defaults=access_type_data)
        if publisher_data:
            publisher = DatasetPublisher.objects.create(name=publisher_data.get('name'))
        if access_rights_data:
            access_rights = AccessRight.objects.create(license=datacatalog_license, access_type=access_type, **access_rights_data)
        new_datacatalog = DataCatalog.objects.create(access_rights=access_rights, publisher=publisher, **validated_data)

        for page in homepages_data:
            logger.info(f"{page=}")
            homepage, created = CatalogHomePage.objects.get_or_create(url=page.get('url'), defaults=page)
            publisher.homepage.add(homepage)
        for lang in language_data:
            language_created, created = DatasetLanguage.objects.get_or_create(url=lang.get('url'), defaults=lang)
            new_datacatalog.language.add(language_created)

        return new_datacatalog


class DataCatalogUpdateSerializer(ModelSerializer):
    access_rights = AccessRightsModelSerializer(read_only=True)
    publisher = DatasetPublisherModelSerializer(read_only=True)
    language = DatasetLanguageModelSerializer(read_only=True, many=True)

    class Meta:
        model = DataCatalog
        fields = ('id', 'access_rights', 'publisher', 'language', 'title', 'dataset_versioning_enabled', 'harvested',
                  'research_dataset_schema')
        read_only_fields = ['id', ]
