import logging
import uuid

from django.db import models

_logger = logging.getLogger(__name__)


class OrganizationStatistics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    organization = models.CharField(unique=True, max_length=200)
    count_total = models.IntegerField(default=0)
    count_ida = models.IntegerField(default=0)
    count_pas = models.IntegerField(default=0)
    count_att = models.IntegerField(default=0)
    count_other = models.IntegerField(default=0)
    byte_size_total = models.BigIntegerField(default=0)
    byte_size_ida = models.BigIntegerField(default=0)
    byte_size_pas = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["organization"]
