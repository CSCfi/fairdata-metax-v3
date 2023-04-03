# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from rest_framework import serializers

from apps.core.models import Dataset
from apps.core.models.concepts import FieldOfScience, Language, Theme
from apps.core.serializers.common_serializers import AccessRightsModelSerializer

from .dataset_files_serializer import DatasetFilesSerializer
from django.conf import settings

logger = logging.getLogger(__name__)


class DatasetSerializer(serializers.ModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    language = Language.get_serializer()(required=False, many=True)
    theme = Theme.get_serializer()(required=False, many=True)
    field_of_science = FieldOfScience.get_serializer()(required=False, many=True)
    files = DatasetFilesSerializer(required=False)

    class Meta:
        model = Dataset
        fields = (
            "persistent_identifier",
            "issued",
            "title",
            "description",
            "theme",
            "language",
            "data_catalog",
            "access_rights",
            "field_of_science",
            "files",
            # read only
            "id",
            "first",
            "last",
            "previous",
            "replaces",
            "is_deprecated",
            "is_removed",
            "removal_date",
            "cumulation_started",
            "created",
            "modified",
        )
        read_only_fields = (
            "id",
            "first",
            "last",
            "previous",
            "replaces",
            "is_deprecated",
            "is_removed",
            "removal_date",
            "cumulation_started",
            "created",
            "modified",
        )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for lang in rep["language"]:
            lang["pref_label"] = {
                key: lang["pref_label"][key]
                for key in settings.DISPLAY_API_LANGUAGES
                if key in lang["pref_label"].keys()
            }
        if not instance.storage_project:  # remove files dict from response if no files exist
            rep.pop("files", None)
        return rep

    def create(self, validated_data):
        languages = validated_data.pop("language", [])
        themes = validated_data.pop("theme", [])
        fields_of_science = validated_data.pop("field_of_science", [])

        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]
        access_rights = None
        if access_rights_data := validated_data.pop("access_rights", None):
            access_rights = access_rights_serializer.create(access_rights_data)

        files_data = validated_data.pop("files", None)

        dataset = Dataset.objects.create(**validated_data, access_rights=access_rights)

        dataset.language.set(languages)
        dataset.theme.set(themes)
        dataset.field_of_science.set(fields_of_science)

        if files_data:
            files_serializer: DatasetFilesSerializer = self.fields["files"]
            files_serializer.update(dataset.files, files_data)

        return dataset

    def update(self, instance, validated_data):
        languages = validated_data.pop("language", [])
        themes = validated_data.pop("theme", [])
        fields_of_science = validated_data.pop("field_of_science", [])

        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]
        access_rights = None
        if access_rights_data := validated_data.pop("access_rights", None):
            access_rights = access_rights_serializer.create(access_rights_data)
        instance.access_rights = access_rights

        files_data = validated_data.pop("files", None)

        super().update(instance, validated_data)

        instance.language.set(languages)
        instance.theme.set(themes)
        instance.field_of_science.set(fields_of_science)

        if files_data:
            files_serializer: DatasetFilesSerializer = self.fields["files"]
            files_serializer.update(instance.files, files_data)

        return instance
