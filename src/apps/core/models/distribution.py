from .abstracts import AbstractDatasetProperty
from .data_catalog import AccessRight, DatasetLicense
from .files import File
from .services import DataStorage
from django.db import models


class Distribution(AbstractDatasetProperty):
    """A specific representation of a dataset.

    RDF Class: dcat:Distribution

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Distribution
    """

    description = models.CharField(max_length=200, blank=True, null=True)
    release_date = models.DateTimeField(null=True, blank=True)
    license = models.ForeignKey(
        DatasetLicense,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
    )
    access_rights = models.ForeignKey(
        AccessRight, on_delete=models.SET_NULL, related_name="distributions", null=True
    )
    access_url = models.URLField()
    access_service = models.ForeignKey(
        DataStorage,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
    )
    download_url = models.URLField()
    byte_size = models.BigIntegerField(default=0)
    checksum = models.TextField()
    files = models.ManyToManyField(File, related_query_name="distributions")