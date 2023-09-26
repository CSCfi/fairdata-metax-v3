# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from apps.common.serializers import NestedModelSerializer, PatchSerializer
from apps.core.models import Dataset
from apps.core.models.concepts import FieldOfScience, Language, ResearchInfra, Theme
from apps.core.serializers.common_serializers import (
    AccessRightsModelSerializer,
    DatasetActorModelSerializer,
    MetadataProviderModelSerializer,
    OtherIdentifierModelSerializer,
    RemoteResourceSerializer,
    TemporalModelSerializer,
)
from apps.core.serializers.concept_serializers import SpatialModelSerializer

# for preventing circular import, using submodule instead of apps.core.serializers
from apps.core.serializers.provenance_serializers import ProvenanceModelSerializer

from .dataset_files_serializer import FileSetSerializer

logger = logging.getLogger(__name__)


class DatasetSerializer(PatchSerializer, NestedModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    field_of_science = FieldOfScience.get_serializer_field(required=False, many=True)
    infrastructure = ResearchInfra.get_serializer_field(required=False, many=True)
    actors = DatasetActorModelSerializer(required=False, many=True)
    fileset = FileSetSerializer(required=False, source="file_set")
    remote_resources = RemoteResourceSerializer(many=True, required=False)
    language = Language.get_serializer_field(required=False, many=True)
    metadata_owner = MetadataProviderModelSerializer(required=False)
    other_identifiers = OtherIdentifierModelSerializer(required=False, many=True)
    theme = Theme.get_serializer_field(required=False, many=True)
    spatial = SpatialModelSerializer(required=False, many=True)
    temporal = TemporalModelSerializer(required=False, many=True)
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
            "temporal",
            "remote_resources",
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
