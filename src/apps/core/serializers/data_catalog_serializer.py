# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from apps.core import models
from apps.core.serializers.common_serializers import (
    AccessRightsModelSerializer,
    DatasetPublisherModelSerializer,
    DatasetLanguageModelSerializer,
    AbstractDatasetPropertyModelSerializer,
)

logger = logging.getLogger(__name__)


def pop_and_update_or_create_instance(serializer, instance, field_name, validated_data):
    data = validated_data.pop(field_name)
    if instance is not None:
        serializer.update(instance, data)
    else:
        new_serializer = serializer.__class__(data=data)
        if new_serializer.is_valid(raise_exception=True):
            new_serializer.save()


class DataCatalogModelSerializer(AbstractDatasetPropertyModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    publisher = DatasetPublisherModelSerializer(required=False)
    language = DatasetLanguageModelSerializer(required=False, many=True)

    class Meta(AbstractDatasetPropertyModelSerializer.Meta):
        model = models.DataCatalog
        fields = (
            "id",
            "access_rights",
            "publisher",
            "language",
            "title",
            "dataset_versioning_enabled",
            "harvested",
            "research_dataset_schema",
        )

    def create(self, validated_data):
        publisher = None
        access_rights = None

        language_data = validated_data.pop("language", [])
        publisher_data = validated_data.pop("publisher", None)
        access_rights_data = validated_data.pop("access_rights", None)

        publisher_serializer = self.fields["publisher"]
        access_rights_serializer = self.fields["access_rights"]

        if access_rights_data:
            access_rights = access_rights_serializer.create(access_rights_data)

        if publisher_data:
            publisher = publisher_serializer.create(publisher_data)

        new_datacatalog = models.DataCatalog.objects.create(
            access_rights=access_rights, publisher=publisher, **validated_data
        )

        for lang in language_data:
            language_created, created = models.DatasetLanguage.objects.get_or_create(
                url=lang.get("url"), defaults=lang
            )
            new_datacatalog.language.add(language_created)

        return new_datacatalog

    def update(self, instance, validated_data):
        access_rights_serializer = self.fields["access_rights"]
        access_rights_instance = instance.access_rights

        publisher_serializer = self.fields["publisher"]
        publisher_instance = instance.publisher

        if validated_data.get("access_rights"):
            pop_and_update_or_create_instance(
                access_rights_serializer,
                access_rights_instance,
                "access_rights",
                validated_data,
            )

        if validated_data.get("publisher"):
            pop_and_update_or_create_instance(
                publisher_serializer, publisher_instance, "publisher", validated_data
            )

        if validated_data.get("language"):
            language_data = validated_data.pop("language")
            instance.language.clear()
            for language in language_data:
                lang, created = models.DatasetLanguage.objects.update_or_create(
                    url=language.get("url"), defaults=language
                )
                instance.language.add(lang)

        for validated_field in validated_data.keys():
            setattr(
                instance,
                validated_field,
                validated_data.get(validated_field, getattr(instance, validated_field)),
            )
        return super().update(instance, validated_data)
