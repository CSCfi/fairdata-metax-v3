from django.conf import settings
from .abstracts import AbstractBaseModel
from .data_catalog import AccessRight, DatasetLicense
from .catalog_record import ResearchDataset
from .files import File
from .services import DataStorage
from django.contrib.postgres.fields import HStoreField
from django.db import models


class Distribution(AbstractBaseModel):
    """A specific representation of a dataset.

    RDF Class: dcat:Distribution

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Distribution
    """

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="A specific representation of a dataset.",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
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
    dataset = models.ForeignKey(
        ResearchDataset,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
    )
