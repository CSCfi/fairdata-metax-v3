# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from apps.core.models import DataCatalog, DatasetLanguage
from apps.core.serializers import (
    AccessRightsModelSerializer,
    DatasetPublisherModelSerializer,
    DatasetLanguageModelSerializer,
    AbstractDatasetPropertyModelSerializer,
)
from rest_framework import serializers
logger = logging.getLogger(__name__)


def update_or_create_instance(serializer, instance, data):
    if instance is not None:
        serializer.update(instance, data)
    else:
        new_serializer = serializer.__class__(data=data)
        if new_serializer.is_valid(raise_exception=True):
            new_serializer.save()


class DataCatalogModelSerializer(serializers.ModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    publisher = DatasetPublisherModelSerializer(required=False)
    language = DatasetLanguageModelSerializer(required=False, many=True)

    class Meta:
        model = DataCatalog
        fields = (
            "id",
            "access_rights",
            "publisher",
            "language",
            "title",
            "dataset_versioning_enabled",
            "harvested",
            "research_dataset_schema",
            "url"
        )

    @staticmethod
    def get_or_create_languages(language_data):
        languages = []
        for lang in language_data:
            language_created, created = DatasetLanguage.objects.get_or_create(
                url=lang.get("url"), defaults=lang
            )
            languages.append(language_created)
        return languages

    def create(self, validated_data):
        publisher = None
        access_rights = None

        language_data = validated_data.pop("language", [])

        publisher_serializer: DatasetPublisherModelSerializer = self.fields["publisher"]
        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]

        if access_rights_data := validated_data.pop("access_rights", None):
            access_rights = access_rights_serializer.create(access_rights_data)

        if publisher_data := validated_data.pop("publisher", None):
            publisher = publisher_serializer.create(publisher_data)

        new_datacatalog: DataCatalog = DataCatalog.objects.create(
            access_rights=access_rights, publisher=publisher, **validated_data
        )

        languages = self.get_or_create_languages(language_data)
        new_datacatalog.language.add(*languages)

        return new_datacatalog

    def update(self, instance, validated_data):
        access_rights_serializer = self.fields["access_rights"]
        access_rights_instance = instance.access_rights

        publisher_serializer = self.fields["publisher"]
        publisher_instance = instance.publisher

        if access_rights_data := validated_data.pop("access_rights", None):
            update_or_create_instance(
                access_rights_serializer,
                access_rights_instance,
                access_rights_data,
            )

        if publisher_data := validated_data.pop("publisher", None):
            update_or_create_instance(
                publisher_serializer, publisher_instance, publisher_data
            )

        if language_data := validated_data.pop("language", None):
            instance.language.clear()
            languages = self.get_or_create_languages(language_data)
            instance.language.add(*languages)

        return super().update(instance, validated_data)
