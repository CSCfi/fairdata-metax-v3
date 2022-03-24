# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from rest_framework.serializers import ModelSerializer

from apps.core.models import DataCatalog
from apps.core.serializers.common_serializers import AccessRightsModelSerializer, DatasetPublisherModelSerializer, \
    DatasetLanguageModelSerializer


class DataCatalogSerializer(ModelSerializer):
    access_rights = AccessRightsModelSerializer(read_only=True)
    publisher = DatasetPublisherModelSerializer(read_only=True)
    language = DatasetLanguageModelSerializer(read_only=True, many=True)

    class Meta:
        model = DataCatalog
        fields = '__all__'


