# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import logging
from rest_framework.serializers import ModelSerializer

from apps.core.models.services import DataStorage
from apps.core.serializers.common_serializers import (
    AbstractDatasetPropertyModelSerializer,
)

logger = logging.getLogger(__name__)


class DataStorageModelSerializer(ModelSerializer):
    class Meta:
        model = DataStorage
        fields = (
            "id",
            "endpoint_url",
            "endpoint_description",
            "created",
            "modified",
            "is_removed",
        )
        read_only_fields = ["date_created", "date_modified", "is_removed"]
