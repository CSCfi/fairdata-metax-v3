from simple_history.models import HistoricalRecords

from .abstracts import AbstractBaseModel
from .data_catalog import AccessRights
from .catalog_record import Dataset
from apps.files.models.file import File
from apps.files.models.file_storage import FileStorage
from .concepts import License
from django.contrib.postgres.fields import HStoreField
from django.db import models


class Distribution(AbstractBaseModel):
    """A specific representation of a dataset.

    RDF Class: dcat:Distribution

    Source: DCAT Version 3, Draft 11,
    https://www.w3.org/TR/vocab-dcat-3/#Class:Distribution

    Attributes:
        title (HStoreField): Title of the distribution
        description (models.CharField): Description of the distribution
        release_date (models.DateTimeField): Release date of the distribution
        license (models.ForeignKey): License of the distribution
        access_rights (models.ForeignKey): Access rights of the distribution
        access_url (models.URLField): The landing page of the distribution
        access_service (models.ForeignKey): Service that provides the distribution files
        download_url (models.URLField): Direct download link for the distribution resources
        byte_size (models.BigIntegerField): Total size of the distribution in bytes
        checksum (models.TextField): The file-integrity checksum of the distribution
        files (models.ManyToManyField): Files associated with the distribution
        dataset (models.ForeignKey): The dataset providing the distribution
    """

    id = models.CharField(
        max_length=255,
        primary_key=True,
        help_text="A specific representation of a dataset.",
    )
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    description = models.CharField(max_length=200, blank=True, null=True)
    issued = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of formal issuance (e.g., publication) of the resource.",
    )
    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
    )
    access_rights = models.ForeignKey(
        AccessRights, on_delete=models.SET_NULL, related_name="distributions", null=True
    )
    access_url = models.URLField(null=True, blank=True)
    access_service = models.ForeignKey(
        FileStorage,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
    )
    download_url = models.URLField(null=True, blank=True)
    byte_size = models.BigIntegerField(default=0)
    checksum = models.TextField(null=True, blank=True)
    files = models.ManyToManyField(File, related_query_name="distributions")
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
    )
    history = HistoricalRecords(m2m_fields=(files,))
