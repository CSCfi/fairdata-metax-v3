# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging
from collections import namedtuple

from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import empty

from apps.common.helpers import update_or_create_instance
from apps.common.serializers import PatchSerializer
from apps.core.models import Dataset
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.serializers.common_serializers import (
    AccessRightsModelSerializer,
    DatasetActorModelSerializer,
    MetadataProviderModelSerializer,
    OtherIdentifierModelSerializer,
)
from apps.core.serializers.concept_serializers import SpatialModelSerializer

# for preventing circular import, using submodule instead of apps.core.serializers
from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

from .dataset_files_serializer import FileSetSerializer

logger = logging.getLogger(__name__)

NestedDatasetObjects = namedtuple(
    "NestedDatasetObjects",
    "language, theme, fields_of_science, infrastructure, access_rights, metadata_owner, file_set, actors, other_identifiers, spatial, provenance",
)


class DatasetSerializer(PatchSerializer, serializers.ModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    field_of_science = FieldOfScience.get_serializer()(required=False, many=True)
    infrastructure = ResearchInfra.get_serializer()(required=False, many=True)
    actors = DatasetActorModelSerializer(required=False, many=True)
    fileset = FileSetSerializer(required=False, source="file_set")
    language = Language.get_serializer()(required=False, many=True)
    metadata_owner = MetadataProviderModelSerializer(required=False)
    other_identifiers = OtherIdentifierModelSerializer(required=False, many=True)
    theme = Theme.get_serializer()(required=False, many=True)
    spatial = SpatialModelSerializer(required=False, many=True)
    provenance = ProvenanceModelSerializer(required=False, many=True)

    class Meta:
        model = Dataset
        fields = (
            "id",  # read only
            "access_rights",
            "actors",
            "cumulative_state",
            "data_catalog",
            "description",
            "field_of_science",
            "infrastructure",
            "fileset",
            "issued",
            "keyword",
            "language",
            "metadata_owner",
            "other_identifiers",
            "persistent_identifier",
            "theme",
            "title",
            "provenance",
            "spatial",
            # read only
            "created",
            "cumulation_started",
            "first",
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
        if not rep.get("fileset"):
            rep.pop("fileset", None)
        if not instance.other_identifiers.exists():
            rep.pop("other_identifiers", None)
        return rep

    @staticmethod
    def _pop_related_validated_objects(validated_data) -> NestedDatasetObjects:
        return NestedDatasetObjects(
            language=validated_data.pop("language", None),
            theme=validated_data.pop("theme", None),
            fields_of_science=validated_data.pop("field_of_science", None),
            infrastructure=validated_data.pop("infrastructure", None),
            access_rights=validated_data.pop("access_rights", None),
            metadata_owner=validated_data.pop("metadata_owner", None),
            file_set=validated_data.pop("file_set", None),
            actors=validated_data.pop("actors", None),
            provenance=validated_data.pop("provenance", None),
            other_identifiers=validated_data.pop("other_identifiers", None),
            spatial=validated_data.pop("spatial", None),
        )

    def create(self, validated_data):
        rel_objects = self._pop_related_validated_objects(validated_data)

        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]
        metadata_provider_serializer: MetadataProviderModelSerializer = self.fields[
            "metadata_owner"
        ]
        data_serializer: FileSetSerializer = self.fields["fileset"]
        other_identifiers_serializer: OtherIdentifierModelSerializer = self.fields[
            "other_identifiers"
        ]

        access_rights = None
        if rel_objects.access_rights:
            access_rights = access_rights_serializer.create(rel_objects.access_rights)

        metadata_provider = None
        if rel_objects.metadata_owner:
            metadata_provider = metadata_provider_serializer.create(rel_objects.metadata_owner)

        other_identifiers = []
        if rel_objects.other_identifiers:
            other_identifiers = other_identifiers_serializer.create(rel_objects.other_identifiers)

        dataset = Dataset.objects.create(
            **validated_data, access_rights=access_rights, metadata_owner=metadata_provider
        )
        if rel_objects.language:
            dataset.language.set(rel_objects.language)
        if rel_objects.theme:
            dataset.theme.set(rel_objects.theme)
        if rel_objects.fields_of_science:
            dataset.field_of_science.set(rel_objects.fields_of_science)
        if rel_objects.infrastructure:
            dataset.infrastructure.set(rel_objects.infrastructure)
        if rel_objects.other_identifiers:
            dataset.other_identifiers.set(other_identifiers)
        if rel_objects.spatial:
            spatial = self.fields["spatial"].create(rel_objects.spatial)
            dataset.spatial.set(spatial)

        if rel_objects.actors:
            actors: DatasetActorModelSerializer = self.fields["actors"]
            actors._validated_data = rel_objects.actors
            actors = actors.save(dataset_id=dataset.id)
            dataset.actors.set(list(actors))

        if rel_objects.provenance:
            events: ProvenanceModelSerializer = self.fields["provenance"]
            events._validated_data = rel_objects.provenance
            events = events.save(dataset_id=dataset.id)
            dataset.provenance.set(list(events))

        if rel_objects.file_set:
            data_serializer.create(dataset=dataset, validated_data=rel_objects.file_set)

        return dataset

    def update(self, instance, validated_data):
        rel_objects = self._pop_related_validated_objects(validated_data)

        access_rights_serializer: AccessRightsModelSerializer = self.fields["access_rights"]
        if rel_objects.access_rights:
            instance.access_rights = update_or_create_instance(
                access_rights_serializer, instance.access_rights, rel_objects.access_rights
            )

        other_identifiers_serializer: OtherIdentifierModelSerializer = self.fields[
            "other_identifiers"
        ]
        other_identifiers = []
        if rel_objects.other_identifiers:
            other_identifiers = other_identifiers_serializer.update(
                instance, rel_objects.other_identifiers
            )

        metadata_owner_serializer: MetadataProviderModelSerializer = self.fields["metadata_owner"]
        if rel_objects.metadata_owner:
            update_or_create_instance(
                metadata_owner_serializer, instance.metadata_owner, rel_objects.metadata_owner
            )
        if rel_objects.language:
            instance.language.set(rel_objects.language)
        if rel_objects.theme:
            instance.theme.set(rel_objects.theme)
        if rel_objects.fields_of_science:
            instance.field_of_science.set(rel_objects.fields_of_science)
        if rel_objects.infrastructure:
            instance.infrastructure.set(rel_objects.infrastructure)
        if rel_objects.other_identifiers:
            instance.other_identifiers.set(other_identifiers)
        if rel_objects.spatial:
            instance.spatial.set(rel_objects.spatial)

        data_serializer: FileSetSerializer = self.fields["fileset"]
        if rel_objects.file_set:
            # Assigning instance.file_set here avoids refetch from db and clearing
            # non-persistent values added_files_count and removed_files_count
            instance.file_set = data_serializer.create(
                dataset=instance, validated_data=rel_objects.file_set
            )

        return super().update(instance, validated_data)
