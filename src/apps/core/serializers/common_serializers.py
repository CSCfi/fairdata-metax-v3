# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT
from django.core.validators import EMPTY_VALUES
from rest_framework import serializers

from apps.core.models import DatasetLanguage, CatalogHomePage, DatasetPublisher, DatasetLicense, AccessType, AccessRight


class AbstractDatasetModelSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        abstract = True


class AbstractDatasetPropertyModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ("id", "url", "title")
        abstract = True


class DatasetLanguageModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = DatasetLanguage
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields


class CatalogHomePageModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = CatalogHomePage
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields


class AccessTypeModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = AccessType
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields


class DatasetLicenseModelSerializer(AbstractDatasetPropertyModelSerializer):
    class Meta:
        model = DatasetLicense
        fields = AbstractDatasetPropertyModelSerializer.Meta.fields


class DatasetPublisherModelSerializer(AbstractDatasetModelSerializer):
    homepage = CatalogHomePageModelSerializer(many=True)

    class Meta:
        model = DatasetPublisher
        fields = ("id", "name", "homepage")

    def create(self, validated_data):
        homepages = validated_data.pop('homepage')
        dataset_publisher = DatasetPublisher.objects.create(**validated_data)
        for page in homepages:
            page_created = CatalogHomePage.objects.create(**page)
            dataset_publisher.homepage.add(page_created)
        return dataset_publisher

    def update(self, instance, validated_data):
        homepages = validated_data.pop('homepage')
        dataset_publisher = DatasetPublisher.objects.update(**validated_data)
        instance.homepage.clear()
        for homepage in homepages:
            page, created = CatalogHomePage.objects.update_or_create(id=homepage.get('id'), defaults=homepage)
            instance.homepage.add(page)
        return dataset_publisher


class AccessRightsModelSerializer(AbstractDatasetModelSerializer):
    license = DatasetLicenseModelSerializer(read_only=False, many=False)
    access_type = AccessTypeModelSerializer(read_only=False, many=False)

    class Meta:
        model = AccessRight
        fields = ('description', 'license', 'access_type')

    def create(self, validated_data):
        catalog_license = None
        access_type = None
        license_data = validated_data.pop('license')
        access_type_data = validated_data.pop('access_type')
        if license_data not in EMPTY_VALUES:
            catalog_license, license_created = DatasetLicense.objects.get_or_create(url=license_data.get("url"),
                                                                            defaults=license_data)
        if access_type_data not in EMPTY_VALUES:
            access_type, access_type_created = AccessType.objects.get_or_create(url=access_type_data.get("url"),
                                                                                defaults=access_type_data)

        access_rights = AccessRight.objects.create(license=catalog_license, access_type=access_type, **validated_data)
        return access_rights

    def update(self, instance, validated_data):
        license_serializer = self.fields['license']
        access_type_serializer = self.fields['access_type']
        license_instance = instance.license
        access_type_instance = instance.access_type
        license_data = validated_data.pop('license', None)
        access_type_data = validated_data.pop('access_type', None)
        license_serializer.update(license_instance, license_data)
        access_type_serializer.update(access_type_instance, access_type_data)

        return super(AccessRightsModelSerializer, self).update(instance, validated_data)
