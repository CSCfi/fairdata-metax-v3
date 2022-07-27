import logging

from rest_framework import viewsets

from apps.core.serializers import DatasetPublisherModelSerializer, AccessRightsModelSerializer, \
    DatasetLanguageModelSerializer

logger = logging.getLogger(__name__)


class PublisherViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetPublisherModelSerializer


class AccessRightsViewSet(viewsets.ModelViewSet):
    serializer_class = AccessRightsModelSerializer


class DatasetLanguageViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetLanguageModelSerializer
