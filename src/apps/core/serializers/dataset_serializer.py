# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging
from collections import namedtuple

from common.helpers import update_or_create_instance
from django.conf import settings
from rest_framework import serializers

from apps.core.models import Dataset
from apps.core.models.concepts import FieldOfScience, Language, Theme
from apps.core.serializers.common_serializers import (
    AccessRightsModelSerializer,
    DatasetActorModelSerializer,
    MetadataProviderModelSerializer,
)

from .dataset_files_serializer import DatasetFilesSerializer

logger = logging.getLogger(__name__)

NestedDatasetObjects = namedtuple(
    "NestedDatasetObjects",
    "language, theme, fields_of_science, access_rights, metadata_owner, files, actors",
)


class DatasetSerializer(serializers.ModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    field_of_science = FieldOfScience.get_serializer()(required=False, many=True)
    actors = DatasetActorModelSerializer(required=False, many=True)
    files = DatasetFilesSerializer(required=False)
    language = Language.get_serializer()(required=False, many=True)
    metadata_owner = MetadataProviderModelSerializer(required=False)
    theme = Theme.get_serializer()(required=False, many=True)

    class Meta:
        model = Dataset
        fields = (
            "access_rights",
            "actors",
            "data_catalog",
            "description",
            "field_of_science",
            "files",
            "issued",
            "language",
            "metadata_owner",
            "persistent_identifier",
            "theme",
            "title",
            # read only
            "created",
            "cumulation_started",
            "first",
            "id",
            "is_deprecated",
            "is_removed",
            "last",
            "modified",
            "previous",
            "removal_date",
            "replaces",
        )
        read_only_fields = (
            "created",
            "cumulation_started",
            "first",
            "id",
            "is_deprecated",
            "is_removed",
            "last",
            "modified",
            "previous",
            "removal_date",
            "replaces",
        )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for lang in rep["language"]:
            lang["pref_label"] = {
                key: lang["pref_label"][key]
                for key in settings.DISPLAY_API_LANGUAGES
                if key in lang["pref_label"].keys()
            }
        if not instance.file_storage:  # remove files dict from response if no files exist
            rep.pop("files", None)
        return rep

    @staticmethod
    def _pop_related_validated_objects(validated_data) -> NestedDatasetObjects:
        return NestedDatasetObjects(
            language=validated_data.pop("language", []),
            theme=validated_data.pop("theme", []),
            fields_of_science=validated_data.pop("field_of_science", []),
            access_rights=validated_data.pop("access_rights", None),
            metadata_owner=validated_data.pop("metadata_owner", None),
            files=validated_data.pop("files", None),
            actors=validated_data.pop("actors", None),
        )

    def create(self, validated_data):
        rel_objects = self._pop_related_validated_objects(validated_data)

        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]
        metadata_provider_serializer: MetadataProviderModelSerializer = self.fields[
            "metadata_owner"
        ]
        files_serializer: DatasetFilesSerializer = self.fields["files"]

        access_rights = None
        if rel_objects.access_rights:
            access_rights = access_rights_serializer.create(rel_objects.access_rights)

        metadata_provider = None
        if rel_objects.metadata_owner:
            metadata_provider = metadata_provider_serializer.create(rel_objects.metadata_owner)

        dataset = Dataset.objects.create(
            **validated_data, access_rights=access_rights, metadata_owner=metadata_provider
        )

        dataset.language.set(rel_objects.language)
        dataset.theme.set(rel_objects.theme)
        dataset.field_of_science.set(rel_objects.fields_of_science)

        if rel_objects.actors:
            actors = DatasetActorModelSerializer(many=True, data=rel_objects.actors)
            actors.is_valid(raise_exception=True)
            actors = actors.save(dataset_id=dataset.id)
            dataset.actors.set(list(actors))

        if rel_objects.files:
            files_serializer.update(dataset.files, rel_objects.files)

        return dataset

    def update(self, instance, validated_data):
        rel_objects = self._pop_related_validated_objects(validated_data)

        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]
        if rel_objects.access_rights:
            update_or_create_instance(
                access_rights_serializer, instance.access_rights, rel_objects.access_rights
            )
        dataset_actor_serializer: DatasetActorModelSerializer = self.fields["actors"]
        if rel_objects.actors:
            update_or_create_instance(
                dataset_actor_serializer, instance.actors, rel_objects.actors
            )

        metadata_owner_serializer: MetadataProviderModelSerializer = self.fields["metadata_owner"]
        if rel_objects.metadata_owner:
            update_or_create_instance(
                metadata_owner_serializer, instance.metadata_owner, rel_objects.metadata_owner
            )

        instance.language.set(rel_objects.language)
        instance.theme.set(rel_objects.theme)
        instance.field_of_science.set(rel_objects.fields_of_science)

        files_serializer: DatasetFilesSerializer = self.fields["files"]
        if rel_objects.files:
            files_serializer.update(instance.files, rel_objects.files)

        return super().update(instance, validated_data)
