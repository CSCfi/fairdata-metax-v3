import logging
import uuid

from django.db import models
from django.contrib.postgres.fields import ArrayField

_logger = logging.getLogger(__name__)


class ProjectStatistics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project_identifier = models.CharField(unique=True, max_length=200)
    ida_count = models.IntegerField()
    ida_byte_size = models.BigIntegerField()
    ida_published_datasets = ArrayField(models.TextField(), default=list)
    pas_count = models.IntegerField(default=0)
    pas_byte_size = models.BigIntegerField(default=0)
    pas_published_datasets = ArrayField(models.TextField(), default=list)

    class Meta:
        ordering = ["project_identifier"]
