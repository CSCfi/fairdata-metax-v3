# This file is part of the Metax API service
#
# Copyright 2017-2023 Ministry of Education and Culture, Finland
#
# :author: CSC - IT Center for Science Ltd., Espoo Finland <servicedesk@csc.fi>
# :license: MIT

from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models.abstracts import AbstractBaseModel


class FileStorage(AbstractBaseModel):
    """A collection of operations that provides access to one or more datasets or data processing functions.

    RDF Class: dcat:DataService
    Source: DCAT Version3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Data_Service
    """

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="A unique id of the data storage",
    )

    endpoint_url = models.URLField(
        help_text="The root location or primary endpoint of the service (a Web-resolvable IRI)."
    )

    endpoint_description = models.TextField(
        help_text="A description of the services available via the end-points, including their operations, parameters etc."
    )
    history = HistoricalRecords()
