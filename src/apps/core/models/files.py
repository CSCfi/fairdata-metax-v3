import uuid

from .abstracts import AbstractBaseModel
from .services import DataStorage
from django.db import models


class File(AbstractBaseModel):

    byte_size = models.BigIntegerField(default=0)
    checksum = models.TextField()
    date_frozen = models.DateTimeField(null=True, blank=True)
    file_format = models.CharField(max_length=200, null=True)
    file_name = models.TextField()
    file_path = models.TextField()
    file_storage = models.ForeignKey(
        DataStorage, on_delete=models.DO_NOTHING, null=True, blank=True
    )
    date_uploaded = models.DateTimeField()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_identifier = models.CharField(max_length=200, null=True, blank=True)
