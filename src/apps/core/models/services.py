from django.db import models
from django.conf import settings

from .abstracts import AbstractBaseModel


class DataStorage(AbstractBaseModel):
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
