# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from apps.core.views import (
    DataCatalogView,
    DataStorageView,
    PublisherViewSet,
    DatasetViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r"datacatalog", DataCatalogView, basename="datacatalog")
router.register(r"dataset", DatasetViewSet, basename="dataset")
router.register(r"datastorage", DataStorageView, basename="storage")
router.register(r"publisher", PublisherViewSet, basename="publisher")

urlpatterns = [
    path(r"", include(router.urls)),
]
