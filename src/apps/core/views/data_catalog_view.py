# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
import json

from apps.core.managers.DataCatalog import DataCatalogManager
from apps.core.models import DataCatalog, DatasetLicense, AccessType, AccessRight, DatasetPublisher, CatalogHomePage, \
    DatasetLanguage
from apps.core.serializers.common_serializers import DatasetLicenseModelSerializer, AccessTypeModelSerializer, \
    AccessRightsModelSerializer, DatasetPublisherModelSerializer
from apps.core.serializers.data_catalog_serializer import DataCatalogSerializer, DataCatalogUpdateSerializer

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import GenericAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response


class DataCatalogEditor:

    def license_edit(self, license_data):
        if license_data:
            try:
                return DatasetLicense.objects.get(id=license_data.get('id'))
            except ObjectDoesNotExist:
                license_serializer = DatasetLicenseModelSerializer(data=license_data)
                if license_serializer.is_valid(raise_exception=True):
                    return license_serializer.save()
        else:
            return None

    def access_type_edit(self, access_type_data):
        if access_type_data:
            try:
                return AccessType.objects.get(id=access_type_data.get('id'))
            except ObjectDoesNotExist:
                access_type_serializer = AccessTypeModelSerializer(data=access_type_data)
                if access_type_serializer.is_valid(raise_exception=True):
                    return access_type_serializer.save()
        else:
            return None


class DataCatalogView(GenericAPIView, DataCatalogEditor):
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

                access_rights_serializer = AccessRightsModelSerializer(data=access_rights_data)
                if access_rights_serializer.is_valid(raise_exception=True):
                    access_rights = access_rights_serializer.save()
                    license_data = access_rights_data.pop("license", None)
                    access_type_data = access_rights_data.pop("access_type", None)
                    access_rights.license = self.license_edit(license_data)
                    access_rights.access_type = self.access_type_edit(access_type_data)
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
        data = {}
        filter_header = self.request.META.get('HTTP_X_FILTER', None)
        if filter_header:
            data = json.loads(filter_header)
        data_catalogs = DataCatalogManager().filter_catalogs(filter_data=data)
        serializer = DataCatalogSerializer(data_catalogs, many=True)
        return Response(serializer.data)


class DataCatalogViewByID(RetrieveUpdateDestroyAPIView, DataCatalogEditor):
    serializer_class = DataCatalogSerializer
    queryset = DataCatalog.objects.all()

    def get(self, request, *args, **kwargs):
        catalog_id = kwargs['id']
        datacatalog = get_object_or_404(DataCatalog, id=catalog_id)
        serializer = self.serializer_class(datacatalog)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        catalog_id = kwargs['id']
        data = request.data
        if catalog_id != data.get('id', None):
            return Response({'error': 'Data catalog id missmatch'}, status=status.HTTP_400_BAD_REQUEST)
        updated_catalog = None
        access_rights = None
        publisher = None
        datacatalog = get_object_or_404(DataCatalog, id=catalog_id)
        serializer = DataCatalogUpdateSerializer(datacatalog, data=data)
        if serializer.is_valid(raise_exception=True):
            updated_catalog = serializer.save()
        serializer = self.serializer_class(updated_catalog)
        if serializer.data.get('access_rights', None) != data.get('access_rights', None):
            access_rights_data = data.pop("access_rights", None)
            if not access_rights_data:        # remove access rights
                access_rights = get_object_or_404(AccessRight, id=updated_catalog.access_rights_id)
                access_rights.delete()
                access_rights = None
            else:                               # updating access rights
                if not serializer.data.get('access_rights', None):
                    access_rights_serializer = AccessRightsModelSerializer(data=access_rights_data)
                    if access_rights_serializer.is_valid(raise_exception=True):
                        access_rights = access_rights_serializer.save()
                else:
                    access_rights = get_object_or_404(AccessRight, id=updated_catalog.access_rights_id)
                license_data = access_rights_data.pop("license", None)
                access_type_data = access_rights_data.pop("access_type", None)
                access_rights.license = self.license_edit(license_data)
                access_rights.access_type = self.access_type_edit(access_type_data)
                access_rights.save()
            updated_catalog.access_rights = access_rights
            updated_catalog.save()

        if serializer.data.get('publisher', None) != data.get('publisher', None):
            publisher_data = data.pop("publisher", None)
            if not publisher_data:
                publisher = get_object_or_404(DatasetPublisher, id=updated_catalog.publisher_id)
                publisher.delete()
                publisher = None
            else:
                if not serializer.data.get('publisher', None):
                    publisher_serializer = DatasetPublisherModelSerializer(data=publisher_data)
                    if publisher_serializer.is_valid(raise_exception=True):
                        publisher = publisher_serializer.save()
                else:
                    publisher = get_object_or_404(DatasetPublisher, id=updated_catalog.publisher_id)
                    publisher.name = publisher_data.get('name')
                    publisher.homepage.clear()
                    if 'homepage' in publisher_data:
                        for homepage in publisher_data.get('homepage', []):
                            page, created = CatalogHomePage.objects.update_or_create(id=homepage.get('id'),
                                                                                     defaults=homepage)
                            publisher.homepage.add(page)
                    publisher.save()
            updated_catalog.publisher = publisher
            updated_catalog.save()
        if serializer.data.get('language', None) != data.get('language', None):
            language_data = data.pop('language', None)
            updated_catalog.language.clear()
            for lang in language_data:
                language_created, created = DatasetLanguage.objects.get_or_create(id=lang.get('id'), defaults=lang)
                updated_catalog.language.add(language_created)
            updated_catalog.save()
        response_serializer = self.serializer_class(updated_catalog)
        return Response(response_serializer.data)

    def patch(self, request, *args, **kwargs):
        raise NotImplementedError('PATCH method not implemented yet')

    def delete(self, request, *args, **kwargs):
        catalog_id = kwargs['id']
        datacatalog = get_object_or_404(DataCatalog, id=catalog_id)
        datacatalog.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


