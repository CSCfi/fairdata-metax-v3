# This file is part of the Metax API service
#
# Copyright 2017-2022 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path

from apps.core.views.data_catalog_view import DataCatalogView, DataCatalogViewByID


urlpatterns = ([
    re_path(r'datacatalog$', DataCatalogView.as_view(), name='datacatalog'),
    re_path(r'datacatalog/(?P<id>.+)', DataCatalogViewByID.as_view(), name='datacatalogbyid'),
    ])
