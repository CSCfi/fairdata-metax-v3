import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from .abstracts import AbstractBaseModel


class File(AbstractBaseModel):
    """

    Attributes:
        byte_size (models.BigIntegerField): The size of the file in bytes
        checksum (models.TextField): The file-integrity checksum of the file
        date_frozen (models.DateTimeField): The date when the file was frozen in IDA
        file_format (models.CharField): The file-format of the file
        file_name (models.TextField): The name of the file
        file_path (models.TextField): The path of the file
        date_uploaded (models.DateTimeField): The date when the file was uploaded to IDA
        project_identifier (models.CharField): The IDA project identifier
    """

    byte_size = models.BigIntegerField(default=0)
    checksum = models.TextField()
    date_frozen = models.DateTimeField(null=True, blank=True)
    file_format = models.CharField(max_length=200, null=True)
    file_name = models.TextField()
    file_path = models.TextField()
    date_uploaded = models.DateTimeField()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_identifier = models.CharField(max_length=200, null=True, blank=True)
    history = HistoricalRecords()