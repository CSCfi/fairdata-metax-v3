# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json

from apps.core.models import DataCatalog, DatasetLicense, AccessType, AccessRight, DatasetPublisher, CatalogHomePage, \
    DatasetLanguage
from apps.core.serializers.common_serializers import DatasetLicenseModelSerializer, AccessTypeModelSerializer, \
    AccessRightsModelSerializer, DatasetPublisherModelSerializer
from apps.core.serializers.data_catalog_serializer import DataCatalogSerializer

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response


class DataCatalogView(GenericAPIView):
    serializer_class = DataCatalogSerializer
    queryset = DataCatalog.objects.all()

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = DataCatalogSerializer(data=data)
        if serializer.is_valid():
            language_data = data.pop("language", None)
            access_rights_data = data.pop("access_rights", None)
            publisher_data = data.pop("publisher", None)
            access_rights = None
            publisher = None
            if access_rights_data:
                license = None
                access_type = None
                license_data = access_rights_data.pop("license", None)
                access_type_data = access_rights_data.pop("access_type", None)
                if license_data:
                    try:
                        license = DatasetLicense.objects.get(id=license_data.get('id'))
                    except ObjectDoesNotExist:
                        license_serializer = DatasetLicenseModelSerializer(data=license_data)
                        if license_serializer.is_valid(raise_exception=True):
                            license = license_serializer.save()

                if access_type_data:
                    try:
                        access_type = AccessType.objects.get(id=access_type_data.get('id'))
                    except ObjectDoesNotExist:
                        access_type_serializer = AccessTypeModelSerializer(data=access_type_data)
                        if access_type_serializer.is_valid(raise_exception=True):
                            access_type = access_type_serializer.save()

                access_rights_serializer = AccessRightsModelSerializer(data=access_rights_data)
                if access_rights_serializer.is_valid(raise_exception=True):
                    access_rights = access_rights_serializer.save()
                    access_rights.licence = license
                    access_rights.access_type = access_type
                    access_rights.save()

            if publisher_data:
                publisher_serializer = DatasetPublisherModelSerializer(data=publisher_data)
                if publisher_serializer.is_valid(raise_exception=True):
                    publisher = publisher_serializer.save()

            new_data_catalog = serializer.save(publisher=publisher, access_rights=access_rights)

            for lang in language_data:
                language_created, created = DatasetLanguage.objects.get_or_create(id=lang.get('id'), defaults=lang)
                new_data_catalog.language.add(language_created)
            response_serializer = DataCatalogSerializer(new_data_catalog)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        data_catalogs = DataCatalog.objects.all()
        serializer = DataCatalogSerializer(data_catalogs, many=True)
        return Response(serializer.data)
