# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.views import (
    DataCatalogView,
    PublisherViewSet,
    DatasetViewSet,
)
from apps.core.views.dataset_view import DatasetFilesViewSet, DatasetDirectoryViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"datacatalog", DataCatalogView, basename="datacatalog")
router.register(r"dataset", DatasetViewSet, basename="dataset")
router.register(
    r"dataset/(?P<dataset_id>[^/.]+)/files",
    DatasetFilesViewSet,
    basename="dataset_files",
)
router.register(
    r"dataset/(?P<dataset_id>[^/.]+)/directories",
    DatasetDirectoryViewSet,
    basename="dataset_directories",
)
router.register(r"publisher", PublisherViewSet, basename="publisher")

urlpatterns = [
    path(r"", include(router.urls)),
]
