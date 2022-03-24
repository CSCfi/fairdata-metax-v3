# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from rest_framework import serializers

from apps.core.models import DatasetLanguage, CatalogHomePage, DatasetPublisher, DatasetLicense, AccessType, AccessRight


class AbstractDatasetModelSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        abstract = True


class AbstractDatasetPropertyModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ("id", "title")
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

    def validate(self, attrs):
        if 'title' not in attrs:
            licence = DatasetLicense.objects.filter(id=attrs.get('id')).first()
            if licence:
                attrs['title'] = licence.title
        data = serializers.Serializer.validate(self, attrs)
        return data


class DatasetPublisherModelSerializer(AbstractDatasetModelSerializer):
    homepage = CatalogHomePageModelSerializer(many=True)

    class Meta:
        model = DatasetPublisher
        fields = ("name", "homepage")

    def create(self, validated_data):
        homepages = validated_data.pop('homepage')
        dataset_publisher = DatasetPublisher.objects.create(**validated_data)
        for page in homepages:
            page_created = CatalogHomePage.objects.create(**page)
            # page_created.publishers.add(dataset_publisher)
            dataset_publisher.homepage.add(page_created)
        return dataset_publisher


class AccessRightsModelSerializer(AbstractDatasetModelSerializer):
    license = DatasetLicenseModelSerializer(read_only=True, many=False)
    access_type = AccessTypeModelSerializer(read_only=True, many=False)
    class Meta:
        model = AccessRight
        fields = "__all__"



