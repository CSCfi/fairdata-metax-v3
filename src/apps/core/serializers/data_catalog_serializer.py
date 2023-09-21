# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging

from apps.common.helpers import update_or_create_instance
from apps.common.serializers import NestedModelSerializer
from apps.core.models import DataCatalog, Language
from apps.core.serializers import AccessRightsModelSerializer, DatasetPublisherModelSerializer

logger = logging.getLogger(__name__)


class DataCatalogModelSerializer(NestedModelSerializer):
    access_rights = AccessRightsModelSerializer(required=False)
    publisher = DatasetPublisherModelSerializer(required=False)
    language = Language.get_serializer_field(required=False, many=True)

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
            "dataset_schema",
            "url",
        )
