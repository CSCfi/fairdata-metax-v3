import uuid

from .abstracts import AbstractDatasetProperty
from django.db import models


class Contract(AbstractDatasetProperty):

    description = models.CharField(max_length=200, blank=True, null=True)
    quota = models.BigIntegerField()
    valid_until = models.DateTimeField()