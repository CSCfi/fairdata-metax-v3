# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT


from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.files.views import DirectoryViewSet, FileStorageView, FileViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"filestorages", FileStorageView, basename="storage")
router.register(r"files", FileViewSet, basename="files")
router.register(r"directories", DirectoryViewSet, basename="directories")

urlpatterns = [
    path(r"", include(router.urls)),
]
