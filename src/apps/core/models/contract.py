from django.db import models
from simple_history.models import HistoricalRecords

from apps.common.models import AbstractDatasetProperty


class Contract(AbstractDatasetProperty):
    description = models.CharField(max_length=200, blank=True, null=True)
    quota = models.BigIntegerField()
    valid_until = models.DateTimeField()
    history = HistoricalRecords()
